from odoo import fields, models


class NhsRiskAssurance(models.Model):
    _name = 'nhs.risk.assurance'
    _description = 'Risk Assurance (Three Lines of Defence)'
    _order = 'risk_id, line, sequence'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Assurance Description', required=True)
    line = fields.Selection([
        ('first', '1st Line — Management'),
        ('second', '2nd Line — Oversight / Compliance'),
        ('third', '3rd Line — Internal Audit'),
    ], string='Assurance Line', required=True, default='first')
    assurance_gap = fields.Boolean(string='Gap in Assurance')
    source = fields.Char(string='Source', help='e.g. Audit ref, committee name')
