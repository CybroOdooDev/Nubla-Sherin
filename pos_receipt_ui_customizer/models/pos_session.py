from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        if 'pos.receipt' not in res:
            res.append('pos.receipt')
        return res

    def _loader_params_pos_config(self):
        res = super()._loader_params_pos_config()
        res['search_params']['fields'].extend([
            'is_custom_receipt',
            'receipt_design_id',
            'design_receipt',
            'design_receipt_font_style',
            'selected_product_fields',
            'selected_columns_config'
        ])
        return res

    def _loader_params_pos_receipt(self):
        return {
            'search_params': {
                'fields': [
                    'id', 'design_receipt', 'design_receipt_font_style', 
                    'is_custom_receipt', 'selected_product_fields', 'selected_columns_config'
                ],
            }
        }

    # @api.model
    # def _load_pos_data_fields(self, config_id):
    #     # Make sure receipt_id is included
    #     return super()._load_pos_data_fields(config_id) + ['receipt_design_id']


