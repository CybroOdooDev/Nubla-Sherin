from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    admission_id = fields.Many2one('hospital.admission', string="Admission")
