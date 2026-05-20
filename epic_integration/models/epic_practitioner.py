import logging
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)

try:
    import jwt
except ImportError:
    jwt = None
    _logger.warning("PyJWT library not found. Epic Integration will not be able to generate JWT assertions.")


class EpicPractitioner(models.Model):
    _name = 'epic.practitioner'
    _description = 'Epic Practitioner'
    _inherit = ['epic.fhir.mixin']

    name = fields.Char(string='Name', required=True)
    epic_id = fields.Char(string='Epic FHIR ID', required=True, index=True)
    npi = fields.Char(string='NPI')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ], string='Gender')
    telecom = fields.Char(string='Telecom')
    active = fields.Boolean(string='Active', default=True)

    def action_sync_practitioners(self):
        if not jwt:
            raise exceptions.UserError("The PyJWT python library is required. Please install it using 'pip install PyJWT'.")

        company = self.env.company

        search_params = {}
        if company.epic_practitioner_search_identifier:
            search_params['identifier'] = company.epic_practitioner_search_identifier.strip()
        if company.epic_practitioner_search_family:
            search_params['family'] = company.epic_practitioner_search_family.strip()
        if company.epic_practitioner_search_given:
            search_params['given'] = company.epic_practitioner_search_given.strip()
        if company.epic_practitioner_search_name:
            search_params['name'] = company.epic_practitioner_search_name.strip()

        if not search_params:
            raise exceptions.UserError(
                "Epic Practitioner sync uses the Practitioner.Search endpoint, which requires at least one search parameter.\n"
                "Configure at least one of Identifier / Family / Given / Name under Settings > Epic Integration, then retry."
            )

        access_token, _scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        url = self._epic_fhir_url(company, 'Practitioner')
        return self._fetch_and_create_practitioners(access_token, url, params=search_params)

    def _fetch_and_create_practitioners(self, access_token, url, params=None):
        bundle = self._epic_fhir_get(access_token, url, params=params)
        entries = bundle.get('entry', [])
        created_count = updated_count = 0

        for entry in entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') != 'Practitioner':
                continue

            epic_id = resource.get('id')

            names = resource.get('name', [])
            full_name = "Unknown Name"
            if names:
                first_name = names[0]
                text_name = first_name.get('text')
                if text_name:
                    full_name = text_name
                else:
                    given = " ".join(first_name.get('given', []))
                    family = first_name.get('family', '')
                    full_name = f"{given} {family}".strip()

            npi = ''
            for ident in resource.get('identifier', []):
                if ident.get('system', '').endswith('hl7.org/fhir/sid/us-npi'):
                    npi = ident.get('value', '')
                    break

            telecoms = resource.get('telecom', [])
            telecom_val = telecoms[0].get('value', '') if telecoms else ''

            gender = resource.get('gender', 'unknown')

            existing = self.search([('epic_id', '=', epic_id)], limit=1)
            vals = {
                'name': full_name,
                'npi': npi,
                'gender': gender,
                'telecom': telecom_val,
                'active': resource.get('active', True),
            }
            if existing:
                existing.write(vals)
                updated_count += 1
            else:
                vals['epic_id'] = epic_id
                self.create(vals)
                created_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Complete',
                'message': f'Synced practitioners from Epic. Created: {created_count}, Updated: {updated_count}',
                'sticky': False,
            },
        }
