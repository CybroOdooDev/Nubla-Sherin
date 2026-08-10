import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class EpicController(http.Controller):
    @http.route('/epic/jwks.json', type='http', auth='public', csrf=False, cors='*')
    def epic_jwks(self, **kw):
        # Epic fetches this URL without an Odoo session. In multi-company DBs the "first"
        # company may not be the one configured for Epic, so pick the first company that
        # actually has a JWKS configured.
        Company = request.env['res.company'].sudo()
        company = Company.search([('epic_jwks', '!=', False)], limit=1) or Company.search([], limit=1)
        if company and company.epic_jwks:
            try:
                jwks_data = json.loads(company.epic_jwks)
                return request.make_response(
                    json.dumps(jwks_data),
                    headers=[('Content-Type', 'application/json')],
                )
            except Exception:
                _logger.exception("Invalid Epic JWKS JSON configured on company id=%s", company.id)
                return request.make_response(
                    json.dumps({"error": "Invalid JWKS JSON configured"}),
                    headers=[('Content-Type', 'application/json')],
                    status=500,
                )
        
        return request.make_response(
            json.dumps({"error": "JWKS not configured"}),
            headers=[('Content-Type', 'application/json')],
            status=404
        )
