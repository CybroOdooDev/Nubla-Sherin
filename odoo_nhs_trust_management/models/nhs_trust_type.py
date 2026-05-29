# -*- coding: utf-8 -*-
from odoo import models, fields, api

class NhsTrustType(models.Model):
    _name = 'nhs.trust.type'
    _description = 'NHS Trust Type'
    _order = 'sequence, name'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, translate=True, index=True)
    code = fields.Char(string='Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    health_system = fields.Selection([
        ('nhs_england', 'NHS England Only'),
        ('nhs_scotland', 'NHS Scotland Only'),
        ('both', 'Both Health Systems'),
    ], string='Health System Applicability', required=True, default='both', index=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The NHS Trust Type code must be unique!'),
    ]
