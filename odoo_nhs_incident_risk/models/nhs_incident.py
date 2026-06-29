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


HARM_ORDER = ['no_harm', 'low', 'moderate', 'severe', 'death']
DOC_TRIGGER_GRADES = {'moderate', 'severe', 'death'}


class NhsIncident(models.Model):
    _name = 'nhs.incident'
    _description = 'NHS Incident / Patient Safety Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'name'

    # ── Identification ───────────────────────────────────────────────
    name = fields.Char(string='Reference', required=True, readonly=True,
                       copy=False, default='New', tracking=True,
                       help='Auto-generated unique reference number for this incident (e.g. INC/2026/00001).')
    company_id = fields.Many2one('res.company', string='Organisation',
                                 required=True, default=lambda self: self.env.company,
                                 help='The NHS organisation or CQC provider this incident belongs to.')
    incident_kind = fields.Selection([
        ('incident', 'Patient Safety Incident'),
        ('risk_event', 'Near Miss / Hazard'),
        ('outcome', 'Outcome (harm without known incident)'),
        ('good_care', 'Good Care / Excellence'),
    ], string='Event Type', required=True, default='incident', tracking=True,
       help='Classify the nature of the event: a patient safety incident, a near miss/hazard, '
            'an adverse outcome without a known cause, or a good care example to share.')

    # ── When / Where ─────────────────────────────────────────────────
    occurred_at = fields.Datetime(string='Date/Time of Incident', required=True, tracking=True,
                                  help='The date and time the event actually occurred. Cannot be set in the future.')
    reported_at = fields.Datetime(string='Date/Time Reported', required=True,
                                  default=fields.Datetime.now,
                                  help='The date and time this incident was first reported to the system.')
    location_id = fields.Many2one('nhs.location', string='Location', required=True,
                                  help='The ward, department, or site where the incident occurred.')
    location_detail = fields.Char(string='Location Detail',
                                  help='e.g. Bathroom of room 12')
    category_id = fields.Many2one('nhs.incident.category', string='Category',
                                  required=True,
                                  help='The incident category used for reporting and trend analysis. '
                                       'Selecting a category may auto-set the response level and harm floor.')

    # ── Description ──────────────────────────────────────────────────
    description = fields.Text(
        string='What Happened',
        required=True,
        help='Describe what happened. Do NOT include full names of patients — use initials.')
    immediate_action = fields.Text(string='Immediate Action Taken',
                                   help='Record any immediate steps taken at the time of the incident '
                                        'to ensure patient/staff safety.')

    # ── Reporter ─────────────────────────────────────────────────────
    is_anonymous = fields.Boolean(string='Anonymous Report',
                                  help='Tick if the reporter wishes to remain anonymous. '
                                       'Reporter name and contact fields will be hidden.')
    reporter_name = fields.Char(string='Reporter Name',
                                help='Full name of the person who reported the incident.')
    reporter_email = fields.Char(string='Reporter Email',
                                 help='Email address used to send acknowledgement and feedback to the reporter.')
    reporter_role = fields.Char(string='Reporter Job Role',
                                help='Job title or role of the reporter (e.g. Staff Nurse, Paramedic).')
    reported_via = fields.Selection([
        ('public_form', 'Public Web Form'),
        ('backend', 'Backend (direct)'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('import', 'Import'),
    ], string='Reported Via', required=True, default='backend',
       help='The channel through which this incident was reported.')

    # ── Grading ──────────────────────────────────────────────────────
    harm_grade = fields.Selection([
        ('no_harm', 'No Harm'),
        ('low', 'Low Harm'),
        ('moderate', 'Moderate Harm'),
        ('severe', 'Severe Harm'),
        ('death', 'Death'),
    ], string='NPSA Harm Grade', tracking=True,
       help='The NPSA harm grading scale. Moderate harm or above triggers a Duty of Candour obligation '
            'and may require LFPSE submission.')
    physical_harm = fields.Selection([
        ('none', 'None'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('fatal', 'Fatal'),
    ], string='Physical Harm (LFPSE)',
       help='The degree of physical harm experienced by the patient, as required for LFPSE reporting.')
    psychological_harm = fields.Selection([
        ('none', 'None'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], string='Psychological Harm (LFPSE)',
       help='The degree of psychological harm experienced, as required for LFPSE reporting.')
    response_level = fields.Selection([
        ('none', 'No Separate Response'),
        ('swarm', 'SWARM Huddle'),
        ('aar', 'After Action Review'),
        ('mdt_review', 'MDT Review'),
        ('psii', 'PSII'),
    ], string='PSIRF Response Level', tracking=True,
       help='The PSIRF-defined learning response: SWARM for immediate debrief, AAR for structured review, '
            'MDT Review for multidisciplinary input, PSII for serious incidents requiring formal investigation.')
    is_never_event = fields.Boolean(string='Never Event', tracking=True,
                                    help='Tick if this is a Never Event — a serious, largely preventable patient safety incident. '
                                         'Automatically sets response level to PSII.')

    # ── Safeguarding ─────────────────────────────────────────────────
    safeguarding_flag = fields.Boolean(string='Safeguarding Concern', tracking=True,
                                       help='Tick if this incident involves a safeguarding concern for a vulnerable adult or child. '
                                            'Access is restricted to Safeguarding Officers.')
    safeguarding_referral_made = fields.Boolean(string='LA Referral Made',
                                                help='Tick if a referral has been made to the Local Authority safeguarding team.')
    safeguarding_reference = fields.Char(string='LA Reference',
                                         help='The reference number provided by the Local Authority for this safeguarding referral.')

    # ── Workflow ─────────────────────────────────────────────────────
    state = fields.Selection([
        ('new', 'New'),
        ('triage', 'Triage'),
        ('investigation', 'Investigation'),
        ('actions', 'Actions'),
        ('pending_closure', 'Pending Closure'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
        ('duplicate', 'Duplicate'),
    ], string='Status', default='new', required=True, tracking=True,
       group_expand='_read_group_state',
       help='The current workflow stage of this incident.')
    handler_id = fields.Many2one('res.users', string='Handler', tracking=True,
                                 help='The member of staff responsible for managing this incident through to closure.')
    rejection_reason = fields.Text(string='Rejection Reason',
                                   help='Explanation of why this incident report was rejected (e.g. duplicate, out of scope).')
    duplicate_of_id = fields.Many2one('nhs.incident', string='Duplicate Of',
                                      help='The master incident record of which this report is a duplicate.')
    related_incident_ids = fields.Many2many(
        'nhs.incident', 'nhs_incident_related_rel',
        'incident_id', 'related_id', string='Related Incidents',
        help='Other incidents that are related to or contextually linked with this one.')

    # ── Relations ────────────────────────────────────────────────────
    risk_ids = fields.Many2many('nhs.risk', string='Related Risks',
                                help='Risks on the risk register that are associated with this incident.')
    person_ids = fields.One2many('nhs.incident.person', 'incident_id',
                                 string='Persons Affected',
                                 help='Patients, staff, or visitors affected by this incident.')
    investigation_id = fields.Many2one('nhs.investigation', string='Investigation',
                                       copy=False,
                                       help='The formal investigation record linked to this incident.')
    action_ids = fields.One2many('nhs.action', 'incident_id', string='Actions',
                                 help='Improvement actions arising from this incident.')
    doc_id = fields.Many2one('nhs.duty.of.candour', string='Duty of Candour',
                             copy=False,
                             help='The Duty of Candour record auto-created when harm grade reaches the configured threshold.')
    doc_state = fields.Selection(related='doc_id.state', string='DoC Status', readonly=True)
    riddor_id = fields.Many2one('nhs.riddor', string='RIDDOR', copy=False,
                                help='The RIDDOR determination record for this incident, if applicable.')
    cqc_notification_ids = fields.One2many('nhs.cqc.notification', 'incident_id',
                                           string='CQC Notifications',
                                           help='CQC statutory notifications that must be submitted for this incident.')
    lfpse_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('exported', 'Exported'),
        ('submitted', 'Submitted'),
    ], string='LFPSE Status', default='not_required', tracking=True,
       help='The Learn from Patient Safety Events (LFPSE) submission status for this incident.')
    riddor_hint = fields.Boolean(string='RIDDOR Check Suggested', default=False,
                                 help='Set automatically when incident characteristics suggest RIDDOR reporting may be required. '
                                      'Use the RIDDOR Check button to run the determination wizard.')

    # ── Closure ──────────────────────────────────────────────────────
    closed_at = fields.Datetime(string='Closed At', readonly=True,
                                help='The date and time this incident was formally closed.')
    days_to_close = fields.Integer(string='Days to Close (working)',
                                   compute='_compute_days_to_close', store=True,
                                   help='Number of working days (excluding weekends and bank holidays) from reporting to closure.')
    feedback_sent = fields.Boolean(string='Feedback Sent to Reporter',
                                   help='Tick once feedback or an outcome summary has been sent to the original reporter.')

    # ── Smart button counts ───────────────────────────────────────────
    person_count = fields.Integer(compute='_compute_counts',
                                  help='Number of persons affected by or involved in this incident.')
    action_count = fields.Integer(compute='_compute_counts',
                                  help='Number of corrective/preventive actions raised against this incident.')
    cqc_count = fields.Integer(compute='_compute_counts',
                               help='Number of CQC statutory notifications linked to this incident.')
    risk_count = fields.Integer(compute='_compute_counts',
                                help='Number of risk register entries associated with this incident.')
    investigation_count = fields.Integer(compute='_compute_counts',
                                         help='1 if a linked investigation exists, 0 otherwise.')

    @api.depends('person_ids', 'action_ids', 'cqc_notification_ids', 'risk_ids', 'investigation_id')
    def _compute_counts(self):
        for rec in self:
            rec.person_count = len(rec.person_ids)
            rec.action_count = len(rec.action_ids)
            rec.cqc_count = len(rec.cqc_notification_ids)
            rec.risk_count = len(rec.risk_ids)
            rec.investigation_count = 1 if rec.investigation_id else 0

    @api.model
    def _read_group_state(self, stages, domain, order=None, **kwargs):
        if domain:
            try:
                if not isinstance(domain, (list, tuple)) and hasattr(domain, '__iter__'):
                    domain = list(domain)
            except Exception:
                pass
        state_list = ['new', 'triage', 'investigation', 'actions', 'pending_closure', 'closed', 'rejected', 'duplicate']
        allowed_states = set()
        has_state_filter = False

        def parse_domain(dom):
            nonlocal has_state_filter
            if not isinstance(dom, (list, tuple)):
                return
            if len(dom) == 3 and dom[0] == 'state':
                has_state_filter = True
                op, val = dom[1], dom[2]
                if op == '=':
                    allowed_states.add(val)
                elif op == 'in' and isinstance(val, (list, tuple)):
                    allowed_states.update(val)
                elif op == 'not in' and isinstance(val, (list, tuple)):
                    if not allowed_states:
                        allowed_states.update(state_list)
                    allowed_states.difference_update(val)
                elif op == '!=':
                    if not allowed_states:
                        allowed_states.update(state_list)
                    allowed_states.discard(val)
            else:
                for item in dom:
                    parse_domain(item)

        parse_domain(domain)
        if has_state_filter:
            return [s for s in state_list if s in allowed_states]
        return state_list

    @api.depends('reported_at', 'closed_at')
    def _compute_days_to_close(self):
        Holiday = self.env['nhs.holiday']
        for rec in self:
            if rec.reported_at and rec.closed_at:
                start = rec.reported_at.date()
                end = rec.closed_at.date()
                holidays = set(Holiday.search([]).mapped('date'))
                days = 0
                current = start
                from datetime import timedelta
                while current < end:
                    current += timedelta(days=1)
                    if current.weekday() < 5 and current not in holidays:
                        days += 1
                rec.days_to_close = days
            else:
                rec.days_to_close = 0

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('nhs.incident') or 'New'
        records = super().create(vals_list)
        for rec in records:
            rec._apply_harm_rules()
            self.env['nhs.notification.rule'].evaluate(rec)
            if not rec.handler_id and rec.location_id.default_handler_id:
                rec.with_context(nhs_workflow=True).write(
                    {'handler_id': rec.location_id.default_handler_id.id})
        return records

    def write(self, vals):
        if 'state' in vals and not self.env.context.get('nhs_workflow'):
            raise UserError(
                'Incident state must be changed through workflow action buttons, not direct write.')
        result = super().write(vals)
        if 'harm_grade' in vals or 'category_id' in vals:
            for rec in self:
                rec._apply_harm_rules()
                self.env['nhs.notification.rule'].evaluate(rec)
        return result

    def _apply_harm_rules(self):
        for rec in self:
            if rec.is_never_event:
                rec.with_context(nhs_workflow=True).write({'response_level': 'psii'})
            trigger = rec.company_id.doc_trigger_grade or 'moderate'
            if rec.harm_grade and rec.harm_grade in DOC_TRIGGER_GRADES:
                grade_idx = HARM_ORDER.index(rec.harm_grade)
                trigger_idx = HARM_ORDER.index(trigger)
                if grade_idx >= trigger_idx and not rec.doc_id:
                    doc = self.env['nhs.duty.of.candour'].create({
                        'incident_id': rec.id,
                        'triggered_at': fields.Datetime.now(),
                    })
                    rec.with_context(nhs_workflow=True).write({'doc_id': doc.id})

    @api.constrains('occurred_at')
    def _check_occurred_at(self):
        for rec in self:
            if rec.occurred_at and rec.occurred_at > fields.Datetime.now():
                raise ValidationError('Incident date/time cannot be in the future.')

    @api.constrains('state', 'rejection_reason')
    def _check_rejection_reason(self):
        for rec in self:
            if rec.state == 'rejected' and not rec.rejection_reason:
                raise ValidationError('A rejection reason is required.')

    @api.constrains('state', 'duplicate_of_id')
    def _check_duplicate_of(self):
        for rec in self:
            if rec.state == 'duplicate':
                if not rec.duplicate_of_id:
                    raise ValidationError('Please specify the master incident for a duplicate.')
                if rec.duplicate_of_id.state == 'duplicate':
                    raise ValidationError('The master incident cannot itself be a duplicate.')

    @api.onchange('is_never_event')
    def _onchange_never_event(self):
        if self.is_never_event:
            self.response_level = 'psii'

    @api.onchange('category_id')
    def _onchange_category(self):
        if self.category_id:
            if self.category_id.default_response_level:
                self.response_level = self.category_id.default_response_level
            if self.category_id.default_harm_floor:
                self.harm_grade = self.category_id.default_harm_floor

    # ── Workflow actions ─────────────────────────────────────────────
    def action_accept(self):
        for rec in self:
            rec.with_context(nhs_workflow=True).write({'state': 'triage'})

    def action_reject(self, reason):
        for rec in self:
            rec.with_context(nhs_workflow=True).write({
                'state': 'rejected',
                'rejection_reason': reason,
            })
            if rec.reporter_email and not rec.is_anonymous:
                template = self.env.ref(
                    'odoo_nhs_incident_risk.mail_template_rejection_feedback',
                    raise_if_not_found=False)
                if template:
                    template.send_mail(rec.id, force_send=True)

    def action_mark_duplicate(self, master_id):
        for rec in self:
            rec.with_context(nhs_workflow=True).write({
                'state': 'duplicate',
                'duplicate_of_id': master_id,
            })

    def action_start_investigation(self):
        for rec in self:
            if rec.state != 'triage':
                raise UserError('Incident must be in Triage state to start an investigation.')
            if not rec.harm_grade:
                raise UserError('Harm grade must be set before starting an investigation.')
            if not rec.response_level:
                raise UserError('Response level must be set before starting an investigation.')
            if rec.response_level == 'none':
                rec.with_context(nhs_workflow=True).write({'state': 'actions'})
            else:
                inv = self.env['nhs.investigation'].create({
                    'incident_id': rec.id,
                    'response_level': rec.response_level,
                    'lead_investigator_id': rec.handler_id.id or self.env.user.id,
                })
                rec.with_context(nhs_workflow=True).write({
                    'state': 'investigation',
                    'investigation_id': inv.id,
                })

    def action_advance_to_actions(self):
        for rec in self:
            if rec.investigation_id and rec.investigation_id.state != 'approved':
                raise UserError('Investigation must be approved before advancing to Actions.')
            rec.with_context(nhs_workflow=True).write({'state': 'actions'})

    def action_request_closure(self):
        for rec in self:
            open_actions = rec.action_ids.filtered(
                lambda a: a.state not in ('done', 'cancelled'))
            if open_actions:
                raise UserError(
                    f'{len(open_actions)} action(s) must be completed or cancelled before closure.')
            if rec.doc_id and rec.doc_id.state != 'complete':
                raise UserError('Duty of Candour record must be complete before closure.')
            open_cqc = rec.cqc_notification_ids.filtered(lambda n: n.state == 'required')
            if open_cqc:
                raise UserError(
                    f'{len(open_cqc)} CQC notification(s) must be resolved before closure.')
            rec.with_context(nhs_workflow=True).write({'state': 'pending_closure'})

    def action_close(self):
        if not self.env.user.has_group(
                'odoo_nhs_incident_risk.group_hc_quality_lead'):
            raise UserError('Only Quality Lead users can close incidents.')
        for rec in self:
            rec.with_context(nhs_workflow=True).write({
                'state': 'closed',
                'closed_at': fields.Datetime.now(),
            })
            if rec.reporter_email and not rec.is_anonymous:
                template = self.env.ref(
                    'odoo_nhs_incident_risk.mail_template_closure_feedback',
                    raise_if_not_found=False)
                if template:
                    template.send_mail(rec.id, force_send=True)
                rec.with_context(nhs_workflow=True).write({'feedback_sent': True})

    def action_create_risk(self):
        self.ensure_one()
        return self.env['nhs.risk'].create_from_incident(self)

    def action_open_triage_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Triage Incident',
            'res_model': 'nhs.triage.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_incident_id': self.id},
        }

    def action_open_riddor_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'RIDDOR Determination',
            'res_model': 'nhs.riddor.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_incident_id': self.id},
        }

    def action_open_persons(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Persons Affected',
            'res_model': 'nhs.incident.person',
            'view_mode': 'list,form',
            'domain': [('incident_id', '=', self.id)],
            'context': {'default_incident_id': self.id},
        }

    def action_open_actions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Actions',
            'res_model': 'nhs.action',
            'view_mode': 'list,form',
            'domain': [('incident_id', '=', self.id)],
            'context': {'default_incident_id': self.id},
        }

    def action_open_cqc_notifications(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'CQC Notifications',
            'res_model': 'nhs.cqc.notification',
            'view_mode': 'list,form',
            'domain': [('incident_id', '=', self.id)],
            'context': {'default_incident_id': self.id},
        }

    def action_open_risks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related Risks',
            'res_model': 'nhs.risk',
            'view_mode': 'list,form',
            'domain': [('incident_ids', 'in', [self.id])],
        }

    def action_open_investigation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Investigation',
            'res_model': 'nhs.investigation',
            'view_mode': 'form',
            'res_id': self.investigation_id.id,
        }

    def action_open_doc(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Duty of Candour',
            'res_model': 'nhs.duty.of.candour',
            'view_mode': 'form',
            'res_id': self.doc_id.id,
        }

    @api.model
    def _cron_sla_triage(self):
        threshold = fields.Datetime.now() - timedelta(days=3)
        incidents = self.search([
            ('state', 'in', ['new', 'triage']),
            ('reported_at', '<', threshold),
        ])
        for inc in incidents:
            if inc.handler_id and not inc.activity_ids.filtered(
                    lambda a: a.activity_type_id.name == 'To-Do'):
                inc.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=inc.handler_id.id,
                    note=f'Triage SLA breached: {inc.name}')

    @api.model
    def _cron_anonymise(self):
        pass
