from odoo import api, fields, models


class ProductTemplate(models.Model):
    """ Extend product template for library management """
    _inherit = 'product.template'


    is_rental = fields.Boolean(string="rental product")
    is_security_required = fields.Boolean("Is Security Amount Required")
    rental_tenure_ids = fields.One2many(
        'rental.product.tenure',
        'product_tmpl_id',
        string="Rental Product Tenure"
    )