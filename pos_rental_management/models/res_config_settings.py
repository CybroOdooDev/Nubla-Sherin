from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    rental_security_product_id = fields.Many2one(
        'product.product',
        string="Default Rental Security Product",
        config_parameter='pos_rental_management.rental_security_product_id',
        domain=[('is_rental', '=', True)],
        help="Default Rental Security Product for POS Orders."
    )

    allow_partial_payment = fields.Boolean(
        string="Allow Partial Payment",
        config_parameter='pos_rental.allow_partial_payment'
    )
