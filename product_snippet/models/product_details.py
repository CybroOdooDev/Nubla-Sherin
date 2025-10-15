# -*- coding: utf-8 -*-
from odoo import fields, models

class ProductDetails(models.Model):
    _name = 'product.details'
    _rec_name = 'product_name'

    product_name = fields.Many2one('product.product')
    image = fields.Image()
    price = fields.Float()