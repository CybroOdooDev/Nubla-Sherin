# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_to_repair_ids = fields.Many2many('product.product', domain=[('categ_id', '=' , 'Electrical')])



