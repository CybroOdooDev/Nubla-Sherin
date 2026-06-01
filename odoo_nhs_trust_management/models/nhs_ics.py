# -*- coding: utf-8 -*-
from odoo import models, fields, api

class NhsIcs(models.Model):
    _name = 'nhs.ics'
    _description = 'NHS Integrated Care System (ICS)'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(
        string='Name', 
        required=True, 
        index=True,
        help="Full statutory name (e.g. 'Frimley ICS')."
    )
    code = fields.Char(
        string='ODS Code', 
        required=True, 
        index=True,
        help="Unique short code."
    )
    icb_id = fields.Many2one(
        'nhs.icb', 
        string='Integrated Care Board (ICB)', 
        required=True, 
        ondelete='cascade', 
        index=True,
        help="Parent ICB. ondelete='cascade' — if the ICB is deleted, the ICS goes too."
    )
    region_id = fields.Many2one(
        'nhs.region', 
        string='NHS Region', 
        related='icb_id.region_id', 
        store=True, 
        index=True,
        help="Related to icb_id.region_id, stored. Lets users group ICSs by region in list views."
    )
    description = fields.Text(
        string='Description',
        help="Free-text description of the ICS's footprint and member organisations."
    )
    active = fields.Boolean(
        string='Active', 
        default=True,
        help="Archive flag."
    )


    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The ICS ODS code must be unique!'),
    ]
