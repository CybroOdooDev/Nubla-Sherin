# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class WebsitePartnerSnippetController(http.Controller):
   @http.route('/get_website_product', type='jsonrpc', auth='public', website=True, csrf=False)
   def get_website_partners(self):
       products = request.env['product.details'].sudo().search([

       ], limit=4)

       product_list = [{
           'product_name': product.product_name,
           'price': product.price or '',
           'image': f"data:image/png;base64,{product.image_1920.decode()}"
       } for product in products]
       print(product_list)
       return {'partner_list': product_list}