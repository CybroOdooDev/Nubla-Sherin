from odoo import fields, models


class NhsRiskReview(models.Model):
    _name = 'nhs.risk.review'
    _description = 'Risk Review Log Entry'
    _order = 'reviewed_at desc'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True, ondelete='cascade')
    reviewed_at = fields.Datetime(string='Reviewed At', required=True,
                                  default=fields.Datetime.now)
    reviewer_id = fields.Many2one('res.users', string='Reviewer', required=True,
                                  default=lambda self: self.env.user)
    prev_current_consequence = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)], string='Previous Consequence')
    prev_current_likelihood = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)], string='Previous Likelihood')
    new_current_consequence = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)], string='New Consequence')
    new_current_likelihood = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)], string='New Likelihood')
    commentary = fields.Text(string='Commentary')
    decision = fields.Selection([
        ('no_change', 'No Change'),
        ('rescore', 'Re-scored'),
        ('escalate', 'Escalated'),
        ('deescalate', 'De-escalated'),
        ('close', 'Risk Closed'),
    ], string='Decision', required=True, default='no_change')
