from odoo import models, fields, api
from odoo.http import request
import secrets
from urllib.parse import urlencode
import time
import logging

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Sage 200 Evolution Freedom Service Credentials
    sage_evolution_api_url = fields.Char(string='Evolution API URL', config_parameter='sage_evolution_integration.sage_api_url', help="e.g. http://192.168.1.100:8080/FreedomService")
    sage_evolution_db = fields.Char(string='Evolution Database', config_parameter='sage_evolution_integration.sage_company_db')
    sage_evolution_username = fields.Char(string='Evolution Username', config_parameter='sage_evolution_integration.sage_api_username')
    sage_evolution_password = fields.Char(string='Evolution Password', config_parameter='sage_evolution_integration.sage_api_password')

    # Sage Cloud OAuth Credentials
    sage_client_id = fields.Char(string='Sage Client ID', config_parameter='sage_evolution_integration.sage_client_id')
    sage_client_secret = fields.Char(string='Sage Client Secret', config_parameter='sage_evolution_integration.sage_client_secret')
    sage_auth_token = fields.Char(string='Access Token', config_parameter='sage_evolution_integration.sage_auth_token')

    def action_test_freedom_connection(self):
        """ Test connection to Sage 200 Evolution Freedom Service """
        import requests
        from requests.auth import HTTPBasicAuth

        url = (self.sage_evolution_api_url or "").rstrip('/')
        if not url:
            raise UserError("Please enter the Evolution API URL first.")
        
        # Test a simple endpoint like Customers or common GET
        test_url = f"{url}/Customers"
        try:
            response = requests.get(
                test_url,
                auth=HTTPBasicAuth(self.sage_evolution_username, self.sage_evolution_password),
                timeout=10
            )
            if response.status_code == 200:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'Successfully connected to Sage 200 Evolution Freedom Service.',
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection Failed',
                        'message': f'Status Code: {response.status_code} - {response.text[:200]}',
                        'type': 'danger',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Error',
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def action_connect_to_sage(self):
        """ Redirect to Sage Authorization URL """
        if not self.sage_client_id:
            raise UserError("Please enter the Client ID first.")
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Force https for redirect_uri as required by Sage ID and ngrok
        if base_url and base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://', 1)
        redirect_uri = f"{base_url}/sage_evolution_integration/callback"
        
        # For Sage Distribution & Manufacturing Operations (SDMO) / Sage ID:
        auth_url = "https://id.sage.com/authorize"
        audience = "https://api.columbus.sage.com/global/sdmo"
        
        params = {
            'client_id': self.sage_client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            # Try without audience first to see if it resolves 'permission' issues
            # 'audience': "https://api.columbus.sage.com/global/sdmo",
            'scope': 'openid profile email offline_access', 
            'state': secrets.token_urlsafe(16)
        }
        
        # Store state to verify in callback
        self.env['ir.config_parameter'].sudo().set_param('sage_evolution_integration.auth_state', params['state'])
        
        url = f"{auth_url}?{urlencode(params)}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }
from odoo.exceptions import UserError
