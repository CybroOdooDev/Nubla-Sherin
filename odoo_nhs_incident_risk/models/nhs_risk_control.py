from odoo import fields, models


class NhsRiskControl(models.Model):
    _name = 'nhs.risk.control'
    _description = 'Risk Control'
    _order = 'risk_id, sequence'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Control Description', required=True)
    control_gap = fields.Boolean(string='Gap in Control')
    owner_id = fields.Many2one('res.users', string='Control Owner')
