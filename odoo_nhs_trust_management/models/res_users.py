# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    nhs_allowed_icb_ids = fields.Many2many(
        'nhs.icb',
        'nhs_user_icb_rel',
        'user_id',
        'icb_id',
        string='Allowed ICBs (England)',
        help='Users will only be able to see NHS Trusts associated with these Integrated Care Boards (ICBs).'
    )
    nhs_allowed_health_board_ids = fields.Many2many(
        'nhs.health.board',
        'nhs_user_health_board_rel',
        'user_id',
        'health_board_id',
        string='Allowed Health Boards (Scotland)',
        help='Users will only be able to see NHS Trusts associated with these Scottish Health Boards.'
    )
