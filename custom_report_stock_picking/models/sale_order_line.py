from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    delivery_description = fields.Text(
        string="Delivery Description",
        compute="_compute_delivery_description",
        store=True,
    )

    @api.depends('name', 'product_id')
    def _compute_delivery_description(self):
        for line in self:
            description = line.name or ''
            product_name = line.product_id.display_name or ''

            if product_name and description.startswith(product_name):
                description = description.replace(product_name, '', 1).strip()

            line.delivery_description = description
