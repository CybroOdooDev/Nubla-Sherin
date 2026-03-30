from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    sage_id = fields.Char(string='Sage ID', copy=False)
    sage_account_code = fields.Char(string='Sage Account Code', copy=False)

    def action_export_to_sage(self):
        """ Server action to export selected contacts to Sage """
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return False
        
        # This will call the sync log method
        return self.env['sage.sync.log'].push_customers(active_ids)
