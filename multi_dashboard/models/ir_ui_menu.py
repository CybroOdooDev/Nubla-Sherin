# -*- coding: utf-8 -*-
from odoo import fields, models


class IrUiMenu(models.Model):
    """ Inherit ir.ui.menu to add new field is_from_multi_dashboard which helps
    to identify the menu created from multi dashboard or not."""
    _inherit = "ir.ui.menu"

    is_from_multi_dashboard = fields.Boolean(string="From Multi Dashboard",
                                             help="This menu is created from multi dashboard")
