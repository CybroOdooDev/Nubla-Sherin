# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class NhsHealthBoard(models.Model):
    _name = 'nhs.health.board'
    _description = 'NHS Scotland Health Board'
    _order = 'name'
    _rec_name = 'name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True, index=True, tracking=True)
    code = fields.Char(string='ODS Code', required=True, index=True)
    short_name = fields.Char(string='Short Name')
    region_id = fields.Many2one(
        'nhs.region',
        string='NHS Region',
        domain="[('health_system', '=', 'nhs_scotland')]",
        index=True
    )
    board_type = fields.Selection([
        ('territorial', 'Territorial Health Board'),
        ('national', 'National Health Board'),
    ], string='Board Type', required=True, default='territorial', index=True)
    population_served = fields.Integer(string='Population Served')
    headquarters_address = fields.Text(string='Headquarters Address')
    website = fields.Char(string='Website')
    trust_ids = fields.One2many('nhs.trust', 'health_board_id', string='Associated Trusts')
    trust_count = fields.Integer(string='Trusts Count', compute='_compute_trust_count')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The Health Board ODS code must be unique!'),
    ]

    @api.constrains('region_id')
    def _check_region_system(self):
        for board in self:
            if board.region_id and board.region_id.health_system != 'nhs_scotland':
                raise ValidationError('An NHS Scotland Health Board must belong to an NHS Scotland Region!')

    @api.depends('trust_ids')
    def _compute_trust_count(self):
        for board in self:
            board.trust_count = len(board.trust_ids)
