from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class NhsDutyOfCandour(models.Model):
    _name = 'nhs.duty.of.candour'
    _description = 'Duty of Candour Compliance Record (CQC Reg 20)'
    _inherit = ['mail.thread']
    _order = 'written_deadline'

    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='restrict')
    triggered_at = fields.Datetime(string='Triggered At', required=True,
                                   default=fields.Datetime.now, tracking=True)
    written_deadline = fields.Date(string='Written Notification Deadline',
                                   compute='_compute_written_deadline', store=True,
                                   help='+10 working days from trigger.')
    # Stage 1 — verbal
    verbal_done = fields.Boolean(string='Verbal Notification Done', tracking=True)
    verbal_at = fields.Datetime(string='Verbal Date/Time')
    verbal_by_id = fields.Many2one('res.users', string='Verbal Notified By')
    verbal_notes = fields.Text(string='Verbal Notes')
    # Stage 2 — written
    written_done = fields.Boolean(string='Written Notification Done', tracking=True)
    written_at = fields.Datetime(string='Written Date/Time')
    written_letter_attachment_id = fields.Many2one('ir.attachment', string='Signed Letter')
    # Stage 3 — findings shared
    findings_shared_done = fields.Boolean(string='Findings Shared', tracking=True)
    findings_shared_at = fields.Datetime(string='Findings Shared Date')
    # State
    state = fields.Selection([
        ('open', 'Open'),
        ('overdue', 'Overdue'),
        ('complete', 'Complete'),
    ], string='Status', compute='_compute_state', store=True, tracking=True)
    exemption_reason = fields.Text(string='Exemption / Justification',
                                   help='Document lawful reason if contact cannot be made.')

    @api.depends('triggered_at')
    def _compute_written_deadline(self):
        Holiday = self.env['nhs.holiday']
        for rec in self:
            if rec.triggered_at:
                start = rec.triggered_at.date()
                rec.written_deadline = Holiday.add_working_days(start, 10)
            else:
                rec.written_deadline = False

    @api.depends('verbal_done', 'written_done', 'findings_shared_done',
                 'written_deadline', 'exemption_reason')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if rec.exemption_reason or \
               (rec.verbal_done and rec.written_done and rec.findings_shared_done):
                rec.state = 'complete'
            elif rec.written_deadline and today > rec.written_deadline and not rec.written_done:
                rec.state = 'overdue'
            else:
                rec.state = 'open'

    def action_generate_letter(self):
        self.ensure_one()
        return self.env.ref(
            'odoo_nhs_incident_risk.action_report_doc_letter'
        ).report_action(self)

    @api.model
    def _cron_doc_deadlines(self):
        today = fields.Date.today()
        docs = self.search([('state', 'in', ['open', 'overdue'])])
        quality_group = self.env.ref(
            'odoo_nhs_incident_risk.group_hc_quality_lead', raise_if_not_found=False)
        quality_users = quality_group.users if quality_group else self.env['res.users']
        for doc in docs:
            if not doc.written_deadline or doc.written_done:
                continue
            days_left = (doc.written_deadline - today).days
            if days_left in (2, 5):
                for user in quality_users:
                    doc.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        note=f'DoC deadline in {days_left} days — {doc.incident_id.name}')
