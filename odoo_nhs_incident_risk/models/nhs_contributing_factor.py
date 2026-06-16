from odoo import fields, models


class NhsContributingFactor(models.Model):
    _name = 'nhs.contributing.factor'
    _description = 'Contributing Factor (Yorkshire Contributory Factors Framework)'
    _order = 'group_name, name'

    group_name = fields.Selection([
        ('patient', 'Patient Factors'),
        ('task', 'Task & Technology'),
        ('individual', 'Individual Staff'),
        ('team', 'Team Factors'),
        ('environment', 'Work Environment'),
        ('organisational', 'Organisational & Management'),
        ('external', 'External Factors'),
    ], string='Group', required=True)
    name = fields.Char(string='Factor', required=True)
    active = fields.Boolean(default=True)
