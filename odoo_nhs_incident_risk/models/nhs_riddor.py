from odoo import api, fields, models
from datetime import timedelta


class NhsRiddor(models.Model):
    _name = 'nhs.riddor'
    _description = 'RIDDOR Determination & HSE Report Log'
    _order = 'id desc'

    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='restrict')
    person_id = fields.Many2one('nhs.incident.person', string='Injured Person')
    reportable = fields.Boolean(string='Reportable to HSE', required=True)
    riddor_category = fields.Selection([
        ('death', 'Death'),
        ('specified_injury', 'Specified Injury'),
        ('over_7_day', 'Over-7-Day Incapacitation'),
        ('occupational_disease', 'Occupational Disease'),
        ('dangerous_occurrence', 'Dangerous Occurrence'),
        ('gas', 'Gas Incident'),
    ], string='RIDDOR Category')
    determination_log = fields.Text(string='Determination Log',
                                    required=True,
                                    help='Full Q&A transcript of the wizard — audit defence.')
    report_deadline = fields.Date(string='HSE Report Deadline',
                                  compute='_compute_deadline', store=True)
    submitted = fields.Boolean(string='Submitted to HSE')
    submitted_at = fields.Datetime(string='Submitted At')
    hse_reference = fields.Char(string='HSE Reference (F2508)')

    @api.depends('riddor_category', 'incident_id.occurred_at')
    def _compute_deadline(self):
        for rec in self:
            if not rec.riddor_category or not rec.incident_id.occurred_at:
                rec.report_deadline = False
                continue
            base = rec.incident_id.occurred_at.date()
            if rec.riddor_category in ('death', 'specified_injury'):
                rec.report_deadline = base + timedelta(days=10)
            elif rec.riddor_category == 'over_7_day':
                rec.report_deadline = base + timedelta(days=15)
            else:
                rec.report_deadline = base + timedelta(days=10)
