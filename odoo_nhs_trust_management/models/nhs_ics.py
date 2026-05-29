# -*- coding: utf-8 -*-
from odoo import models, fields, api

class NhsIcs(models.Model):
    _name = 'nhs.ics'
    _description = 'NHS Integrated Care System (ICS)'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, index=True)
    code = fields.Char(string='ODS Code', required=True, index=True)
    icb_id = fields.Many2one('nhs.icb', string='Integrated Care Board (ICB)', required=True, ondelete='cascade', index=True)
    region_id = fields.Many2one('nhs.region', string='NHS Region', related='icb_id.region_id', store=True, index=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The ICS ODS code must be unique!'),
    ]
