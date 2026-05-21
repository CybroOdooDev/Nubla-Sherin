import json
import logging
import time
import uuid
import requests

from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Connection
    epic_client_id = fields.Char(related='company_id.epic_client_id', readonly=False)
    epic_non_production_client_id = fields.Char(related='company_id.epic_non_production_client_id', readonly=False)
    epic_environment = fields.Selection(related='company_id.epic_environment', readonly=False)
    epic_private_key = fields.Text(related='company_id.epic_private_key', readonly=False)
    epic_jwks = fields.Text(related='company_id.epic_jwks', readonly=False)
    epic_token_endpoint = fields.Char(related='company_id.epic_token_endpoint', readonly=False)
    epic_fhir_base_url = fields.Char(related='company_id.epic_fhir_base_url', readonly=False)

    # Practitioner
    epic_practitioner_search_identifier = fields.Char(related='company_id.epic_practitioner_search_identifier', readonly=False)
    epic_practitioner_search_family = fields.Char(related='company_id.epic_practitioner_search_family', readonly=False)
    epic_practitioner_search_given = fields.Char(related='company_id.epic_practitioner_search_given', readonly=False)
    epic_practitioner_search_name = fields.Char(related='company_id.epic_practitioner_search_name', readonly=False)

    # Appointment
    epic_appointment_search_date = fields.Date(related='company_id.epic_appointment_search_date', readonly=False)
    epic_appointment_search_status = fields.Char(related='company_id.epic_appointment_search_status', readonly=False)
    epic_appointment_search_patient = fields.Char(related='company_id.epic_appointment_search_patient', readonly=False)

    # Allergy
    epic_allergy_search_patient = fields.Char(related='company_id.epic_allergy_search_patient', readonly=False)

    # Condition
    epic_condition_search_patient = fields.Char(related='company_id.epic_condition_search_patient', readonly=False)
    epic_condition_search_category = fields.Selection(related='company_id.epic_condition_search_category', readonly=False)

    # Patient
    epic_patient_search_name = fields.Char(related='company_id.epic_patient_search_name', readonly=False)
    epic_patient_search_family = fields.Char(related='company_id.epic_patient_search_family', readonly=False)
    epic_patient_search_given = fields.Char(related='company_id.epic_patient_search_given', readonly=False)
    epic_patient_search_identifier = fields.Char(related='company_id.epic_patient_search_identifier', readonly=False)
    epic_patient_search_birthdate = fields.Date(related='company_id.epic_patient_search_birthdate', readonly=False)

    def action_test_epic_connection(self):
        if not pyjwt:
            raise exceptions.UserError("PyJWT library not installed. Run: pip install PyJWT")

        company = self.env.company
        use_sandbox = (not company.epic_environment or company.epic_environment == 'sandbox')
        client_id = company.epic_non_production_client_id if use_sandbox else company.epic_client_id
        private_key = (company.epic_private_key or '').strip()
        token_endpoint = (company.epic_token_endpoint or '').strip()
        fhir_base = (company.epic_fhir_base_url or '').rstrip('/')

        if not all([client_id, private_key, token_endpoint, fhir_base]):
            raise exceptions.UserError("Please fill in all Epic API Configuration fields before testing.")

        lines = []

        try:
            now = int(time.time())
            payload = {
                'iss': client_id, 'sub': client_id, 'aud': token_endpoint,
                'jti': str(uuid.uuid4()), 'exp': now + 300, 'nbf': now, 'iat': now,
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
            encoded_jwt = pyjwt.encode(payload, private_key, algorithm='RS384', headers=jwt_headers)
            if isinstance(encoded_jwt, bytes):
                encoded_jwt = encoded_jwt.decode('utf-8')
            lines.append("✔ JWT signed successfully.")
        except Exception as e:
            raise exceptions.UserError(f"JWT signing failed: {e}")

        try:
            resp = requests.post(
                token_endpoint,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data={
                    'grant_type': 'client_credentials',
                    'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
                    'client_assertion': encoded_jwt,
                },
                timeout=15,
            )
            if not resp.ok:
                raise exceptions.UserError(f"Token request failed ({resp.status_code}):\n{resp.text}")
            token_data = resp.json()
            access_token = token_data.get('access_token')
            granted_scope = token_data.get('scope', '(none granted)')
            lines.append(f"✔ Token obtained.")
            lines.append(f"   Scopes granted by Epic: {granted_scope}")
            if not access_token:
                raise exceptions.UserError("Token response had no access_token.")
        except exceptions.UserError:
            raise
        except Exception as e:
            raise exceptions.UserError(f"Token request error: {e}")

        try:
            meta_url = (fhir_base + '/metadata') if '/api/FHIR/' in fhir_base else (fhir_base + '/api/FHIR/R4/metadata')
            meta_resp = requests.get(meta_url, headers={'Accept': 'application/json'}, timeout=15)
            lines.append(f"✔ FHIR Base URL reachable (metadata OK)." if meta_resp.ok
                         else f"✘ FHIR metadata returned {meta_resp.status_code} — check FHIR Base URL.")
        except Exception as e:
            lines.append(f"✘ Could not reach FHIR Base URL: {e}")

        search_params = {}
        for field, param in [
            ('epic_practitioner_search_family', 'family'),
            ('epic_practitioner_search_name', 'name'),
        ]:
            val = getattr(company, field, '')
            if val:
                search_params[param] = val.strip()
                break

        if search_params:
            try:
                prac_url = (fhir_base + '/Practitioner') if '/api/FHIR/' in fhir_base else (fhir_base + '/api/FHIR/R4/Practitioner')
                prac_resp = requests.get(
                    prac_url,
                    headers={'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'},
                    params=search_params, timeout=15,
                )
                if prac_resp.ok:
                    count = len(prac_resp.json().get('entry', []))
                    lines.append(f"✔ Practitioner search succeeded! Found {count} result(s).")
                    if count == 0:
                        lines.append("   (No practitioners matched — try a different search filter.)")
                else:
                    www_auth = prac_resp.headers.get('WWW-Authenticate', '')
                    lines.append(f"✘ Practitioner search failed ({prac_resp.status_code}).")
                    if 'insufficient_scope' in www_auth:
                        lines.append("   Cause: insufficient_scope — add Practitioner.Read/Search (R4) to Epic app.")
                    else:
                        lines.append(f"   Detail: {prac_resp.text[:300]}")
            except Exception as e:
                lines.append(f"✘ Practitioner search error: {e}")
        else:
            lines.append("ℹ No practitioner search parameter configured — skipped.")

        message = '\n'.join(lines)
        _logger.info("Epic connection test:\n%s", message)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Epic Connection Test',
                'message': message,
                'sticky': True,
                'type': 'info',
            },
        }
