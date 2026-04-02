# -*- coding: utf-8 -*-
from odoo import api, fields, models

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_hotel_charge = fields.Boolean(string='Is Hotel Charge',
                                     help='Check this if you want to use this payment method for hotel room charge.')

    @api.model
    def _load_pos_data_fields(self, config):
        """Expose `is_hotel_charge` in the POS frontend models."""
        fields_list = super()._load_pos_data_fields(config)
        if 'is_hotel_charge' not in fields_list:
            fields_list.append('is_hotel_charge')
        return fields_list
