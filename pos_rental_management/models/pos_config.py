# models/pos_config.py
from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    rental_security_product_id = fields.Many2one(
        'product.product',
        string="Default Rental Security Product",
        domain=[('type', '=', 'service'),('available_in_pos', '=', True)],
    )

    allow_partial_payment = fields.Boolean(
        string="Allow Partial Payment",
        config_parameter='pos_rental.allow_partial_payment'
    )
