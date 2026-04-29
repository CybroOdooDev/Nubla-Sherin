# -*- coding: utf-8 -*-
import requests

from odoo import fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nhs_simple_environment = fields.Selection([
        ('sandbox', 'Sandbox (Testing)'),
        ('integration', 'Integration'),
        ('production', 'Production'),
    ], string='NHS Environment',
       config_parameter='nhs_simple.environment',
       default='sandbox')
    nhs_simple_apikey = fields.Char(string='NHS API Key',
                                    config_parameter='nhs_simple.apikey')

    def action_nhs_test_connection(self):
        """Calls NHS Hello World to verify the API key."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        env = ICP.get_param('nhs_simple.environment', 'sandbox')
        apikey = ICP.get_param('nhs_simple.apikey', '')
        if not apikey:
            raise UserError("Save the API key first.")

        urls = {
            'sandbox':     'https://sandbox.api.service.nhs.uk',
            'integration': 'https://int.api.service.nhs.uk',
            'production':  'https://api.service.nhs.uk',
        }
        url = f"{urls[env]}/hello-world/hello/application"
        try:
            resp = requests.get(url, headers={'apikey': apikey}, timeout=15)
            ok = resp.ok
            msg = resp.text[:300]
        except Exception as e:
            ok = False
            msg = str(e)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'NHS Connection OK' if ok else 'NHS Connection Failed',
                'message': msg,
                'type': 'success' if ok else 'danger',
                'sticky': not ok,
            },
        }
