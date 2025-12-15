# models/pos_session.py
from odoo import models,api
import json


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        if 'pos.receipt' not in res:
            res.append('pos.receipt')
        return res

    def _loader_params_pos_receipt(self):
        return {
            'search_params': {
                'fields': ['id', 'design_receipt'],
            }
        }

    # @api.model
    # def _load_pos_data_fields(self, config_id):
    #     # Make sure receipt_id is included
    #     return super()._load_pos_data_fields(config_id) + ['receipt_design_id']


