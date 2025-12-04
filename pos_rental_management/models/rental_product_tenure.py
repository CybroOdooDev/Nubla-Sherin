from odoo import api, fields, models

class RentalProductTenure(models.Model):
    _name = 'rental.product.tenure'
    _description = 'Rental Product Tenure'

    name = fields.Char(required=True)
    duration_uom = fields.Selection(
        [
            ('day', 'Day(s)'),
            ('week', 'Week(s)'),
            ('month', 'Month(s)'),
            ('year', 'Year(s)'),
        ],
        default='day',
        required=True,
    )
    range_start = fields.Integer(required=True)
    range_end = fields.Integer(required=True)
    amount = fields.Float(required=True)

    product_tmpl_id = fields.Many2one('product.template')

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            "name",
            "duration_uom",
            "range_start",
            "range_end",
            "amount",
            "product_tmpl_id",
        ]

    @api.model
    def _load_pos_data_search_read(self, response, config_id):
        # do NOT index response by self._name
        fields = self._load_pos_data_fields(config_id)
        domain = []  # or restrict by config if you want
        return self.search_read(domain, fields)



    def action_open_tenure_popup(self):
        return {
            'name': "Create Rental Product Tenure",
            'type': 'ir.actions.act_window',
            'res_model': 'rental.product.tenure',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_tmpl_id': self.id,
            }
        }

    def action_save_close(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_save_new(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rental.product.tenure',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_tmpl_id': self.product_tmpl_id.id},
        }



