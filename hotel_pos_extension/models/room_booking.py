# -*- coding: utf-8 -*-
from odoo import api, fields, models
        
class RoomBooking(models.Model):
    _inherit = 'room.booking'

    pos_order_line_ids = fields.One2many('hotel.pos.line', 'booking_id', string='POS Orders')
    amount_total_pos = fields.Monetary(string="Total POS Amount", compute='_compute_amount_untaxed')

    @api.depends(
        'room_line_ids.price_subtotal', 'room_line_ids.price_tax', 'room_line_ids.price_total',
        'food_order_line_ids.price_subtotal', 'food_order_line_ids.price_tax', 'food_order_line_ids.price_total',
        'service_line_ids.price_subtotal', 'service_line_ids.price_tax', 'service_line_ids.price_total',
        'vehicle_line_ids.price_subtotal', 'vehicle_line_ids.price_tax', 'vehicle_line_ids.price_total',
        'event_line_ids.price_subtotal', 'event_line_ids.price_tax', 'event_line_ids.price_total',
        # POS charges linked to the booking.
        'pos_order_line_ids.pos_order_id.amount_total',
        'pos_order_line_ids.pos_order_id.currency_id',
        'pos_order_line_ids.pos_order_id.state',
    )
    def _compute_amount_untaxed(self, flag=False):
        """Extended calculation to include POS charges and add to invoice list"""
        booking_list = super(RoomBooking, self)._compute_amount_untaxed(flag=flag)
        
        for rec in self:
            amount_total_pos = sum(rec.pos_order_line_ids.mapped('amount_total'))
            rec.amount_total_pos = amount_total_pos
            rec.amount_total += amount_total_pos
            # Since POS orders are already taxed, we add to total.
            # We also add to amount_untaxed for consistent subtotal display projects, 
            # though this is technically an approximation if the POS order has taxes.
            rec.amount_untaxed += amount_total_pos 
            
            if flag:
                # Add POS orders to the booking_list for invoicing
                for line in rec.pos_order_line_ids:
                    # Explode POS order into individual items for the folio
                    for pos_line in line.pos_order_id.lines:
                        booking_list.append({
                            'name': f"POS: {pos_line.full_product_name or pos_line.product_id.name} (Ref: {line.pos_reference or ''})",
                            'quantity': pos_line.qty,
                            'price_unit': pos_line.price_unit,
                            'product_type': 'pos'
                        })
        return booking_list

    pos_invoice_count = fields.Integer(compute='_compute_pos_invoice_count', string='POS Invoice Count')

    def _compute_pos_invoice_count(self):
        for rec in self:
            invoices = rec.pos_order_line_ids.mapped('pos_order_id.account_move')
            rec.pos_invoice_count = len(invoices.filtered(lambda x: x.state != 'cancel'))

    def action_view_pos_invoices(self):
        self.ensure_one()
        invoices = self.pos_order_line_ids.mapped('pos_order_id.account_move').filtered(lambda x: x.state != 'cancel')
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
