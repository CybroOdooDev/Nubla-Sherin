# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_payment_state(self):
        """Override to sync fitness subscription status when payment_state changes."""
        old_states = {move.id: move.payment_state for move in self}
        super()._compute_payment_state()
        for move in self:
            new_state = move.payment_state
            old_state = old_states.get(move.id)
            if new_state != old_state and new_state in ('paid', 'in_payment'):
                self._sync_fitness_subscriptions(move)

    def _sync_fitness_subscriptions(self, move):
        """Sync fitness subscription and payment records when invoice is paid."""
        subscriptions = self.env['fitness.subscription'].sudo().search(
            [('invoice_ids', 'in', move.id)]
        )
        for sub in subscriptions:
            # Activate draft subscriptions
            if sub.state == 'draft':
                sub.state = 'active'

            # Create a fitness.payment record for backend tracking
            existing_payment = self.env['fitness.payment'].sudo().search(
                [('subscription_id', '=', sub.id)], limit=1
            )
            if not existing_payment:
                self.env['fitness.payment'].sudo().create({
                    'subscription_id': sub.id,
                    'amount': move.amount_total,
                    'payment_date': fields.Date.context_today(self),
                    'payment_method': 'card',
                })
