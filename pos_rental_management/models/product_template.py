from odoo import api, fields, models


class ProductTemplate(models.Model):
    """ Extend product template for library management """
    _inherit = 'product.template'


    is_rental = fields.Boolean(string="rental product")
    is_security_required = fields.Boolean("Is Security Amount Required")
    security_amount = fields.Float(string="Security Amount")
    rental_tenure_ids = fields.One2many(
        'rental.product.tenure',
        'product_tmpl_id',
        string="Rental Product Tenure"
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += [
            'is_rental',
            'is_security_required',
            'security_amount',
            'rental_tenure_ids',
        ]
        return fields
