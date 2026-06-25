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
#############################################################################
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class NhsComplaint(models.Model):
    _name = 'nhs.complaint'
    _description = 'PALS Concern or Formal NHS Complaint'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_at desc, id desc'
    _rec_name = 'name'

    # ── Identification ────────────────────────────────────────────────
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

    # ── Complainant & Consent ─────────────────────────────────────────
    complainant_id = fields.Many2one('nhs.complainant', string='Complainant', tracking=True,
                                     help='The person making the complaint. Required for formal complaints.')
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

    # ── Classification ────────────────────────────────────────────────
    subject_id = fields.Many2one('nhs.complaint.subject', string='Subject (KO41a)', required=True,
                                 help='KO41a-aligned subject. Two-level taxonomy for the annual return.')
    location_id = fields.Many2one('nhs.location', string='Location / Service',
                                  help='Where the matter occurred (inherited NHS location model).')
    department_text = fields.Char(string='Department / Service (free text)',
                                  help='Service/department when not a formal location in the hierarchy.')
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('major', 'Major'),
    ], string='Severity / Complexity', required=True, default='low', tracking=True,
       help='Drives the suggested response timescale and prioritisation.')
    is_multi_org = fields.Boolean(string='Multi-Organisation Complaint',
                                  help='Complaint spans more than one NHS provider (joint response required).')
    linked_incident_ids = fields.Many2many('nhs.incident', string='Linked Incidents',
                                           help='Incidents this complaint revealed or relates to.')
    linked_risk_ids = fields.Many2many('nhs.risk', string='Linked Risks',
                                       help='Systemic risks evidenced by this complaint.')
    duty_of_candour_flag = fields.Boolean(string='Duty of Candour Applies',
                                          help='Set when the complaint involves a notifiable safety incident; '
                                               'links to the incident module DoC engine.')

    # ── Deadline fields ───────────────────────────────────────────────
    acknowledged = fields.Boolean(string='Acknowledged', tracking=True,
                                  help='Acknowledgement sent? Formal complaints only.')
    acknowledged_at = fields.Datetime(string='Acknowledged At', tracking=True)
    ack_deadline = fields.Date(string='Acknowledgement Deadline',
                               compute='_compute_ack_deadline', store=True,
                               help='received_at + 3 working days (inherited engine). Statutory deadline.')
    timescale_id = fields.Many2one('nhs.complaint.timescale', string='Response Timescale Preset',
                                   help='Chosen timescale preset (e.g. 40 working days). Drives response_deadline default.')
    response_deadline = fields.Date(string='Agreed Response Deadline', tracking=True,
                                    help='The agreed response deadline. Defaults from timescale preset but editable per case.')
    response_deadline_agreed = fields.Boolean(string='Deadline Agreed with Complainant',
                                              help='Confirms the deadline was actually agreed with the complainant.')

    # ── Workflow & Response ───────────────────────────────────────────
    state = fields.Selection([
        ('received', 'Received'),
        ('acknowledged', 'Acknowledged'),
        ('investigation', 'Under Investigation'),
        ('response_draft', 'Response Draft'),
        ('awaiting_signoff', 'Awaiting Sign-off'),
        ('response_sent', 'Response Sent'),
        ('closed', 'Closed'),
        ('re_opened', 'Re-opened'),
        ('phso', 'PHSO Referred'),
        ('withdrawn', 'Withdrawn'),
        # PALS-specific
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated to Complaint'),
    ], string='Status', required=True, default='received', tracking=True)
    handler_id = fields.Many2one('res.users', string='Case Handler', tracking=True,
                                 help='Assigned complaints handler / case officer.')
    investigation_id = fields.Many2one('nhs.complaint.investigation', string='Investigation',
                                       help='Investigation record (formal complaints).')
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

    # ── Overdue flags (used in list decorations) ──────────────────────
    ack_overdue = fields.Boolean(string='Acknowledgement Overdue',
                                 compute='_compute_overdue_flags', store=False)
    response_overdue = fields.Boolean(string='Response Overdue',
                                      compute='_compute_overdue_flags', store=False)

    # ── Smart button counts ───────────────────────────────────────────
    incident_count = fields.Integer(compute='_compute_incident_count', string='Incidents')
    risk_count = fields.Integer(compute='_compute_risk_count', string='Risks')
    correspondence_count = fields.Integer(compute='_compute_correspondence_count', string='Correspondence')
    action_count = fields.Integer(compute='_compute_action_count', string='Actions')

    # ── Computed helpers ──────────────────────────────────────────────
    @api.depends('event_date', 'received_at')
    def _compute_within_time_limit(self):
        for rec in self:
            if rec.event_date and rec.received_at:
                limit = rec.event_date + timedelta(days=366)
                rec.within_time_limit = rec.received_at.date() <= limit
            else:
                rec.within_time_limit = True

    @api.depends('received_at', 'record_type')
    def _compute_ack_deadline(self):
        for rec in self:
            if rec.record_type == 'complaint' and rec.received_at:
                rec.ack_deadline = self._add_working_days(rec.received_at.date(), 3)
            else:
                rec.ack_deadline = False

    @api.depends('ack_deadline', 'acknowledged', 'state', 'response_deadline')
    def _compute_overdue_flags(self):
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
        for rec in self:
            if rec.received_at and rec.response_sent_at:
                rec.days_to_respond = self._count_working_days(
                    rec.received_at.date(), rec.response_sent_at.date())
            else:
                rec.days_to_respond = 0

    def _add_working_days(self, start_date, days):
        holidays = self._get_holidays()
        current = start_date
        added = 0
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5 and current not in holidays:
                added += 1
        return current

    def _count_working_days(self, start_date, end_date):
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
        holiday_records = self.env['nhs.holiday'].search([
            ('company_id', 'in', [self.env.company.id, False])
        ])
        return {h.date for h in holiday_records}

    @api.depends('linked_incident_ids')
    def _compute_incident_count(self):
        for rec in self:
            rec.incident_count = len(rec.linked_incident_ids)

    @api.depends('linked_risk_ids')
    def _compute_risk_count(self):
        for rec in self:
            rec.risk_count = len(rec.linked_risk_ids)

    @api.depends('correspondence_ids')
    def _compute_correspondence_count(self):
        for rec in self:
            rec.correspondence_count = len(rec.correspondence_ids)

    @api.depends('action_ids')
    def _compute_action_count(self):
        for rec in self:
            rec.action_count = len(rec.action_ids)

    # ── Lifecycle create ──────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                record_type = vals.get('record_type', 'pals')
                code = 'nhs.complaint.formal' if record_type == 'complaint' else 'nhs.complaint.pals'
                vals['name'] = seq.next_by_code(code) or 'New'
        records = super().create(vals_list)
        for rec in records:
            if rec.handler_id:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      user_id=rec.handler_id.id,
                                      note=f'New case assigned: {rec.name}')
        return records

    # ── Constraints ───────────────────────────────────────────────────
    @api.constrains('received_at')
    def _check_received_at(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.received_at and rec.received_at > now:
                raise ValidationError('Received date cannot be in the future.')

    @api.constrains('record_type', 'complainant_id', 'is_anonymous')
    def _check_complainant_required(self):
        for rec in self:
            if rec.record_type == 'complaint' and not rec.complainant_id and not rec.is_anonymous:
                raise ValidationError('A complainant record is required for formal complaints.')

    @api.constrains('is_third_party', 'consent_status')
    def _check_consent(self):
        for rec in self:
            if rec.is_third_party and rec.consent_status == 'not_required':
                raise ValidationError("Please set a consent status when the complainant is acting on behalf of someone else.")

    # ── State guard ───────────────────────────────────────────────────
    def write(self, vals):
        if 'state' in vals and not self.env.context.get('nhs_workflow'):
            raise UserError('Complaint status must be changed through the workflow action buttons.')
        return super().write(vals)

    def unlink(self):
        raise UserError(
            'Statutory complaint records cannot be deleted. '
            'Archive or withdraw the record instead.'
        )

    # ── Workflow actions ──────────────────────────────────────────────
    def action_acknowledge(self):
        for rec in self:
            if rec.record_type != 'complaint':
                raise UserError('Acknowledgement applies to formal complaints only.')
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
        for rec in self:
            rec.with_context(nhs_workflow=True).write({'state': 'investigation'})

    def action_submit_response_draft(self):
        for rec in self:
            if not rec.response_text:
                raise UserError('Please enter a draft response before submitting for sign-off.')
            rec.with_context(nhs_workflow=True).write({'state': 'awaiting_signoff'})

    def action_sign_off(self):
        for rec in self:
            if rec.is_third_party and rec.consent_status in ('pending', 'refused'):
                raise UserError('Cannot sign off: consent for this third-party complaint has not been obtained.')
            rec.with_context(nhs_workflow=True).write({
                'state': 'awaiting_signoff',
                'signed_off_by_id': self.env.user.id,
                'signed_off_at': fields.Datetime.now(),
            })

    def action_send_response(self):
        for rec in self:
            if not rec.signed_off_by_id:
                raise UserError('The response must be signed off before it can be sent.')
            if rec.is_third_party and rec.consent_status in ('pending', 'refused'):
                raise UserError('Cannot send response: consent for this third-party complaint has not been obtained.')
            rec.with_context(nhs_workflow=True).write({
                'state': 'response_sent',
                'response_sent_at': fields.Datetime.now(),
            })
            template = self.env.ref('odoo_nhs_complaints.mail_template_complaint_response', raise_if_not_found=False)
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

    def action_close(self):
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
        for rec in self:
            rec.with_context(nhs_workflow=True).write({
                'state': 're_opened',
                'reopened_count': rec.reopened_count + 1,
            })
            rec.message_post(body=f'Complaint re-opened. Reason: {reason or "Not stated"}')

    def action_withdraw(self):
        for rec in self:
            rec.with_context(nhs_workflow=True).write({'state': 'withdrawn'})

    def action_escalate_phso(self):
        for rec in self:
            phso = self.env['nhs.complaint.phso'].create({
                'complaint_id': rec.id,
                'referred_at': fields.Date.today(),
            })
            rec.with_context(nhs_workflow=True).write({'state': 'phso', 'phso_id': phso.id})

    def action_escalate_to_complaint(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Escalate to Formal Complaint',
            'res_model': 'nhs.complaint.escalate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_pals_id': self.id},
        }

    def action_create_incident(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Link / Create Incident',
            'res_model': 'nhs.complaint.link.incident.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_complaint_id': self.id},
        }

    def action_view_incidents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Linked Incidents',
            'res_model': 'nhs.incident',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.linked_incident_ids.ids)],
        }

    def action_view_actions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Learning Actions',
            'res_model': 'nhs.action',
            'view_mode': 'list,form',
            'domain': [('complaint_id', '=', self.id)],
            'context': {'default_complaint_id': self.id},
        }

    def action_view_correspondence(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Correspondence',
            'res_model': 'nhs.complaint.correspondence',
            'view_mode': 'list,form',
            'domain': [('complaint_id', '=', self.id)],
            'context': {'default_complaint_id': self.id},
        }

    # ── Cron helpers ──────────────────────────────────────────────────
    @api.model
    def _cron_ack_deadline(self):
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
