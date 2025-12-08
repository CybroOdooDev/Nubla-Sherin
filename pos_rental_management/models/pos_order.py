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



class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    is_rented = fields.Boolean(string="Is Rented", default=False)

    rental_tenure_id = fields.Many2one(
        'rental.product.tenure',
        string="Rental Tenure"
    )

    rental_tenure_name = fields.Char(
        compute='_compute_rental_tenure_name',
        store=True
    )

    @api.depends('rental_tenure_id.name')
    def _compute_rental_tenure_name(self):
        for line in self:
            line.rental_tenure_name = (
                line.rental_tenure_id.name if line.rental_tenure_id else ""
            )
