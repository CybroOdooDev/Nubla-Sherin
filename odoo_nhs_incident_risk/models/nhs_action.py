from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError


class NhsAction(models.Model):
    _name = 'nhs.action'
    _description = 'Corrective / Preventive Action (CAPA)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, priority desc'

    name = fields.Char(string='Action Title', required=True)
    reference = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    description = fields.Text(string='Description / Acceptance Criteria')
    action_type = fields.Selection([
        ('corrective', 'Corrective'),
        ('preventive', 'Preventive'),
        ('improvement', 'Improvement'),
    ], string='Type', required=True, default='corrective')
    incident_id = fields.Many2one('nhs.incident', string='Incident', ondelete='restrict')
    investigation_id = fields.Many2one('nhs.investigation', string='Investigation',
                                       ondelete='restrict')
    risk_id = fields.Many2one('nhs.risk', string='Risk', ondelete='restrict')
    owner_id = fields.Many2one('res.users', string='Owner', required=True,
                               default=lambda self: self.env.user, tracking=True)
    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority', default='medium')
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('evidence_review', 'Evidence Review'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='open', required=True, tracking=True)
    cancellation_reason = fields.Text(string='Cancellation Reason')
    completion_evidence = fields.Text(string='Completion Evidence',
                                      help='Required before moving to Evidence Review.')
    verified_by_id = fields.Many2one('res.users', string='Verified By')
    verified_at = fields.Datetime(string='Verified At')
    effectiveness_check = fields.Boolean(string='Schedule Effectiveness Check')
    effectiveness_days = fields.Integer(string='Effectiveness Check Days', default=90)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = seq.next_by_code('nhs.action') or 'New'
        records = super().create(vals_list)
        for rec in records:
            rec.activity_schedule('mail.mail_activity_data_todo',
                                  user_id=rec.owner_id.id,
                                  note=f'Action assigned: {rec.name}')
        return records

    @api.constrains('incident_id', 'investigation_id', 'risk_id')
    def _check_single_parent(self):
        for rec in self:
            parents = bool(rec.incident_id) + bool(rec.investigation_id) + bool(rec.risk_id)
            if parents > 1:
                raise ValidationError('An action can only be linked to one parent record.')

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_submit_evidence(self):
        for rec in self:
            if not rec.completion_evidence:
                raise UserError('Please enter completion evidence before submitting for review.')
            rec.write({'state': 'evidence_review'})

    def action_verify(self):
        self.write({
            'state': 'done',
            'verified_by_id': self.env.user.id,
            'verified_at': fields.Datetime.now(),
        })
        for rec in self.filtered('effectiveness_check'):
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fields.Date.today() + \
                    timedelta(days=rec.effectiveness_days),
                user_id=rec.owner_id.id,
                note=f'Effectiveness check: {rec.name}',
            )

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def write(self, vals):
        if 'state' in vals:
            for rec in self:
                new_state = vals['state']
                if new_state == 'evidence_review' and not (
                        vals.get('completion_evidence') or rec.completion_evidence):
                    raise UserError('Completion evidence is required before evidence review.')
        return super().write(vals)

    @api.model
    def _cron_action_escalation(self):
        today = fields.Date.today()
        warn_date = today + timedelta(days=3)
        actions = self.search([
            ('state', 'not in', ['done', 'cancelled']),
            ('due_date', '<=', warn_date),
        ])
        for action in actions:
            if not action.due_date:
                continue
            days_over = (today - action.due_date).days
            if days_over > 0:
                action.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=action.owner_id.id,
                    note=f'Action OVERDUE by {days_over} days: {action.name}')
