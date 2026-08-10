from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sage_id = fields.Char(string='Sage ID', copy=False, help="Internal ID from Sage Evolution")
    sage_order_number = fields.Char(string='Sage Order Number', copy=False)
