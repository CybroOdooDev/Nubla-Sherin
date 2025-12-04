from odoo import http
from odoo.http import request

class RentalController(http.Controller):

    @http.route('/pos/get_rented_products', type='json', auth='public')
    def get_rented_products(self, partner_id):
        print("mainnnnnnnnnnnnnn")
        orders = request.env['pos.order'].sudo().search([
            ('partner_id', '=', partner_id),
            ('is_rented', '=', True)
        ])

        rented_data = []

        for order in orders:
            for line in order.lines:
                if line.product_id.is_rental:
                    rented_data.append({
                        "order_name": order.name,
                        "product_name": line.product_id.name,
                        "quantity": line.qty,

                    })

        return rented_data
