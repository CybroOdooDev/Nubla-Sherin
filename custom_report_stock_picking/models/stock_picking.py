# -*- coding: utf-8 -*-
################################################################################
#
#    Cats and Dogs Solution
#
#    Copyright (C) Cats and Dogs Solution.
#
#    This program is under the terms of the Odoo Proprietary License v1.0
#    (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
################################################################################
from odoo import fields, models ,_


class StockPicking(models.Model):
    _inherit = "stock.picking"

    delivery_info = fields.Text(related='sale_id.delivery_info')