# -*- coding: utf-8 -*-
#######################################################################################
#
#    Hai Cheung (China) Limited
#
#    Copyright (C) Hai Cheung (China) Limited.
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
########################################################################################
from odoo import fields, models


class SalaryHistoryInherit(models.Model):
    _inherit = 'salary.history'

    employee_id = fields.Many2one(
        'hr.employee',
        related="contract_history_id.contract_id.employee_id",
        string="Employee",
        store=True
    )
