from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


HARM_ORDER = ['no_harm', 'low', 'moderate', 'severe', 'death']
DOC_TRIGGER_GRADES = {'moderate', 'severe', 'death'}


class NhsIncident(models.Model):
    _name = 'nhs.incident'
    _description = 'NHS Incident / Patient Safety Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'occurred_at desc, id desc'
    _rec_name = 'name'

    # ── Identification ───────────────────────────────────────────────
    name = fields.Char(string='Reference', required=True, readonly=True,
                       copy=False, default='New', tracking=True)
    company_id = fields.Many2one('res.company', string='Organisation',
                                 required=True, default=lambda self: self.env.company)
    incident_kind = fields.Selection([
        ('incident', 'Patient Safety Incident'),
        ('risk_event', 'Near Miss / Hazard'),
        ('outcome', 'Outcome (harm without known incident)'),
        ('good_care', 'Good Care / Excellence'),
    ], string='Event Type', required=True, default='incident', tracking=True)

    # ── When / Where ─────────────────────────────────────────────────
    occurred_at = fields.Datetime(string='Date/Time of Incident', required=True, tracking=True)
    reported_at = fields.Datetime(string='Date/Time Reported', required=True,
                                  default=fields.Datetime.now)
    location_id = fields.Many2one('nhs.location', string='Location', required=True)
    location_detail = fields.Char(string='Location Detail',
                                  help='e.g. Bathroom of room 12')
    category_id = fields.Many2one('nhs.incident.category', string='Category',
                                  required=True)

    # ── Description ──────────────────────────────────────────────────
    description = fields.Text(
        string='What Happened',
        required=True,
        help='Describe what happened. Do NOT include full names of patients — use initials.')
    immediate_action = fields.Text(string='Immediate Action Taken')

    # ── Reporter ─────────────────────────────────────────────────────
    is_anonymous = fields.Boolean(string='Anonymous Report')
    reporter_name = fields.Char(string='Reporter Name')
    reporter_email = fields.Char(string='Reporter Email')
    reporter_role = fields.Char(string='Reporter Job Role')
    reported_via = fields.Selection([
        ('public_form', 'Public Web Form'),
        ('backend', 'Backend (direct)'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('import', 'Import'),
    ], string='Reported Via', required=True, default='backend')

    # ── Grading ──────────────────────────────────────────────────────
    harm_grade = fields.Selection([
        ('no_harm', 'No Harm'),
        ('low', 'Low Harm'),
        ('moderate', 'Moderate Harm'),
        ('severe', 'Severe Harm'),
        ('death', 'Death'),
    ], string='NPSA Harm Grade', tracking=True)
    physical_harm = fields.Selection([
        ('none', 'None'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('fatal', 'Fatal'),
    ], string='Physical Harm (LFPSE)')
    psychological_harm = fields.Selection([
        ('none', 'None'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], string='Psychological Harm (LFPSE)')
    response_level = fields.Selection([
        ('none', 'No Separate Response'),
        ('swarm', 'SWARM Huddle'),
        ('aar', 'After Action Review'),
        ('mdt_review', 'MDT Review'),
        ('psii', 'PSII'),
    ], string='PSIRF Response Level', tracking=True)
    is_never_event = fields.Boolean(string='Never Event', tracking=True)

    # ── Safeguarding ─────────────────────────────────────────────────
    safeguarding_flag = fields.Boolean(string='Safeguarding Concern', tracking=True)
    safeguarding_referral_made = fields.Boolean(string='LA Referral Made')
    safeguarding_reference = fields.Char(string='LA Reference')

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
    ], string='Status', default='new', required=True, tracking=True)
    handler_id = fields.Many2one('res.users', string='Handler', tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason')
    duplicate_of_id = fields.Many2one('nhs.incident', string='Duplicate Of')
    related_incident_ids = fields.Many2many(
        'nhs.incident', 'nhs_incident_related_rel',
        'incident_id', 'related_id', string='Related Incidents')

    # ── Relations ────────────────────────────────────────────────────
    risk_ids = fields.Many2many('nhs.risk', string='Related Risks')
    person_ids = fields.One2many('nhs.incident.person', 'incident_id',
                                 string='Persons Affected')
    investigation_id = fields.Many2one('nhs.investigation', string='Investigation',
                                       copy=False)
    action_ids = fields.One2many('nhs.action', 'incident_id', string='Actions')
    doc_id = fields.Many2one('nhs.duty.of.candour', string='Duty of Candour',
                             copy=False)
    riddor_id = fields.Many2one('nhs.riddor', string='RIDDOR', copy=False)
    cqc_notification_ids = fields.One2many('nhs.cqc.notification', 'incident_id',
                                           string='CQC Notifications')
    lfpse_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('exported', 'Exported'),
        ('submitted', 'Submitted'),
    ], string='LFPSE Status', default='not_required', tracking=True)
    riddor_hint = fields.Boolean(string='RIDDOR Check Suggested', default=False)

    # ── Closure ──────────────────────────────────────────────────────
    closed_at = fields.Datetime(string='Closed At', readonly=True)
    days_to_close = fields.Integer(string='Days to Close (working)',
                                   compute='_compute_days_to_close', store=True)
    feedback_sent = fields.Boolean(string='Feedback Sent to Reporter')

    # ── Smart button counts ───────────────────────────────────────────
    person_count = fields.Integer(compute='_compute_counts')
    action_count = fields.Integer(compute='_compute_counts')
    cqc_count = fields.Integer(compute='_compute_counts')
    risk_count = fields.Integer(compute='_compute_counts')

    @api.depends('person_ids', 'action_ids', 'cqc_notification_ids', 'risk_ids')
    def _compute_counts(self):
        for rec in self:
            rec.person_count = len(rec.person_ids)
            rec.action_count = len(rec.action_ids)
            rec.cqc_count = len(rec.cqc_notification_ids)
            rec.risk_count = len(rec.risk_ids)

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
