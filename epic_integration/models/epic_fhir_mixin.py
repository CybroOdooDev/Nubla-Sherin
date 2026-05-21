import json
import logging
import time
import uuid
import requests

from odoo import models, exceptions

_logger = logging.getLogger(__name__)

try:
    import jwt
except ImportError:
    jwt = None


class EpicFhirMixin(models.AbstractModel):
    _name = 'epic.fhir.mixin'
    _description = 'Epic FHIR Shared Authentication Mixin'

    def _epic_get_access_token(self, company):
        if not jwt:
            raise exceptions.UserError("PyJWT library required. Run: pip install PyJWT")

        use_sandbox = (not company.epic_environment or company.epic_environment == 'sandbox')
        client_id = company.epic_non_production_client_id if use_sandbox else company.epic_client_id
        private_key = (company.epic_private_key or '').strip()
        token_endpoint = (company.epic_token_endpoint or '').strip()

        if not all([client_id, private_key, token_endpoint]):
            raise exceptions.UserError(
                "Epic Client ID, Private Key, and Token Endpoint must all be configured in Settings."
            )
        if not private_key.startswith('-----BEGIN'):
            raise exceptions.UserError(
                "Epic Private Key must be PEM-formatted (starting with '-----BEGIN ...')."
            )

        now = int(time.time())
        payload = {
            'iss': client_id,
            'sub': client_id,
            'aud': token_endpoint,
            'jti': str(uuid.uuid4()),
            'exp': now + 300,
            'nbf': now,
            'iat': now,
        }

        jwt_headers = {'typ': 'JWT'}
        if company.epic_jwks:
            try:
                jwks = json.loads(company.epic_jwks)
                keys = jwks.get('keys') if isinstance(jwks, dict) else None
                if isinstance(keys, list) and keys:
                    kid = keys[0].get('kid')
                    if kid:
                        jwt_headers['kid'] = kid
            except Exception:
                pass

        encoded_jwt = jwt.encode(payload, private_key, algorithm='RS384', headers=jwt_headers)
        if isinstance(encoded_jwt, bytes):
            encoded_jwt = encoded_jwt.decode('utf-8')

        response = requests.post(
            token_endpoint,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'client_credentials',
                'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
                'client_assertion': encoded_jwt,
            },
            timeout=15,
        )
        if not response.ok:
            _logger.error("Epic token request failed %s: %s", response.status_code, response.text)
            raise exceptions.UserError(
                f"Epic authentication failed ({response.status_code}):\n{response.text}"
            )

        token_data = response.json()
        granted_scope = token_data.get('scope', '')
        if granted_scope:
            _logger.info("Epic token granted scopes: %s", granted_scope)
        else:
            _logger.warning("Epic token granted NO scopes — check Epic App Orchard API configuration.")

        return token_data.get('access_token'), granted_scope

    def _epic_has_scope(self, required_scope, granted_scope):
        """Return True if granted_scope contains required_scope (exact or qualified variant)."""
        granted = granted_scope or ''
        return any(
            token == required_scope or token.startswith(required_scope + '?')
            for token in granted.split()
        )

    def _epic_check_scope(self, required_scope, granted_scope):
        if not self._epic_has_scope(required_scope, granted_scope):
            resource = required_scope.replace('system/', '').split('.')[0]
            is_write = required_scope.endswith('.write')
            if is_write:
                api_hint = (
                    f"  2. Search for '{resource}.Create'\n"
                    f"  3. Add '{resource}.Create (Demographics) (R4)' or any available\n"
                    f"     qualified (R4) Create variant for your use case.\n"
                    f"     (The Open Epic sandbox only provides qualified R4 versions.)\n"
                )
            else:
                api_hint = (
                    f"  2. Search for '{resource}.Read' and '{resource}.Search'\n"
                    f"  3. Add ALL available (R4) versions — including qualified ones like\n"
                    f"     '{resource}.Read (Demographics) (R4)', etc.\n"
                    f"     (The Open Epic sandbox only provides qualified R4 versions.)\n"
                )
            raise exceptions.UserError(
                f"Epic did not grant '{required_scope}' scope.\n\n"
                f"Scopes currently granted: {granted_scope or '(none)'}\n\n"
                f"To fix in Epic App Orchard:\n"
                f"  1. Open your app → Incoming APIs\n"
                + api_hint +
                f"  4. Save the app, wait ~1 minute, then retry."
            )

    def _epic_fhir_url(self, company, resource):
        base = (company.epic_fhir_base_url or '').rstrip('/')
        if '/api/FHIR/' in base:
            return f"{base}/{resource}"
        return f"{base}/api/FHIR/R4/{resource}"

    def _epic_fhir_get(self, access_token, url, params=None):
        from urllib.parse import urlencode
        headers = {'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'}
        response = requests.get(url, headers=headers, params=params or None, timeout=30)
        if response.status_code >= 400:
            www_auth = response.headers.get('WWW-Authenticate', '')
            qs = ('?' + urlencode(params, doseq=True)) if params else ''
            _logger.error("Epic FHIR failed %s %s | WWW-Auth: %s | Body: %s",
                          response.status_code, f"{url}{qs}", www_auth, response.text)
            details = response.text or ''
            if www_auth:
                details += f"\nWWW-Authenticate: {www_auth}"
            if response.status_code == 403 and 'insufficient_scope' in www_auth:
                details += (
                    "\n\nFix: Add the required Read/Search (R4) APIs to your app in Epic App Orchard."
                )
            raise exceptions.UserError(
                f"Epic FHIR API request failed ({response.status_code}) for {url}{qs}.\n{details}".strip()
            )
        return response.json()

    def _epic_fhir_post(self, access_token, url, json_data):
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        response = requests.post(url, headers=headers, json=json_data, timeout=30)
        if response.status_code >= 400:
            www_auth = response.headers.get('WWW-Authenticate', '')
            _logger.error("Epic FHIR POST failed %s %s | WWW-Auth: %s | Body: %s",
                          response.status_code, url, www_auth, response.text)
            details = response.text or ''
            if www_auth:
                details += f"\nWWW-Authenticate: {www_auth}"
            raise exceptions.UserError(
                f"Epic FHIR API creation failed ({response.status_code}) for {url}.\n{details}".strip()
            )
        return response.json()
