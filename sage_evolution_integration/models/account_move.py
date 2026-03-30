from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    sage_id = fields.Char(string='Sage ID', help='Internal ID from Sage Evolution', copy=False)
    sage_invoice_number = fields.Char(string='Sage Invoice Number', help='Invoice Number from Sage Evolution', copy=False)
