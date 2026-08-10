import json
import logging
import requests
from odoo import models, fields, api, exceptions

_logger = logging.getLogger(__name__)


class EpicPatient(models.Model):
    _name = 'epic.patient'
    _description = 'NHS Patient'
    _inherit = ['epic.fhir.mixin']
    _order = 'name'

    # --- Epic / Core identifiers ---
    epic_id = fields.Char(string='Epic FHIR ID', index=True)
    name = fields.Char(string='Full Name', required=True)
    mrn = fields.Char(string='MRN', help='Medical Record Number from Epic.')
    nhs_number = fields.Char(string='NHS Number', help='10-digit NHS Number.')
    ssn = fields.Char(string='SSN', help='Social Security Number (required for Epic patient creation in US deployments).')
    active = fields.Boolean(default=True)

    # --- Demographics ---
    birth_date = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ], string='Gender')
    blood_type = fields.Selection([
        ('a_pos', 'A+'), ('a_neg', 'A-'),
        ('b_pos', 'B+'), ('b_neg', 'B-'),
        ('ab_pos', 'AB+'), ('ab_neg', 'AB-'),
        ('o_pos', 'O+'), ('o_neg', 'O-'),
    ], string='Blood Type')
    ethnic_group = fields.Selection([
        ('A', 'White — British'),
        ('B', 'White — Irish'),
        ('C', 'White — Any other'),
        ('D', 'Mixed — White and Black Caribbean'),
        ('E', 'Mixed — White and Black African'),
        ('F', 'Mixed — White and Asian'),
        ('G', 'Mixed — Any other mixed'),
        ('H', 'Asian or Asian British — Indian'),
        ('J', 'Asian or Asian British — Pakistani'),
        ('K', 'Asian or Asian British — Bangladeshi'),
        ('L', 'Asian or Asian British — Any other'),
        ('M', 'Black or Black British — Caribbean'),
        ('N', 'Black or Black British — African'),
        ('P', 'Black or Black British — Any other'),
        ('R', 'Other — Chinese'),
        ('S', 'Other Ethnic Group'),
        ('Z', 'Not stated'),
    ], string='Ethnic Group (NHS 16+1)')

    # --- Contact ---
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Char(string='Address')

    # --- Next of Kin ---
    next_of_kin = fields.Char(string='Next of Kin')
    next_of_kin_phone = fields.Char(string='Next of Kin Phone')

    # --- NHS Clinical ---
    ward_id = fields.Many2one('nhs.ward', string='Current Ward', ondelete='set null')
    admission_date = fields.Date(string='Admission Date')
    discharge_date = fields.Date(string='Discharge Date')
    gp_name = fields.Char(string='GP Name')
    gp_practice = fields.Char(string='GP Practice')

    # --- Related clinical records (for stat buttons) ---
    allergy_ids = fields.One2many('epic.allergy', 'patient_id', string='Allergies')
    condition_ids = fields.One2many('epic.condition', 'patient_id', string='Conditions')
    note_ids = fields.One2many('epic.clinical.note', 'patient_id', string='Clinical Notes')

    allergy_count = fields.Integer(compute='_compute_clinical_counts', string='Allergy Count')
    condition_count = fields.Integer(compute='_compute_clinical_counts', string='Condition Count')
    note_count = fields.Integer(compute='_compute_clinical_counts', string='Note Count')

    @api.depends('allergy_ids', 'condition_ids', 'note_ids')
    def _compute_clinical_counts(self):
        for rec in self:
            rec.allergy_count = len(rec.allergy_ids)
            rec.condition_count = len(rec.condition_ids)
            rec.note_count = len(rec.note_ids)

    def action_view_allergies(self):
        return self._build_clinical_action('epic.allergy', 'Allergies', 'action_epic_allergy')

    def action_view_conditions(self):
        return self._build_clinical_action('epic.condition', 'Conditions', 'action_epic_condition')

    def action_view_notes(self):
        return self._build_clinical_action('epic.clinical.note', 'Clinical Notes', 'action_epic_clinical_note')

    def _build_clinical_action(self, model, name, action_xmlid):
        action = self.env['ir.actions.act_window']._for_xml_id(f'epic_integration.{action_xmlid}')
        action['domain'] = [('patient_id', '=', self.id)]
        action['context'] = {'default_patient_id': self.id, 'default_patient_epic_id': self.epic_id}
        action['name'] = f'{name} — {self.name}'
        return action

    def action_push_to_epic(self):
        company = self.env.company
        access_token, granted_scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        if not self._epic_has_scope('system/Patient.write', granted_scope):
            _logger.warning(
                "system/Patient.write not in granted scopes (%s) — attempting push anyway.",
                granted_scope,
            )
        url = self._epic_fhir_url(company, 'Patient')

        for patient in self:
            if patient.epic_id:
                raise exceptions.UserError(
                    f"Patient {patient.name} already has an Epic FHIR ID ({patient.epic_id})."
                )

            names = (patient.name or '').split(' ', 1)
            given = [names[0]] if names else []
            family = names[1] if len(names) > 1 else (names[0] if names else 'Unknown')

            identifiers = []
            if patient.nhs_number:
                identifiers.append({
                    'use': 'official',
                    'system': 'https://fhir.nhs.uk/Id/nhs-number',
                    'value': patient.nhs_number,
                })
            if patient.ssn:
                identifiers.append({
                    'use': 'usual',
                    'type': {'coding': [{'system': 'http://terminology.hl7.org/CodeSystem/v2-0203', 'code': 'SS'}]},
                    'system': 'urn:oid:2.16.840.1.113883.4.1',
                    'value': patient.ssn,
                })
            if not identifiers:
                raise exceptions.UserError(
                    f"Patient '{patient.name}' needs an NHS Number or SSN to be pushed to Epic."
                )

            fhir_payload = {
                'resourceType': 'Patient',
                'active': patient.active,
                'name': [{'use': 'official', 'family': family, 'given': given}],
                'identifier': identifiers,
            }

            if patient.gender and patient.gender != 'unknown':
                fhir_payload['gender'] = patient.gender
            if patient.birth_date:
                fhir_payload['birthDate'] = str(patient.birth_date)

            telecom = []
            if patient.phone:
                telecom.append({'system': 'phone', 'value': patient.phone, 'use': 'home'})
            if patient.email:
                telecom.append({'system': 'email', 'value': patient.email, 'use': 'home'})
            if telecom:
                fhir_payload['telecom'] = telecom

            if patient.address:
                fhir_payload['address'] = [{'use': 'home', 'text': patient.address}]

            response_data = self._epic_fhir_post(access_token, url, fhir_payload)
            epic_id = response_data.get('id')
            if not epic_id:
                raise exceptions.UserError(
                    "Epic created the patient but did not return a FHIR ID."
                )
            patient.epic_id = epic_id

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Patient Pushed to Epic',
                'message': 'Patient record successfully created in Epic.',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_sync_patients(self):
        company = self.env.company

        search_params = {}
        if company.epic_patient_search_family:
            search_params['family'] = company.epic_patient_search_family.strip()
        if company.epic_patient_search_given:
            search_params['given'] = company.epic_patient_search_given.strip()
        if company.epic_patient_search_identifier:
            ident = company.epic_patient_search_identifier.strip()
            search_params['_id' if len(ident) > 15 else 'identifier'] = ident
        if company.epic_patient_search_birthdate:
            search_params['birthdate'] = str(company.epic_patient_search_birthdate)
        if not search_params and company.epic_patient_search_name:
            search_params['name'] = company.epic_patient_search_name.strip()

        if not search_params:
            raise exceptions.UserError(
                "Patient sync requires at least one search parameter.\n"
                "Configure Family / Identifier / Birthdate under Settings > NHS Trust | Epic Integration."
            )

        access_token, granted_scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        if self._epic_has_scope('system/Patient.read', granted_scope):
            url = self._epic_fhir_url(company, 'Patient')
            bundle = self._epic_fhir_get(access_token, url, params=search_params)
            entries = bundle.get('entry', [])
        else:
            _logger.info("system/Patient.read not granted, trying Patient.$match fallback.")
            entries = self._try_patient_match(access_token, company, search_params)

        if entries is None:
            raise exceptions.UserError(
                "Epic did not grant 'system/Patient.read' scope and Patient.$match also failed.\n\n"
                f"Scopes granted: {granted_scope or '(none)'}\n\n"
                "In Epic App Orchard, add 'Patient.Read (R4)' and 'Patient.Search (R4)' to Incoming APIs."
            )

        return self._process_patient_entries(entries)

    def _try_patient_match(self, access_token, company, search_params):
        url = self._epic_fhir_url(company, 'Patient/$match')
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
            ],
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
            return response.json().get('entry', [])
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
                full_name = text or (
                    f"{' '.join(n.get('given', []))} {n.get('family', '')}".strip() or 'Unknown'
                )

            mrn = ssn = nhs_number = ''
            for ident in resource.get('identifier', []):
                system = ident.get('system', '')
                type_codes = [c.get('code') for c in ident.get('type', {}).get('coding', [])]
                if 'https://fhir.nhs.uk/Id/nhs-number' in system and not nhs_number:
                    nhs_number = ident.get('value', '')
                elif 'MR' in type_codes and not mrn:
                    mrn = ident.get('value', '')
                elif 'SS' in type_codes and not ssn:
                    ssn = ident.get('value', '')
                elif 'urn:oid:2.16.840.1.113883.4.1' in system and not ssn:
                    ssn = ident.get('value', '')

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
                'ssn': ssn,
                'nhs_number': nhs_number,
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
                self.with_context(sync_from_epic=True).create(vals)
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Patient Sync Complete',
                'message': f'Synced from Epic. Created: {created}, Updated: {updated}.',
                'type': 'success',
                'sticky': False,
            },
        }
