import logging
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)

try:
    import jwt
except ImportError:
    jwt = None
    _logger.warning("PyJWT library not found. Epic Integration requires PyJWT for JWT assertions.")


class EpicPractitioner(models.Model):
    _name = 'epic.practitioner'
    _description = 'NHS Clinical Staff'
    _inherit = ['epic.fhir.mixin']
    _order = 'name'

    # --- Core ---
    name = fields.Char(string='Full Name', required=True)
    epic_id = fields.Char(string='Epic FHIR ID', required=True, index=True)
    active = fields.Boolean(default=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ], string='Gender')

    # --- NHS Professional Identifiers ---
    npi = fields.Char(string='NPI', help='US National Provider Identifier (from Epic).')
    gmc_number = fields.Char(string='GMC Number', help='General Medical Council registration number.')
    nmc_pin = fields.Char(string='NMC Pin', help='Nursing & Midwifery Council registration pin.')

    # --- NHS Role & Department ---
    role = fields.Selection([
        ('consultant', 'Consultant'),
        ('registrar', 'Registrar'),
        ('junior_doctor', 'Junior Doctor / FY'),
        ('gp', 'GP'),
        ('nurse_consultant', 'Nurse Consultant'),
        ('nurse', 'Nurse'),
        ('specialist_nurse', 'Specialist Nurse'),
        ('midwife', 'Midwife'),
        ('pharmacist', 'Pharmacist'),
        ('physiotherapist', 'Physiotherapist'),
        ('occupational_therapist', 'Occupational Therapist'),
        ('radiographer', 'Radiographer'),
        ('other', 'Other'),
    ], string='Role')
    specialty = fields.Char(string='Specialty')
    department = fields.Char(string='Department')
    telecom = fields.Char(string='Contact')

    def action_sync_practitioners(self):
        if not jwt:
            raise exceptions.UserError(
                "The PyJWT python library is required. Install it with: pip install PyJWT"
            )

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
                "Practitioner sync requires at least one search parameter.\n"
                "Configure Identifier / Family / Given / Name under Settings > NHS Trust | Epic Integration."
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
            full_name = 'Unknown'
            if names:
                n = names[0]
                text = n.get('text', '')
                full_name = text or (
                    f"{' '.join(n.get('given', []))} {n.get('family', '')}".strip() or 'Unknown'
                )

            npi = gmc_number = nmc_pin = ''
            for ident in resource.get('identifier', []):
                system = ident.get('system', '')
                if 'hl7.org/fhir/sid/us-npi' in system and not npi:
                    npi = ident.get('value', '')
                elif 'gmc-number' in system.lower() and not gmc_number:
                    gmc_number = ident.get('value', '')
                elif 'nmc' in system.lower() and not nmc_pin:
                    nmc_pin = ident.get('value', '')

            telecoms = resource.get('telecom', [])
            telecom_val = telecoms[0].get('value', '') if telecoms else ''

            vals = {
                'name': full_name,
                'npi': npi,
                'gmc_number': gmc_number,
                'nmc_pin': nmc_pin,
                'gender': resource.get('gender', 'unknown'),
                'telecom': telecom_val,
                'active': resource.get('active', True),
            }
            existing = self.search([('epic_id', '=', epic_id)], limit=1)
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
                'title': 'Staff Sync Complete',
                'message': f'Synced clinical staff from Epic. Created: {created_count}, Updated: {updated_count}.',
                'type': 'success',
                'sticky': False,
            },
        }
