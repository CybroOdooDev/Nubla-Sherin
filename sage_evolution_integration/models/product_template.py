from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sage_id = fields.Char(string='Sage ID', help='Internal ID from Sage Evolution')
    sage_code = fields.Char(string='Sage Code', help='Item Code from Sage Evolution')
