import json
import logging
import requests
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)


class EpicPatient(models.Model):
    _name = 'epic.patient'
    _description = 'Epic Patient'
    _inherit = ['epic.fhir.mixin']

    epic_id = fields.Char(string='Epic FHIR ID', required=True, index=True)
    name = fields.Char(string='Name', required=True)
    birth_date = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ], string='Gender')
    mrn = fields.Char(string='MRN')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Char(string='Address')
    active = fields.Boolean(default=True)

    def action_sync_patients(self):
        company = self.env.company

        search_params = {}
        if company.epic_patient_search_family:
            search_params['family'] = company.epic_patient_search_family.strip()
        if company.epic_patient_search_given:
            search_params['given'] = company.epic_patient_search_given.strip()
        if company.epic_patient_search_identifier:
            search_params['identifier'] = company.epic_patient_search_identifier.strip()
        if company.epic_patient_search_birthdate:
            search_params['birthdate'] = str(company.epic_patient_search_birthdate)
        # Use name only if no other param set (avoid duplicate with family)
        if not search_params and company.epic_patient_search_name:
            search_params['name'] = company.epic_patient_search_name.strip()

        if not search_params:
            raise exceptions.UserError(
                "Patient sync requires at least one search parameter.\n"
                "Configure Family / Identifier / Birthdate under Settings > Epic Integration."
            )

        access_token, granted_scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        # Try standard Patient search first
        if 'system/Patient.read' in (granted_scope or ''):
            url = self._epic_fhir_url(company, 'Patient')
            bundle = self._epic_fhir_get(access_token, url, params=search_params)
            entries = bundle.get('entry', [])
        else:
            # Fallback: try Patient.$match (POST) — uses Demographics scope
            _logger.info("system/Patient.read not granted, trying Patient.$match fallback.")
            entries = self._try_patient_match(access_token, company, search_params)

        if entries is None:
            raise exceptions.UserError(
                "Epic did not grant 'system/Patient.read' scope and Patient.$match also failed.\n\n"
                f"Scopes granted: {granted_scope or '(none)'}\n\n"
                "In Epic App Orchard, add 'Patient.Read (R4)' and 'Patient.Search (R4)' "
                "(plain R4 — no qualifiers) to your app's Incoming APIs."
            )

        return self._process_patient_entries(entries)

    def _try_patient_match(self, access_token, company, search_params):
        """Try Patient.$match (POST) as fallback when system/Patient.read scope is not granted."""
        url = self._epic_fhir_url(company, 'Patient/$match')

        # Build patient resource from search params
        patient_resource = {'resourceType': 'Patient'}
        name_obj = {}
        if search_params.get('family'):
            name_obj['family'] = search_params['family']
        if search_params.get('given'):
            name_obj['given'] = [search_params['given']]
        if name_obj:
            patient_resource['name'] = [name_obj]
        if search_params.get('birthdate'):
            patient_resource['birthDate'] = search_params['birthdate']
        if search_params.get('identifier'):
            patient_resource['identifier'] = [{'value': search_params['identifier']}]

        body = {
            'resourceType': 'Parameters',
            'parameter': [
                {'name': 'resource', 'resource': patient_resource},
                {'name': 'onlyCertainMatches', 'valueBoolean': False},
                {'name': 'count', 'valueInteger': 50},
            ]
        }

        try:
            response = requests.post(
                url,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                data=json.dumps(body),
                timeout=30,
            )
            if response.status_code >= 400:
                _logger.warning("Patient.$match failed %s: %s", response.status_code, response.text)
                return None
            bundle = response.json()
            return bundle.get('entry', [])
        except Exception as e:
            _logger.error("Patient.$match error: %s", e)
            return None

    def _process_patient_entries(self, entries):
        created = updated = 0

        for entry in entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') != 'Patient':
                continue

            epic_id = resource.get('id')
            if not epic_id:
                continue

            names = resource.get('name', [])
            full_name = 'Unknown'
            if names:
                n = names[0]
                text = n.get('text', '')
                if text:
                    full_name = text
                else:
                    given = ' '.join(n.get('given', []))
                    family = n.get('family', '')
                    full_name = f"{given} {family}".strip() or 'Unknown'

            mrn = ''
            for ident in resource.get('identifier', []):
                type_codings = ident.get('type', {}).get('coding', [])
                if any(c.get('code') == 'MR' for c in type_codings):
                    mrn = ident.get('value', '')
                    break

            phone = email = ''
            for t in resource.get('telecom', []):
                if t.get('system') == 'phone' and not phone:
                    phone = t.get('value', '')
                elif t.get('system') == 'email' and not email:
                    email = t.get('value', '')

            address = ''
            addrs = resource.get('address', [])
            if addrs:
                a = addrs[0]
                parts = a.get('line', []) + [a.get('city', ''), a.get('state', ''), a.get('postalCode', '')]
                address = ', '.join(p for p in parts if p)

            vals = {
                'name': full_name,
                'birth_date': resource.get('birthDate') or False,
                'gender': resource.get('gender', 'unknown'),
                'mrn': mrn,
                'phone': phone,
                'email': email,
                'address': address,
                'active': resource.get('active', True),
            }

            existing = self.search([('epic_id', '=', epic_id)], limit=1)
            if existing:
                existing.write(vals)
                updated += 1
            else:
                vals['epic_id'] = epic_id
                self.create(vals)
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Patient Sync Complete',
                'message': f'Synced patients from Epic. Created: {created}, Updated: {updated}',
                'sticky': False,
            },
        }
