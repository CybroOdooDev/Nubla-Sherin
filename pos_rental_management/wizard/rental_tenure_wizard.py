from odoo import api, fields, models

class RentalProductTenure(models.TransientModel):
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
        string="Duration UoM",
        default='day',
        required=True,
    )
    range_start = fields.Integer()
    range_end = fields.Integer()
    amount = fields.Float()
    product_tmpl_id = fields.Many2one('product.template')

    def action_save_close(self):
        self._create_real_tenure()
        return {'type': 'ir.actions.act_window_close'}

    def action_save_new(self):
        self._create_real_tenure()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rental.product.tenure',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_tmpl_id': self.product_tmpl_id.id}
        }

    def _create_real_tenure(self):
        print("HHHHHHh")
        self.env['rental.product.tenure'].create({
            'name': self.name,
            'uom_id': self.uom_id.id,
            'range_start': self.range_start,
            'range_end': self.range_end,
            'amount': self.amount,
            'product_tmpl_id': self.product_tmpl_id.id,
        })
