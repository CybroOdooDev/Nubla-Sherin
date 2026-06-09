# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    nhs_allowed_welsh_lhb_ids = fields.Many2many(
        'nhs.welsh.lhb',
        'nhs_user_welsh_lhb_rel',
        'user_id',
        'lhb_id',
        string='Allowed Welsh LHBs',
        help="Welsh Local Health Boards this user may see trusts for. Empty = no Welsh access.",
    )
    nhs_allowed_region_ids = fields.Many2many(
        'nhs.region',
        'nhs_user_region_rel',
        'user_id',
        'region_id',
        string='Allowed Regions',
        help="Primarily for Northern Ireland users. Add Northern Ireland here to grant access to all NI HSC Trusts.",
    )
