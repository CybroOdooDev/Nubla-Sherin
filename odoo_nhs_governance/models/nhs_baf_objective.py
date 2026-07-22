# -*- coding: utf-8 -*-
from odoo import fields, models


class NhsBafObjective(models.Model):
    _name = 'nhs.baf.objective'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'NHS BAF Strategic Objective'
    _order = 'code, name'

    name = fields.Char(required=True, tracking=True, help="Strategic objective set by the board.")
    code = fields.Char(help="Objective reference code used in BAF reporting.")
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning organisation for company-level security.",
    )
    lead_director_id = fields.Many2one(
        'nhs.director',
        string='Lead Director',
        help="Executive lead responsible for this strategic objective.",
    )
    risk_ids = fields.One2many(
        'nhs.baf.risk',
        'objective_id',
        help="Principal risks that threaten delivery of this strategic objective.",
    )
    active = fields.Boolean(default=True, help="Archive flag for objectives no longer in the active BAF.")
