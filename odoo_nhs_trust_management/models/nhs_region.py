# -*- coding: utf-8 -*-
from odoo import models, fields, api

class NhsRegion(models.Model):
    _name = 'nhs.region'
    _description = 'NHS Region'
    _order = 'health_system, name'
    _rec_name = 'name'

    name = fields.Char(
        string='Name', 
        required=True, 
        translate=True, 
        index=True,
        help="Full region name (e.g. 'North East and Yorkshire'). Used in the breadcrumb on Trust forms."
    )
    code = fields.Char(
        string='Code', 
        required=True, 
        index=True,
        help="Short region code (e.g. 'NEY' for England, 'SCO-N' for Scotland). Must be unique. Used in Excel exports and the PDF profile header."
    )
    health_system = fields.Selection([
        ('nhs_england', 'NHS England'),
        ('nhs_scotland', 'NHS Scotland'),
    ], 
        string='Health System', 
        required=True, 
        default='nhs_england', 
        index=True,
        help="Selection: 'nhs_england' or 'nhs_scotland'. Default: 'nhs_england'. Drives downstream filtering — a region only appears in the dropdown when the Trust's health_system matches."
    )
    trust_count = fields.Integer(
        string='Trusts Count', 
        compute='_compute_trust_count',
        help="Live count of Trusts attached to this region. Displayed on the stat button in the region form."
    )
    active = fields.Boolean(
        string='Active', 
        default=True,
        help="Standard Odoo archive flag. Archived regions remain on existing records but disappear from new dropdowns."
    )


    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The NHS Region code must be unique!'),
    ]

    @api.depends('health_system')
    def _compute_trust_count(self):
        # Efficiently compute count of trusts per region using read_group
        trust_data = self.env['nhs.trust'].read_group(
            [('region_id', 'in', self.ids)],
            ['region_id'],
            ['region_id']
        )
        mapped_data = {data['region_id'][0]: data['region_id_count'] for data in trust_data if data['region_id']}
        for region in self:
            region.trust_count = mapped_data.get(region.id, 0)
