# -*- coding: utf-8 -*-
from odoo import fields, models

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    product_type = fields.Selection(selection_add=[('pos', 'POS')],
                                    ondelete={'pos': 'cascade'})

    def reconcile(self):
        """Skip reconciliation ONLY if the context flag is explicitly set.
        This prevents POS from auto-paying invoices with POS payments,
        but allows manual 'Pay' button and reconciliation to work.
        """
        if self.env.context.get('skip_pos_invoice_reconciliation'):
            return True

        return super().reconcile()
