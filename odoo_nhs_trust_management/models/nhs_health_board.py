# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class NhsHealthBoard(models.Model):
    _name = 'nhs.health.board'
    _description = 'NHS Scotland Health Board'
    _order = 'name'
    _rec_name = 'name'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Name', 
        required=True, 
        index=True, 
        tracking=True,
        help="Full statutory name (e.g. 'NHS Greater Glasgow and Clyde'). Tracked on chatter."
    )
    code = fields.Char(
        string='ODS Code', 
        required=True, 
        index=True,
        help="Official Scottish Government Health Board code. Format S08000xxx for territorial, SBxxxx for national. Used in PHS / ISD Scotland reporting datasets — keep aligned with national codes."
    )
    short_name = fields.Char(
        string='Short Name',
        help="Optional short name (e.g. 'NHS GGC' for Greater Glasgow and Clyde)."
    )
    region_id = fields.Many2one(
        'nhs.region',
        string='NHS Region',
        domain="[('health_system', '=', 'nhs_scotland')]",
        index=True,
        help="Optional grouping region (North/East/West Scotland). National boards may leave this empty."
    )
    board_type = fields.Selection([
        ('territorial', 'Territorial Health Board'),
        ('national', 'National Health Board'),
    ], 
        string='Board Type', 
        required=True, 
        default='territorial', 
        index=True,
        help="Selection: 'territorial' or 'national'. Default: 'territorial'. Territorial boards serve a geographic population. National boards serve specific functions (e.g. ambulance, public health, training) Scotland-wide."
    )
    population_served = fields.Integer(
        string='Population Served',
        help="Resident population the board is responsible for (territorial only)."
    )
    headquarters_address = fields.Text(
        string='Headquarters Address',
        help="Free-text HQ address."
    )
    website = fields.Char(
        string='Website',
        help="Public board website."
    )
    trust_ids = fields.One2many(
        'nhs.trust', 
        'health_board_id', 
        string='Associated Trusts',
        help="Trusts whose health_board_id points here. In Scotland the Health Board IS often the Trust — but the data model supports both for flexibility."
    )
    trust_count = fields.Integer(
        string='Trusts Count', 
        compute='_compute_trust_count',
        help="Count of linked trusts."
    )
    active = fields.Boolean(
        string='Active', 
        default=True,
        help="Archive flag."
    )


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
