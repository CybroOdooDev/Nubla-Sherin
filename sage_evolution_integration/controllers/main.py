from odoo import http
from odoo.http import request
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class SageCallback(http.Controller):

    @http.route('/sage_evolution_integration/callback', type='http', auth="user", website=False)
    def sage_callback(self, **kwargs):
        code = kwargs.get('code')
        state = kwargs.get('state')
        
        icp = request.env['ir.config_parameter'].sudo()
        stored_state = icp.get_param('sage_evolution_integration.auth_state')
        
        if state != stored_state:
            return "Invalid State! Possible CSRF attack."

        client_id = icp.get_param('sage_evolution_integration.sage_client_id')
        client_secret = icp.get_param('sage_evolution_integration.sage_client_secret')
        base_url = icp.get_param('web.base.url')
        redirect_uri = f"{base_url}/sage_evolution_integration/callback"

        # Exchange code for token (Sage ID)
        token_url = "https://id.sage.com/oauth/token"
        payload = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }

        try:
            response = requests.post(token_url, data=payload)
            response.raise_for_status()
            token_data = response.json()
            
            # Store tokens
            icp.set_param('sage_evolution_integration.sage_auth_token', token_data.get('access_token'))
            icp.set_param('sage_evolution_integration.sage_refresh_token', token_data.get('refresh_token'))
            
            return request.render('sage_evolution_integration.sage_auth_success', {
                'message': 'Successfully connected to Sage!'
            })
        except Exception as e:
            _logger.error("Sage Auth Error: %s", str(e))
            return f"Authentication Failed: {str(e)}"
