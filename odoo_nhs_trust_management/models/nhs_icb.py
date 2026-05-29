# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class NhsIcb(models.Model):
    _name = 'nhs.icb'
    _description = 'NHS Integrated Care Board (ICB)'
    _order = 'name'
    _rec_name = 'name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True, index=True, tracking=True)
    code = fields.Char(string='ODS Code', required=True, index=True)
    short_name = fields.Char(string='Short Name')
    region_id = fields.Many2one(
        'nhs.region',
        string='NHS Region',
        required=True,
        domain="[('health_system', '=', 'nhs_england')]",
        index=True
    )
    ics_ids = fields.One2many('nhs.ics', 'icb_id', string='ICS Subdivisions')
    trust_ids = fields.One2many('nhs.trust', 'icb_id', string='Associated Trusts')
    trust_count = fields.Integer(string='Trusts Count', compute='_compute_trust_count')
    population_served = fields.Integer(string='Population Served')
    headquarters_address = fields.Text(string='Headquarters Address')
    website = fields.Char(string='Website')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The ICB ODS code must be unique!'),
    ]

    @api.constrains('region_id')
    def _check_region_system(self):
        for icb in self:
            if icb.region_id and icb.region_id.health_system != 'nhs_england':
                raise ValidationError('An Integrated Care Board (ICB) must belong to an NHS England Region!')

    @api.depends('trust_ids')
    def _compute_trust_count(self):
        for icb in self:
            icb.trust_count = len(icb.trust_ids)
