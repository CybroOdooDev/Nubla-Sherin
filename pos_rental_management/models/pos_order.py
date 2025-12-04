from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = "pos.order"

    is_rented = fields.Boolean(
        string="Rented",
        compute="_compute_is_rented",
        store=True
    )

    @api.depends('lines.product_id')
    def _compute_is_rented(self):
        for order in self:
            order.is_rented = any(line.product_id.is_rental for line in order.lines)






