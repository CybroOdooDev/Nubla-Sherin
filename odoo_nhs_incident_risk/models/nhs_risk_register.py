from odoo import fields, models


class NhsRiskRegister(models.Model):
    _name = 'nhs.risk.register'
    _description = 'Risk Register (tier)'
    _order = 'tier, name'

    name = fields.Char(string='Register Name', required=True)
    tier = fields.Selection([
        ('local', 'Local / Departmental'),
        ('directorate', 'Directorate / Divisional'),
        ('corporate', 'Corporate Risk Register'),
        ('baf', 'Board Assurance Framework (BAF)'),
    ], string='Tier', required=True, default='local')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    owner_group_id = fields.Many2one('res.groups', string='Owner Group')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    risk_count = fields.Integer(compute='_compute_risk_count')

    def _compute_risk_count(self):
        RiskModel = self.env['nhs.risk']
        for reg in self:
            reg.risk_count = RiskModel.search_count([('register_id', '=', reg.id)])
