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
from odoo import fields, models,api


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    remarks = fields.Char(string='Remarks', tracking = True)
    receive_payment_in = fields.Selection([
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
    ], string='Receive Payment In', tracking = True , required=True)
    employee_bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Bank Account Number',
        domain="[('id', 'in', employee_bank_account_ids)]"
    )
    employee_bank_account_ids = fields.Many2many(
        'res.partner.bank',
        compute='_compute_employee_bank_accounts',
        string='Employee Bank Accounts',
        store=False
    )

    @api.depends('employee_id')
    def _compute_employee_bank_accounts(self):
        """Get employee's linked bank accounts."""
        for rec in self:
            if rec.employee_id and rec.employee_id.bank_account_id:
                rec.employee_bank_account_ids = rec.employee_id.bank_account_id
            else:
                rec.employee_bank_account_ids = False