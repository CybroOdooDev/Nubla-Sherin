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
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    keep_description = fields.Boolean(
        string="Keep Description",
        help="If enabled, Keep description from sales order upon the delivery slips."
    )
