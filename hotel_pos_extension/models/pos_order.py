# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    booking_id = fields.Many2one('room.booking', string='Hotel Booking', help='Hotel booking associated with this POS order.')

    def _ensure_hotel_pos_line(self):
        """Ensure the booking shows the POS order under the 'POS Orders' tab.

        The POS can create an order as draft first and later update/validate it (same uuid),
        adding the hotel-charge payment method afterwards. In that flow, relying only on
        `create()` is not enough.
        """
        HotelPosLine = self.env['hotel.pos.line']
        for order in self:
            if not order.booking_id:
                continue

            link = HotelPosLine.search([('pos_order_id', '=', order.id)], limit=1)
            if link:
                if link.booking_id != order.booking_id:
                    link.booking_id = order.booking_id.id
                continue

            HotelPosLine.create({
                'booking_id': order.booking_id.id,
                'pos_order_id': order.id,
            })

    @api.model
    def _order_fields(self, ui_order):
        """Add booking_id to the order fields"""
        res = super(PosOrder, self)._order_fields(ui_order)
        res['booking_id'] = ui_order.get('booking_id', False)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Create Hotel POS Line if the order is charged to a room"""
        orders = super(PosOrder, self).create(vals_list)
        orders._ensure_hotel_pos_line()
        return orders

    def write(self, vals):
        res = super().write(vals)
        # Create/update the link record when the order is later validated and payments are added.
        self._ensure_hotel_pos_line()
        return res

    @api.model
    def _process_order(self, order, existing_order):
        """Ensure booking linkage survives the POS sync lifecycle.

        In Odoo 19, POS orders can be created/updated in multiple passes. We
        re-apply booking_id after super() and then ensure the hotel POS link.
        """
        booking_id = order.get('booking_id')
        order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(order_id)
        if booking_id and pos_order.booking_id.id != booking_id:
            pos_order.write({'booking_id': booking_id})
        pos_order._ensure_hotel_pos_line()
        return order_id

    def _generate_pos_order_invoice(self):
        """Override to forcefully keep the invoice 'Not Paid' for hotel charges.
        We use a context flag that is caught by our AccountMoveLine.reconcile override.
        """
        is_hotel_charge = self.booking_id or any(p.payment_method_id.is_hotel_charge or p.payment_method_id.type == 'pay_later' for p in self.payment_ids)
        if is_hotel_charge:
            # We call super with a context flag that prevents reconciliation at the line level.
            # This is the most absolute way to ensure the invoice remains 'Not Paid'.
            move = super(PosOrder, self.with_context(skip_pos_invoice_reconciliation=True))._generate_pos_order_invoice()
            
            # Final safeguard for Odoo 19: remove any already applied reconciliation 
            # and refresh the move amounts to ensure 'not_paid' status.
            # We do it on all lines to be sure.
            move.line_ids.sudo().remove_move_reconcile()
            
            # Also ensure payment lines of this order are NOT reconciled with this invoice
            for payment in self.payment_ids:
                if payment.account_move_id:
                    payment.account_move_id.line_ids.sudo().remove_move_reconcile()
            
            # Explicitly clear any partials involving this move's lines (critical if Odoo auto-reconciled)
            self.env['account.partial.reconcile'].sudo().search([
                '|', ('debit_move_id', 'in', move.line_ids.ids),
                ('credit_move_id', 'in', move.line_ids.ids)
            ]).unlink()

            move.sudo()._compute_amount()
            # Force payment_state recompute
            move._compute_payment_state()
            return move
            
        return super()._generate_pos_order_invoice()

    def _reconcile_invoice_payments(self, invoice, payment_moves):
        """Secondary layer to skip reconciliation for hotel room charges in Odoo 19."""
        is_hotel_charge = self.booking_id or any(p.payment_method_id.is_hotel_charge or p.payment_method_id.type == 'pay_later' for p in self.payment_ids)
        if self.env.context.get('skip_pos_invoice_reconciliation') or is_hotel_charge:
            return

        return super()._reconcile_invoice_payments(invoice, payment_moves)

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('payment_state', 'state', 'is_move_sent', 'pos_order_ids')
    def _compute_status_in_payment(self):
        """Override to show 'Not Paid' for hotel POS invoices even if they are sent.
        
        This aligns with the hotel workflow where POS charges are only settled at checkout.
        """
        super()._compute_status_in_payment()
        for move in self:
            if move.state == 'posted' and move.payment_state == 'not_paid':
                # Check if this invoice is from a hotel POS order (has booking_id or specific payment methods)
                # Standard Odoo 19 field name is pos_order_ids (One2many)
                if move.pos_order_ids.filtered(lambda o: o.booking_id or any(p.payment_method_id.is_hotel_charge or p.payment_method_id.type == 'pay_later' for p in o.payment_ids)):
                    move.status_in_payment = 'not_paid'

