# -*- coding: utf-8 -*-
from odoo import models, api, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        # After payment is posted and reconciled, create fitness.payment records
        for payment in self:
            reconciled_invoices = payment.reconciled_invoice_ids
            if reconciled_invoices:
                subscriptions = self.env['fitness.subscription'].sudo().search(
                    [('invoice_ids', 'in', reconciled_invoices.ids)]
                )
                for sub in subscriptions:
                    existing = self.env['fitness.payment'].sudo().search(
                        [('subscription_id', '=', sub.id)], limit=1
                    )
                    if not existing:
                        self.env['fitness.payment'].sudo().create({
                            'subscription_id': sub.id,
                            'amount': payment.amount,
                            'payment_date': payment.date or fields.Date.context_today(self),
                            'payment_method': 'other',
                        })
                    # Also activate the subscription
                    if sub.state == 'draft':
                        sub.state = 'active'
        return res
