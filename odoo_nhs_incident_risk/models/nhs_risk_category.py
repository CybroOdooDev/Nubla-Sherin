from odoo import fields, models


class NhsRiskCategory(models.Model):
    _name = 'nhs.risk.category'
    _description = 'Risk Category'
    _order = 'name'

    name = fields.Char(string='Category', required=True)
    description = fields.Text(string='Description')
    appetite_threshold = fields.Integer(
        string='Appetite Threshold (1–25)', default=6,
        help='Risks with current_rating above this threshold are flagged outside appetite.')
    active = fields.Boolean(default=True)
