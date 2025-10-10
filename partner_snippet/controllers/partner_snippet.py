# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class WebsitePartnerSnippetController(http.Controller):
   @http.route('/get_website_partners', type='jsonrpc', auth='public', website=True, csrf=False)
   def get_website_partners(self):
       partners = request.env['res.partner'].sudo().search([
           ('invoice_ids.move_type', '=', 'out_invoice'),
           ('invoice_ids.state', '=', 'posted'),
           ('image_1920', '!=', False)
       ], limit=4)

       partner_list = [{
           'name': partner.name,
           'email': partner.email or '',
           'image': f"data:image/png;base64,{partner.image_1920.decode()}"
       } for partner in partners]

       return {'partner_list': partner_list}