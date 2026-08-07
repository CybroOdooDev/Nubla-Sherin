# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class NhsComplaint(models.Model):
    """Represents a PALS concern or formal NHS complaint and drives its intake-to-closure workflow."""
    _name = 'nhs.complaint'
    _description = 'PALS Concern or Formal NHS Complaint'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_at desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, readonly=True,
                       copy=False, default='New', tracking=True,
                       help='Auto-generated reference. PALS: PALS/2026/00123; Complaints: COMP/2026/00088.')
    record_type = fields.Selection([
        ('pals', 'PALS Concern'),
        ('complaint', 'Formal Complaint'),
    ], string='Type', required=True, default='pals', tracking=True,
       help="'pals' = informal PALS concern; 'complaint' = statutory formal complaint.")
    company_id = fields.Many2one('res.company', string='Organisation', required=True,
                                 default=lambda self: self.env.company, tracking=True)
    subject_summary = fields.Char(string='Summary', required=True,
                                  help='Short one-line summary of the complaint for lists and dashboards.')
    description = fields.Text(string='Complaint Narrative', required=True,
                              help='The complaint as received. Avoid unnecessary clinical detail or third-party identifiers.')
    received_at = fields.Datetime(string='Received At', required=True,
                                  default=fields.Datetime.now, tracking=True,
                                  help='When the concern/complaint was received. Starts the acknowledgement clock for formal complaints.')
    received_via = fields.Selection([
        ('letter', 'Letter'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('in_person', 'In Person'),
        ('website', 'Website / Portal'),
        ('mp', 'MP / Solicitor Correspondence'),
        ('solicitor', 'Solicitor'),
        ('other', 'Other'),
    ], string='Received Via', required=True, default='phone', tracking=True)
    event_date = fields.Date(string='Date of Incident/Event',
                             help='When the matter complained about occurred. Drives the 12-month time-limit flag.')
    within_time_limit = fields.Boolean(string='Within 12-Month Time Limit',
                                       compute='_compute_within_time_limit', store=True,
                                       help='False when received more than 12 months after the event date.')
    is_anonymous = fields.Boolean(string='Anonymous',
                                  help='PALS only — concern raised anonymously; hides complainant detail.')
    complainant_id = fields.Many2one('nhs.complainant', string='Complainant', tracking=True,
                                     help='The person making the complaint. Auto-created from inline fields on Acknowledge.')
    complainant_name = fields.Char(string='Complainant Name')
    complainant_email = fields.Char(string='Email')
    complainant_phone = fields.Char(string='Phone')
    complainant_relationship = fields.Selection([
        ('self', 'Patient (self)'),
        ('relative', 'Relative'),
        ('carer', 'Carer'),
        ('advocate', 'Advocate'),
        ('mp', 'MP / Elected Representative'),
        ('solicitor', 'Solicitor'),
        ('other', 'Other'),
    ], string='Relationship to Patient', default='self')
    is_third_party = fields.Boolean(string='Third-Party Representative',
                                    help='True when the complainant acts on behalf of the patient.')
    consent_status = fields.Selection([
        ('not_required', 'Not Required (patient is complainant)'),
        ('obtained', 'Consent Obtained'),
        ('pending', 'Consent Pending'),
        ('refused', 'Consent Refused'),
    ], string='Consent Status', default='not_required', tracking=True,
       help='Data-protection control for third-party complaints. Response blocked until obtained.')
    consent_evidence_ref = fields.Char(string='Consent Evidence Reference',
                                       help='Reference to where consent is recorded (chatter attachment or note).')
    patient_name = fields.Char(string='Patient Name / Initials',
                               help='Patient the complaint concerns (initials encouraged).')
    patient_deceased = fields.Boolean(string='Patient Deceased',
                                      help='Triggers next-of-kin/executor authority handling.')
    subject_id = fields.Many2one('nhs.complaint.subject', string='Subject (KO41a)', required=True,
                                 help='KO41a-aligned subject. Two-level taxonomy for the annual return.')
    location_id = fields.Many2one('nhs.location', string='Location / Service',
                                  help='Where the matter occurred (inherited NHS location model).')
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('major', 'Major'),
    ], string='Severity / Complexity', required=True, default='low', tracking=True,
       help='Drives the suggested response timescale and prioritisation.')
    is_multi_org = fields.Boolean(string='Multi-Organisation Complaint',
                                  help='Complaint spans more than one NHS provider (joint response required).')
    partner_org_ids = fields.Many2many(
        'res.partner',
        'nhs_complaint_partner_org_rel', 'complaint_id', 'partner_id',
        string='Partner Organisations',
        help='Other NHS organisations involved in this complaint. Each must contribute to the joint response.',
    )
    lead_org_id = fields.Many2one(
        'res.partner', string='Lead Organisation',
        help='The organisation responsible for coordinating the joint response.',
    )
    multi_org_deadline_agreed = fields.Boolean(
        string='Timescale Agreed with All Organisations',
        help='Confirms the response deadline has been agreed with all partner organisations.',
    )
    org_response_ids = fields.One2many(
        'nhs.complaint.org.response', 'complaint_id',
        string='Organisation Response Contributions',
    )
    all_orgs_responded = fields.Boolean(
        string='All Organisations Responded',
        compute='_compute_all_orgs_responded', store=True,
        help='True when every partner organisation has submitted their response contribution.',
    )
    linked_incident_ids = fields.Many2many(
        'nhs.incident',
        'nhs_complaint_incident_rel', 'complaint_id', 'incident_id',
        string='Linked Incidents',
        help='Incidents this complaint revealed or relates to.',
    )
    linked_risk_ids = fields.Many2many('nhs.risk', string='Linked Risks',
                                       help='Systemic risks evidenced by this complaint.')
    duty_of_candour_flag = fields.Boolean(string='Duty of Candour Applies',
                                          help='Set when the complaint involves a notifiable safety incident; '
                                               'links to the incident module DoC engine.')
    acknowledged = fields.Boolean(string='Acknowledged', tracking=True,
                                  help='Acknowledgement sent? Formal complaints only.')
    acknowledged_at = fields.Datetime(string='Acknowledged At', tracking=True)
    ack_deadline = fields.Date(string='Acknowledgement Deadline',
                               compute='_compute_ack_deadline', store=True,
                               help='received_at + 3 working days (inherited engine). Statutory deadline.')
    timescale_id = fields.Many2one('nhs.complaint.timescale', string='Response Timescale Preset',
                                   default=lambda self: self._default_timescale_id(),
                                   help='Chosen timescale preset (e.g. 40 working days). Drives response_deadline default.')
    response_deadline = fields.Date(string='Agreed Response Deadline', tracking=True,
                                    help='The agreed response deadline. Defaults from timescale preset but editable per case.')
    response_deadline_agreed = fields.Boolean(string='Deadline Agreed with Complainant',
                                              help='Confirms the deadline was actually agreed with the complainant.')
    state = fields.Selection([
        ('received', 'Received'),
        # PALS pathway
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        # Formal complaint pathway
        ('acknowledged', 'Acknowledged'),
        ('investigation', 'Under Investigation'),
        ('response_draft', 'Response Draft'),
        ('awaiting_signoff', 'Awaiting Sign-off'),
        ('response_sent', 'Response Sent'),
        # Shared terminal / exception states
        ('closed', 'Closed'),
        ('re_opened', 'Re-opened'),
        ('phso', 'PHSO Referred'),
        ('withdrawn', 'Withdrawn'),
        ('escalated', 'Escalated to Complaint'),
    ], string='Status', required=True, default='received', tracking=True)
    handler_id = fields.Many2one('res.users', string='Case Handler', tracking=True,
                                 help='Assigned complaints handler / case officer.')
    investigation_id = fields.Many2one('nhs.complaint.investigation', string='Investigation',
                                       help='Investigation record (formal complaints).')
    investigation_lead_investigator_id = fields.Many2one('res.users',
                                                         related='investigation_id.lead_investigator_id',
                                                         readonly=False, string='Lead Investigator')
    investigation_state = fields.Selection(related='investigation_id.state', readonly=False,
                                           string='Investigation Status')
    investigation_department_input_ids = fields.Many2many('res.users',
                                                          related='investigation_id.department_input_ids',
                                                          readonly=False, string='Staff Providing Input')
    investigation_upheld_status = fields.Selection(related='investigation_id.upheld_status',
                                                   readonly=False, string='Overall Outcome')
    investigation_points_of_complaint = fields.Text(related='investigation_id.points_of_complaint',
                                                    readonly=False, string='Points of Complaint')
    investigation_findings = fields.Text(related='investigation_id.findings', readonly=False, string='Investigation Findings')
    investigation_lessons_learned = fields.Text(related='investigation_id.lessons_learned', readonly=False,
                                                string='Lessons Learned')
    investigation_timeline_ids = fields.One2many('nhs.complaint.investigation.timeline',
                                                 related='investigation_id.timeline_ids',
                                                 readonly=False, string='Chronology')
    correspondence_ids = fields.One2many('nhs.complaint.correspondence', 'complaint_id',
                                         string='Correspondence Log')
    response_text = fields.Html(string='Draft Response',
                                help='Drafted written response body — feeds the QWeb response letter.')
    signed_off_by_id = fields.Many2one('res.users', string='Signed Off By', tracking=True,
                                       help='CEO / senior sign-off. Response cannot be sent until set.')
    signed_off_at = fields.Datetime(string='Signed Off At')
    response_sent_at = fields.Datetime(string='Response Sent At', tracking=True)
    response_method = fields.Selection([
        ('letter', 'Letter'),
        ('email', 'Email'),
    ], string='Response Method')
    phso_id = fields.Many2one('nhs.complaint.phso', string='PHSO Record',
                              help='PHSO escalation record — created when escalated to the Ombudsman.')
    action_ids = fields.One2many('nhs.action', 'complaint_id', string='Learning Actions')
    pals_origin_ref = fields.Char(string='Original PALS Reference',
                                  help='Retained when a PALS concern is escalated into this formal complaint.')
    deescalated = fields.Boolean(string='De-escalated',
                                 help='PALS concern resolved informally — a PALS performance metric.')
    reopened_count = fields.Integer(string='Times Re-opened', default=0)
    closed_at = fields.Datetime(string='Closed At')
    days_to_respond = fields.Integer(string='Working Days to Respond',
                                     compute='_compute_days_to_respond', store=True,
                                     help='Working-day duration received → response sent. Headline KPI.')
    satisfaction_rating = fields.Selection([
        ('very_dissatisfied', 'Very Dissatisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('neutral', 'Neutral'),
        ('satisfied', 'Satisfied'),
        ('very_satisfied', 'Very Satisfied'),
    ], string='Complainant Satisfaction', help='Optional post-closure satisfaction rating.')
    ack_overdue = fields.Boolean(string='Acknowledgement Overdue',
                                 compute='_compute_overdue_flags', store=True)
    response_overdue = fields.Boolean(string='Response Overdue',
                                      compute='_compute_overdue_flags', store=True)
    incident_count = fields.Integer(compute='_compute_incident_count', string='Incidents')
    risk_count = fields.Integer(compute='_compute_risk_count', string='Risks')
    correspondence_count = fields.Integer(compute='_compute_correspondence_count', string='Correspondence')
    action_count = fields.Integer(compute='_compute_action_count', string='Actions')
    doc_warning = fields.Selection([
        ('no_incident', 'No Incident Linked'),
        ('no_doc', 'No DoC Record on Incident'),
        ('ok', 'DoC Record Exists'),
    ], compute='_compute_doc_warning', string='DoC Warning')
    doc_state_summary = fields.Char(compute='_compute_doc_warning', string='DoC Status')

    def _default_timescale_id(self):
        """Return the company-configured default response timescale id, or False if none is set."""
        param = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_complaints.default_timescale_id')
        return int(param) if param else False

    @api.depends('event_date', 'received_at')
    def _compute_within_time_limit(self):
        """Flag whether the complaint was received within 12 months of the event date."""
        for rec in self:
            if rec.event_date and rec.received_at:
                limit = rec.event_date + timedelta(days=366)
                rec.within_time_limit = rec.received_at.date() <= limit
            else:
                rec.within_time_limit = True

    @api.depends('received_at', 'record_type')
    def _compute_ack_deadline(self):
        """Set the acknowledgement deadline to 3 working days after receipt for formal complaints."""
        for rec in self:
            if rec.record_type == 'complaint' and rec.received_at:
                rec.ack_deadline = self._add_working_days(rec.received_at.date(), 3)
            else:
                rec.ack_deadline = False

    @api.depends('ack_deadline', 'acknowledged', 'state', 'response_deadline')
    def _compute_overdue_flags(self):
        """Flag whether the acknowledgement or response deadline has passed without the corresponding step being completed."""
        today = fields.Date.today()
        for rec in self:
            rec.ack_overdue = bool(
                rec.ack_deadline and rec.ack_deadline < today
                and not rec.acknowledged and rec.state == 'received'
            )
            rec.response_overdue = bool(
                rec.response_deadline and rec.response_deadline < today
                and rec.state not in ('response_sent', 'closed', 'withdrawn')
            )

    @api.depends('received_at', 'response_sent_at')
    def _compute_days_to_respond(self):
        """Calculate the working-day duration between receipt and the response being sent."""
        for rec in self:
            if rec.received_at and rec.response_sent_at:
                rec.days_to_respond = self._count_working_days(
                    rec.received_at.date(), rec.response_sent_at.date())
            else:
                rec.days_to_respond = 0

    def _add_working_days(self, start_date, days):
        """Return the date reached by adding the given number of working days (excluding weekends and holidays) to start_date."""
        holidays = self._get_holidays()
        current = start_date
        added = 0
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5 and current not in holidays:
                added += 1
        return current

    def _count_working_days(self, start_date, end_date):
        """Count the number of working days (excluding weekends and holidays) between start_date and end_date."""
        if end_date <= start_date:
            return 0
        holidays = self._get_holidays()
        count = 0
        current = start_date
        while current < end_date:
            current += timedelta(days=1)
            if current.weekday() < 5 and current not in holidays:
                count += 1
        return count

    def _get_holidays(self):
        """Return the set of holiday dates applicable to the current company (or all companies)."""
        holiday_records = self.env['nhs.holiday'].search([
            ('company_id', 'in', [self.env.company.id, False])
        ])
        return {h.date for h in holiday_records}

    @api.depends(
        'duty_of_candour_flag', 'linked_incident_ids',
        'linked_incident_ids.doc_id', 'linked_incident_ids.doc_id.state',
    )
    def _compute_doc_warning(self):
        """Derive the Duty of Candour warning badge and status summary from the complaint's linked incidents."""
        state_labels = {'open': 'Open', 'overdue': 'Overdue', 'complete': 'Complete'}
        for rec in self:
            if not rec.duty_of_candour_flag:
                rec.doc_warning = False
                rec.doc_state_summary = False
                continue
            if not rec.linked_incident_ids:
                rec.doc_warning = 'no_incident'
                rec.doc_state_summary = False
                continue
            doc_incident = rec.linked_incident_ids.filtered(lambda i: i.doc_id)
            if not doc_incident:
                rec.doc_warning = 'no_doc'
                rec.doc_state_summary = False
            else:
                inc = doc_incident[0]
                doc_state = inc.doc_id.state
                label = state_labels.get(doc_state, doc_state or 'Unknown')
                rec.doc_warning = 'ok'
                rec.doc_state_summary = f"{inc.name} — {label}"

    @api.depends('linked_incident_ids')
    def _compute_incident_count(self):
        """Set the count of incidents linked to this complaint."""
        for rec in self:
            rec.incident_count = len(rec.linked_incident_ids)

    @api.depends('linked_risk_ids')
    def _compute_risk_count(self):
        """Set the count of risks linked to this complaint."""
        for rec in self:
            rec.risk_count = len(rec.linked_risk_ids)

    @api.depends('correspondence_ids')
    def _compute_correspondence_count(self):
        """Set the count of correspondence log entries for this complaint."""
        for rec in self:
            rec.correspondence_count = len(rec.correspondence_ids)

    @api.depends('action_ids')
    def _compute_action_count(self):
        """Set the count of learning actions linked to this complaint."""
        for rec in self:
            rec.action_count = len(rec.action_ids)

    @api.depends('org_response_ids', 'org_response_ids.state', 'is_multi_org')
    def _compute_all_orgs_responded(self):
        """Flag whether every partner organisation has submitted its response contribution for a multi-org complaint."""
        for rec in self:
            if not rec.is_multi_org or not rec.org_response_ids:
                rec.all_orgs_responded = False
            else:
                rec.all_orgs_responded = all(
                    r.state == 'submitted' for r in rec.org_response_ids
                )

    def _sync_org_responses(self):
        """Create/remove org response lines to mirror partner_org_ids."""
        existing = {r.org_id.id: r for r in self.org_response_ids}
        current_ids = set(self.partner_org_ids.ids)
        existing_ids = set(existing.keys())
        for pid in current_ids - existing_ids:
            self.env['nhs.complaint.org.response'].create({
                'complaint_id': self.id,
                'org_id': pid,
            })
        for pid in existing_ids - current_ids:
            rec = existing[pid]
            if rec.state == 'pending':
                rec.unlink()

    # ── Lifecycle create
    @api.model_create_multi
    def create(self, vals_list):
        """Assign a PALS/formal-complaint sequence reference, schedule an assignment activity for the handler, and sync org response lines for new multi-org complaints."""
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                record_type = vals.get('record_type') or self.env.context.get('default_record_type') or 'pals'
                code = 'nhs.complaint.formal' if record_type == 'complaint' else 'nhs.complaint.pals'
                vals['name'] = seq.next_by_code(code) or 'New'
        records = super().create(vals_list)
        for rec in records:
            if rec.handler_id:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      user_id=rec.handler_id.id,
                                      note=f'New case assigned: {rec.name}')
            if rec.is_multi_org and rec.partner_org_ids:
                rec._sync_org_responses()
        return records

    def write(self, vals):
        """Block direct state changes outside the workflow actions and resync org response lines when partner organisations change."""
        if 'state' in vals and not self.env.context.get('nhs_workflow'):
            raise UserError('Complaint status must be changed through the workflow action buttons.')
        result = super().write(vals)
        if 'partner_org_ids' in vals and not self.env.context.get('skip_org_sync'):
            for rec in self:
                if rec.is_multi_org:
                    rec._sync_org_responses()
        return result

    @api.onchange('complainant_id')
    def _onchange_complainant_populate(self):
        """Copy the linked complainant's name, email, phone and relationship onto the complaint's inline fields."""
        if self.complainant_id:
            self.complainant_name = self.complainant_id.name
            self.complainant_email = self.complainant_id.email
            self.complainant_phone = self.complainant_id.phone
            self.complainant_relationship = self.complainant_id.relationship_to_patient

    @api.onchange('is_multi_org')
    def _onchange_is_multi_org(self):
        """Default the negotiated timescale and lead organisation when flagged multi-org, or clear multi-org fields when unflagged."""
        if self.is_multi_org:
            if not self.timescale_id:
                preset = self.env.ref(
                    'odoo_nhs_complaints.timescale_major_negotiated',
                    raise_if_not_found=False,
                )
                if preset:
                    self.timescale_id = preset
            if not self.lead_org_id:
                self.lead_org_id = self.env.company.partner_id
        else:
            self.partner_org_ids = [(5, 0, 0)]
            self.lead_org_id = False
            self.multi_org_deadline_agreed = False

    # ── Constraints
    @api.constrains('received_at')
    def _check_received_at(self):
        """Reject a received date/time set in the future."""
        now = fields.Datetime.now()
        for rec in self:
            if rec.received_at and rec.received_at > now:
                raise ValidationError('Received date cannot be in the future.')

    # Complainant is required to acknowledge (not on initial save) so staff
    # can log the intake record first and add complainant details before progressing.

    @api.constrains('is_third_party', 'consent_status')
    def _check_consent(self):
        """Require a real consent status whenever the complainant is a third-party representative."""
        for rec in self:
            if rec.is_third_party and rec.consent_status == 'not_required':
                raise ValidationError("Please set a consent status when the complainant is acting on behalf of someone else.")

    def unlink(self):
        """Prevent deletion of statutory complaint records, directing users to archive or withdraw instead."""
        raise UserError(
            'Statutory complaint records cannot be deleted. '
            'Archive or withdraw the record instead.'
        )

    # ── Workflow actions
    def action_acknowledge(self):
        """Create the complainant record if needed, send the acknowledgement email/letter, and mark the complaint acknowledged."""
        for rec in self:
            if rec.record_type != 'complaint':
                raise UserError('Acknowledgement applies to formal complaints only.')
            if not rec.is_anonymous:
                if not rec.complainant_id and not rec.complainant_name:
                    raise UserError(
                        'Please enter the complainant\'s name on the "Complainant & Consent" tab '
                        'before acknowledging.'
                    )
                if not rec.complainant_id and rec.complainant_name:
                    complainant = self.env['nhs.complainant'].create({
                        'name': rec.complainant_name,
                        'email': rec.complainant_email or False,
                        'phone': rec.complainant_phone or False,
                        'relationship_to_patient': rec.complainant_relationship or 'self',
                    })
                    rec.write({'complainant_id': complainant.id})
            rec.with_context(nhs_workflow=True).write({
                'state': 'acknowledged',
                'acknowledged': True,
                'acknowledged_at': fields.Datetime.now(),
            })
            template = self.env.ref('odoo_nhs_complaints.mail_template_complaint_ack', raise_if_not_found=False)
            if template:
                template.send_mail(rec.id, force_send=False)
            rec.correspondence_ids.create({
                'complaint_id': rec.id,
                'direction': 'outbound',
                'channel': 'letter',
                'correspondence_type': 'acknowledgement',
                'occurred_at': fields.Datetime.now(),
                'summary': f'Acknowledgement sent for {rec.name}',
                'user_id': self.env.user.id,
            })

    def action_agree_timescale(self, timescale_id=False, deadline=False):
        """Move the complaint to Under Investigation, applying the given timescale preset or explicit deadline."""
        for rec in self:
            vals = {'state': 'investigation'}
            if timescale_id:
                vals['timescale_id'] = timescale_id
            if deadline:
                vals['response_deadline'] = deadline
                vals['response_deadline_agreed'] = True
            elif timescale_id:
                preset = self.env['nhs.complaint.timescale'].browse(timescale_id)
                vals['response_deadline'] = rec._add_working_days(fields.Date.today(), preset.working_days)
            rec.with_context(nhs_workflow=True).write(vals)

    def action_start_investigation(self):
        """Move the complaint to Under Investigation, auto-creating the investigation record if one doesn't exist."""
        for rec in self:
            vals = {'state': 'investigation'}
            if not rec.investigation_id:
                # Automatically create the investigation record
                investigation = self.env['nhs.complaint.investigation'].create({
                    'complaint_id': rec.id,
                    'lead_investigator_id': rec.handler_id.id or self.env.user.id,
                    'state': 'draft',
                })
                vals['investigation_id'] = investigation.id
            rec.with_context(nhs_workflow=True).write(vals)

    def action_submit_response_draft(self):
        """Handler saves the drafted response text → moves to response_draft for review."""
        for rec in self:
            if not rec.response_text:
                raise UserError('Please enter a draft response before saving the draft.')
            rec.with_context(nhs_workflow=True).write({'state': 'response_draft'})

    def action_submit_for_signoff(self):
        """Draft reviewed — formally submitted to CEO/delegate for sign-off."""
        for rec in self:
            if not rec.response_text:
                raise UserError('A draft response must be present before submitting for sign-off.')
            if rec.is_third_party and rec.consent_status in ('pending', 'refused'):
                raise UserError('Cannot submit for sign-off: consent for this third-party complaint has not been obtained.')
            if rec.is_multi_org and not rec.org_response_ids:
                raise UserError(
                    'This is a Multi-Organisation Complaint. '
                    'Please add at least one partner organisation on the "Multi-Organisation" '
                    'tab before submitting for sign-off.'
                )
            if rec.is_multi_org and not rec.multi_org_deadline_agreed:
                raise UserError(
                    'Multi-Organisation Complaint: please confirm the response timescale has been agreed '
                    'with all partner organisations before submitting for sign-off.'
                )
            if rec.is_multi_org and not rec.all_orgs_responded:
                pending = rec.org_response_ids.filtered(lambda r: r.state == 'pending')
                names = ', '.join(pending.mapped('org_id.name'))
                raise UserError(
                    f'Multi-Organisation Complaint: the following organisations have not yet submitted '
                    f'their response contribution: {names}. '
                    f'Please ensure all contributions are submitted on the "Multi-Organisation" tab.'
                )
            rec.with_context(nhs_workflow=True).write({'state': 'awaiting_signoff'})

    def action_sign_off(self):
        """CEO / quality-lead delegate stamps sign-off; response can then be sent."""
        for rec in self:
            if rec.is_third_party and rec.consent_status in ('pending', 'refused'):
                raise UserError('Cannot sign off: consent for this third-party complaint has not been obtained.')
            if not rec.response_text:
                raise UserError('There is no response text to sign off.')
            rec.with_context(nhs_workflow=True).write({
                'signed_off_by_id': self.env.user.id,
                'signed_off_at': fields.Datetime.now(),
            })

    def action_send_response(self):
        """Send the signed-off response to the complainant, log the outbound correspondence, and notify partner organisations if multi-org."""
        for rec in self:
            if not rec.signed_off_by_id:
                raise UserError('The response must be signed off before it can be sent.')
            if rec.is_third_party and rec.consent_status in ('pending', 'refused'):
                raise UserError('Cannot send response: consent for this third-party complaint has not been obtained.')
            rec.with_context(nhs_workflow=True).write({
                'state': 'response_sent',
                'response_sent_at': fields.Datetime.now(),
            })
            template = self.env.ref('odoo_nhs_complaints.mail_template_complaint_response',
                                    raise_if_not_found=False)
            if template:
                template.send_mail(rec.id, force_send=False)
            rec.correspondence_ids.create({
                'complaint_id': rec.id,
                'direction': 'outbound',
                'channel': rec.response_method or 'letter',
                'correspondence_type': 'response',
                'occurred_at': fields.Datetime.now(),
                'summary': f'Final response sent for {rec.name}',
                'user_id': self.env.user.id,
            })
            if rec.is_multi_org:
                rec._notify_partner_orgs()

    def _notify_partner_orgs(self):
        """Send the final joint response notification to all partner organisations."""
        for org in self.partner_org_ids.filtered(lambda t: t.email):
            self.env['mail.mail'].sudo().create({
                'subject': f'Joint Response — {self.name} ({self.subject_summary})',
                'email_to': org.email,
                'body_html': (
                    f'<p>Dear {org.name} Complaints Team,</p>'
                    f'<p>The formal response for multi-organisation complaint '
                    f'<strong>{self.name}</strong> has now been issued to the complainant.</p>'
                    f'<p><strong>Complaint:</strong> {self.subject_summary}<br/>'
                    f'<strong>Lead Organisation:</strong> {self.lead_org_id.name or self.company_id.name}</p>'
                    f'<p>Please retain this notification for your records.</p>'
                    f'<p>Regards,<br/>Complaints Team — {self.company_id.name}</p>'
                ),
                'auto_delete': True,
            }).send()
        if self.partner_org_ids.filtered(lambda t: t.email):
            self.message_post(
                body=(
                    f'Joint response notification sent to: '
                    + ', '.join(self.partner_org_ids.filtered(lambda t: t.email).mapped('name'))
                )
            )

    def action_close(self):
        """Close the complaint, requiring a sent response for formal complaints and no open learning actions."""
        for rec in self:
            if rec.record_type == 'complaint' and not rec.response_sent_at:
                raise UserError('A formal complaint must have a response sent before it can be closed.')
            open_actions = rec.action_ids.filtered(lambda a: a.state not in ('done', 'cancelled'))
            if open_actions:
                raise UserError(f'There are {len(open_actions)} open action(s) — resolve them before closing.')
            rec.with_context(nhs_workflow=True).write({
                'state': 'closed',
                'closed_at': fields.Datetime.now(),
            })

    def action_reopen(self, reason=''):
        """Re-open the complaint, increment its reopened count, and post the reason to the chatter."""
        for rec in self:
            rec.with_context(nhs_workflow=True).write({
                'state': 're_opened',
                'reopened_count': rec.reopened_count + 1,
            })
            rec.message_post(body=f'Complaint re-opened. Reason: {reason or "Not stated"}')

    def action_withdraw(self):
        """Move the complaint to the Withdrawn state."""
        for rec in self:
            rec.with_context(nhs_workflow=True).write({'state': 'withdrawn'})

    def action_escalate_phso(self):
        """Create a PHSO escalation record and move the complaint to the PHSO Referred state."""
        for rec in self:
            phso = self.env['nhs.complaint.phso'].create({
                'complaint_id': rec.id,
                'referred_at': fields.Date.today(),
            })
            rec.with_context(nhs_workflow=True).write({'state': 'phso', 'phso_id': phso.id})

    def action_escalate_to_complaint(self):
        """Open the wizard to escalate this PALS concern into a formal complaint."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Escalate to Formal Complaint',
            'res_model': 'nhs.complaint.escalate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_pals_id': self.id},
        }

    def action_pals_in_progress(self):
        """Move a PALS concern to the In Progress state."""
        for rec in self:
            if rec.record_type != 'pals':
                raise UserError('This action is only for PALS concerns.')
            rec.with_context(nhs_workflow=True).write({'state': 'in_progress'})

    def action_pals_resolve(self):
        """Mark a PALS concern as Resolved and flag it as de-escalated."""
        for rec in self:
            if rec.record_type != 'pals':
                raise UserError('This action is only for PALS concerns.')
            rec.with_context(nhs_workflow=True).write({
                'state': 'resolved',
                'deescalated': True,
            })


    def action_create_incident(self):
        """Open the wizard to link or create an incident record for this complaint."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Link / Create Incident',
            'res_model': 'nhs.complaint.link.incident.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_complaint_id': self.id},
        }

    def action_open_response_wizard(self):
        """Open the wizard to draft and sign off the complaint response."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Draft & Sign Off Response',
            'res_model': 'nhs.complaint.response.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_complaint_id': self.id},
        }

    def action_open_response_view_wizard(self):
        """Open the read-only wizard showing the complaint's response details."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Response Details',
            'res_model': 'nhs.complaint.response.view.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_complaint_id': self.id},
        }

    def action_open_investigation(self):
        """Open the linked investigation record's form view, or return False if none exists."""
        self.ensure_one()
        if not self.investigation_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Investigation',
            'res_model': 'nhs.complaint.investigation',
            'view_mode': 'form',
            'res_id': self.investigation_id.id,
            'target': 'current',
        }

    def action_view_incidents(self):
        """Open the list/form view of incidents linked to this complaint."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Linked Incidents',
            'res_model': 'nhs.incident',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.linked_incident_ids.ids)],
        }

    def action_view_actions(self):
        """Open the list/form view of learning actions raised from this complaint."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Learning Actions',
            'res_model': 'nhs.action',
            'view_mode': 'list,form',
            'domain': [('complaint_id', '=', self.id)],
            'context': {'default_complaint_id': self.id},
        }

    def action_view_correspondence(self):
        """Open the list/form view of correspondence log entries for this complaint."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Correspondence',
            'res_model': 'nhs.complaint.correspondence',
            'view_mode': 'list,form',
            'domain': [('complaint_id', '=', self.id)],
            'context': {'default_complaint_id': self.id},
        }

    # ── Cron helpers
    @api.model
    def _cron_ack_deadline(self):
        """Schedule overdue or due-soon acknowledgement activities for unacknowledged formal complaints."""
        today = fields.Date.today()
        soon = today + timedelta(days=1)
        complaints = self.search([
            ('record_type', '=', 'complaint'),
            ('state', '=', 'received'),
            ('acknowledged', '=', False),
        ])
        for rec in complaints:
            if not rec.ack_deadline:
                continue
            if rec.ack_deadline < today:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      user_id=rec.handler_id.id if rec.handler_id else self.env.user.id,
                                      note=f'OVERDUE acknowledgement for {rec.name} (deadline: {rec.ack_deadline})')
            elif rec.ack_deadline <= soon:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      user_id=rec.handler_id.id if rec.handler_id else self.env.user.id,
                                      note=f'Acknowledgement due today for {rec.name}')

    @api.model
    def _cron_response_deadline(self):
        """Schedule overdue or upcoming-deadline response activities for open formal complaints."""
        today = fields.Date.today()
        warn_dates = [today + timedelta(days=d) for d in (2, 5)]
        complaints = self.search([
            ('record_type', '=', 'complaint'),
            ('state', 'not in', ['response_sent', 'closed', 'withdrawn']),
            ('response_deadline', '!=', False),
        ])
        for rec in complaints:
            if not rec.response_deadline:
                continue
            if rec.response_deadline < today:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      user_id=rec.handler_id.id if rec.handler_id else self.env.user.id,
                                      note=f'OVERDUE response for {rec.name} (deadline: {rec.response_deadline})')
            elif rec.response_deadline in warn_dates:
                days_left = (rec.response_deadline - today).days
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      user_id=rec.handler_id.id if rec.handler_id else self.env.user.id,
                                      note=f'Response due in {days_left} day(s) for {rec.name}')

    @api.model
    def _cron_anonymise_closed(self):
        """Anonymise the patient and complainant details of complaints closed longer ago than the configured retention period."""
        years = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_complaints.anonymise_after_years', 0))
        if not years:
            return
        cutoff = fields.Date.today() - timedelta(days=years * 365)
        old_complaints = self.search([
            ('state', '=', 'closed'),
            ('closed_at', '<=', fields.Datetime.from_string(str(cutoff))),
            ('complainant_id', '!=', False),
        ])
        for rec in old_complaints:
            rec.with_context(nhs_workflow=True).write({
                'patient_name': 'ANONYMISED',
                'consent_evidence_ref': False,
            })
            if rec.complainant_id:
                rec.complainant_id.write({
                    'name': 'ANONYMISED',
                    'email': False,
                    'phone': False,
                    'address': False,
                })
