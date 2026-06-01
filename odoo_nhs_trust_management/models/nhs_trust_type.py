# -*- coding: utf-8 -*-
from odoo import models, fields, api

class NhsTrustType(models.Model):
    _name = 'nhs.trust.type'
    _description = 'NHS Trust Type'
    _order = 'sequence, name'
    _rec_name = 'name'

    name = fields.Char(
        string='Name', 
        required=True, 
        translate=True, 
        index=True,
        help="Display name (e.g. 'Acute Trust', 'Mental Health Trust'). Translatable so multi-language deployments can localise."
    )
    code = fields.Char(
        string='Code', 
        required=True, 
        index=True,
        help="Unique short code (e.g. 'ACUTE', 'MH', 'SCO-TERR'). Used for CSV imports and Excel exports — keep stable."
    )
    sequence = fields.Integer(
        string='Sequence', 
        default=10,
        help="Display order in the dropdown. Lower numbers appear first. Use multiples of 5 to allow insertions."
    )
    health_system = fields.Selection([
        ('nhs_england', 'NHS England Only'),
        ('nhs_scotland', 'NHS Scotland Only'),
        ('both', 'Both Health Systems'),
    ], 
        string='Health System Applicability', 
        required=True, 
        default='both', 
        index=True,
        help="Filters the dropdown on the Trust form so users only see types applicable to the Trust's health system."
    )
    description = fields.Text(
        string='Description',
        help="Long-form description shown in the type configuration form. Helps administrators choose the right type."
    )
    active = fields.Boolean(
        string='Active', 
        default=True,
        help="Archive flag."
    )


    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The NHS Trust Type code must be unique!'),
    ]
