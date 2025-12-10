
from odoo import fields, models,api


class ResPartner(models.Model):
    """
    This class extends the 'res.partner' model to introduce the 'prevent_partial_payment'
    field.
    """
    _inherit = 'res.partner'

    prevent_partial_payment = fields.Boolean(
        string="Don't allow Partial Payment in POS",
        help="If enabled, partial payments will be prevented for Point of Sale "
             "orders associated with this partner.")

    @api.model
    def _load_pos_data_fields(self, config_id):
        data = super()._load_pos_data_fields(config_id)
        data += ['prevent_partial_payment']
        return data