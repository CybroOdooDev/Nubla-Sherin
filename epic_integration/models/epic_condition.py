import logging
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)


class EpicCondition(models.Model):
    _name = 'epic.condition'
    _description = 'Epic Condition'
    _inherit = ['epic.fhir.mixin']
    _order = 'recorded_date desc, id desc'

    epic_id = fields.Char(string='Epic FHIR ID', index=True)
    patient_id = fields.Many2one('epic.patient', string='Patient', ondelete='cascade')
    patient_epic_id = fields.Char(string='Patient Epic ID')

    clinical_status = fields.Selection([
        ('active', 'Active'),
        ('recurrence', 'Recurrence'),
        ('relapse', 'Relapse'),
        ('inactive', 'Inactive'),
        ('remission', 'Remission'),
        ('resolved', 'Resolved'),
    ], string='Clinical Status', default='active')

    verification_status = fields.Selection([
        ('unconfirmed', 'Unconfirmed'),
        ('provisional', 'Provisional'),
        ('differential', 'Differential'),
        ('confirmed', 'Confirmed'),
        ('refuted', 'Refuted'),
        ('entered-in-error', 'Entered in Error'),
    ], string='Verification Status', default='confirmed')

    category = fields.Selection([
        ('problem-list-item', 'Problem List Item'),
        ('encounter-diagnosis', 'Encounter Diagnosis'),
        ('health-concern', 'Health Concern'),
    ], string='Category', default='problem-list-item')

    severity = fields.Selection([
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], string='Severity')

    condition_name = fields.Char(string='Condition / Diagnosis', required=True)
    condition_code = fields.Char(string='Condition Code')
    condition_system = fields.Char(string='Code System')

    onset_date = fields.Date(string='Onset Date')
    abatement_date = fields.Date(string='Abatement Date')
    recorded_date = fields.Date(string='Recorded Date')

    note = fields.Text(string='Notes')

    def action_sync_conditions(self):
        company = self.env.company

        # Build patient list: specific ID from settings OR all Odoo patients with Epic IDs
        specific_id = (company.epic_condition_search_patient or '').strip()
        if specific_id:
            patient_ids = [specific_id]
        else:
            patient_ids = self.env['epic.patient'].search(
                [('epic_id', '!=', False)]
            ).mapped('epic_id')
            if not patient_ids:
                raise exceptions.UserError(
                    "No patients with Epic FHIR IDs found in Odoo.\n"
                    "Sync patients first, or set a specific Patient Epic ID under "
                    "Settings > Epic Integration > Condition Sync Defaults."
                )

        access_token, granted_scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        if not self._epic_has_scope('system/Condition.read', granted_scope):
            _logger.warning(
                "system/Condition.read not in granted scopes (%s) — attempting anyway.", granted_scope
            )

        url = self._epic_fhir_url(company, 'Condition')
        created = updated = skipped = 0

        valid_clinical = ('active', 'recurrence', 'relapse', 'inactive', 'remission', 'resolved')
        valid_verification = ('unconfirmed', 'provisional', 'differential', 'confirmed', 'refuted', 'entered-in-error')
        valid_category = ('problem-list-item', 'encounter-diagnosis', 'health-concern')

        errors = []
        for patient_epic_id in patient_ids:
            search_params = {'patient': patient_epic_id}
            if company.epic_condition_search_category:
                search_params['category'] = company.epic_condition_search_category
            try:
                bundle = self._epic_fhir_get(access_token, url, params=search_params)
            except Exception as e:
                _logger.warning("Failed to fetch conditions for patient %s: %s", patient_epic_id, e)
                errors.append(str(e))
                skipped += 1
                continue

            for entry in bundle.get('entry', []):
                resource = entry.get('resource', {})
                if resource.get('resourceType') != 'Condition':
                    continue

                epic_id = resource.get('id')
                if not epic_id:
                    continue

                condition_name, condition_code, condition_system = self._parse_code(resource)
                clinical_status = (
                    resource.get('clinicalStatus', {})
                    .get('coding', [{}])[0].get('code', 'active')
                )
                verification_status = (
                    resource.get('verificationStatus', {})
                    .get('coding', [{}])[0].get('code', 'confirmed')
                )
                categories = resource.get('category', [])
                category_code = False
                if categories:
                    codings = categories[0].get('coding', [])
                    category_code = codings[0].get('code', False) if codings else False

                severity_codings = resource.get('severity', {}).get('coding', [])
                severity_display = severity_codings[0].get('display', '').lower() if severity_codings else ''
                severity = severity_display if severity_display in ('mild', 'moderate', 'severe') else False

                patient_ref = resource.get('subject', {}).get('reference', '')
                pat_epic_id = patient_ref.split('/')[-1] if '/' in patient_ref else patient_ref
                patient_rec = self.env['epic.patient'].search([('epic_id', '=', pat_epic_id)], limit=1)

                vals = {
                    'clinical_status': clinical_status if clinical_status in valid_clinical else 'active',
                    'verification_status': verification_status if verification_status in valid_verification else 'confirmed',
                    'category': category_code if category_code in valid_category else False,
                    'severity': severity,
                    'condition_name': condition_name,
                    'condition_code': condition_code,
                    'condition_system': condition_system,
                    'onset_date': (resource.get('onsetDateTime') or resource.get('onsetString') or '')[:10] or False,
                    'abatement_date': (resource.get('abatementDateTime') or '')[:10] or False,
                    'recorded_date': (resource.get('recordedDate') or '')[:10] or False,
                    'note': ' | '.join(n.get('text', '') for n in resource.get('note', [])) or False,
                    'patient_epic_id': pat_epic_id,
                    'patient_id': patient_rec.id if patient_rec else False,
                }

                existing = self.search([('epic_id', '=', epic_id)], limit=1)
                if existing:
                    existing.write(vals)
                    updated += 1
                else:
                    vals['epic_id'] = epic_id
                    self.create(vals)
                    created += 1

        if skipped and skipped == len(patient_ids):
            first_error = errors[0] if errors else 'Unknown error'
            raise exceptions.UserError(
                f"Condition sync failed for all {skipped} patient(s).\n\n"
                f"First error:\n{first_error}\n\n"
                "Most likely fix in Epic App Orchard:\n"
                "  Add 'Condition.Search (Problems) (R4)' and\n"
                "  'Condition.Search (Encounter Diagnosis) (R4)' to Incoming APIs.\n"
                "  (Read APIs alone are not enough — Search APIs are required.)"
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Condition Sync Complete',
                'message': f'Synced conditions from Epic across {len(patient_ids)} patient(s). Created: {created}, Updated: {updated}' + (f', Skipped: {skipped}' if skipped else '') + '.',
                'type': 'success' if not skipped else 'warning',
                'sticky': False,
            },
        }

    def action_push_to_epic(self):
        company = self.env.company
        access_token, granted_scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        if not self._epic_has_scope('system/Condition.write', granted_scope):
            _logger.warning(
                "system/Condition.write not in granted scopes (%s) — attempting push anyway.", granted_scope
            )

        url = self._epic_fhir_url(company, 'Condition')

        for condition in self:
            if condition.epic_id:
                raise exceptions.UserError(
                    f"Condition '{condition.condition_name}' already has an Epic FHIR ID ({condition.epic_id})."
                )

            patient_ref = condition.patient_epic_id or (condition.patient_id.epic_id if condition.patient_id else '')
            if not patient_ref:
                raise exceptions.UserError(
                    f"Condition '{condition.condition_name}' has no linked patient. "
                    "Set the Patient field or Patient Epic ID before pushing."
                )

            if not condition.condition_code or not condition.condition_system:
                raise exceptions.UserError(
                    f"Condition '{condition.condition_name}' is missing a Condition Code or Code System.\n\n"
                    "Epic requires a coded condition. Please fill in both fields:\n"
                    "  • Condition Code: the SNOMED CT or ICD-10 code\n"
                    "  • Code System: the code system URI\n\n"
                    "Common examples:\n"
                    "  Hypertension → Code: 38341003   System: http://snomed.info/sct\n"
                    "  Diabetes T2  → Code: 44054006   System: http://snomed.info/sct\n"
                    "  Asthma       → Code: 195967001  System: http://snomed.info/sct\n"
                    "  Fever        → Code: 386661006  System: http://snomed.info/sct"
                )

            fhir_payload = {
                "resourceType": "Condition",
                "clinicalStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": condition.clinical_status or "active",
                    }]
                },
                "verificationStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": condition.verification_status or "confirmed",
                    }]
                },
                "subject": {"reference": f"Patient/{patient_ref}"},
                "code": self._build_condition_coding(condition),
            }

            if condition.category:
                fhir_payload['category'] = [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                        "code": condition.category,
                    }]
                }]

            if condition.severity:
                severity_codes = {
                    'mild': ('255604002', 'Mild'),
                    'moderate': ('6736007', 'Moderate'),
                    'severe': ('24484000', 'Severe'),
                }
                code, display = severity_codes.get(condition.severity, ('255604002', 'Mild'))
                fhir_payload['severity'] = {
                    "coding": [{"system": "http://snomed.info/sct", "code": code, "display": display}]
                }

            if condition.onset_date:
                fhir_payload['onsetDateTime'] = str(condition.onset_date)
            if condition.abatement_date:
                fhir_payload['abatementDateTime'] = str(condition.abatement_date)
            if condition.recorded_date:
                fhir_payload['recordedDate'] = str(condition.recorded_date)
            if condition.note:
                fhir_payload['note'] = [{"text": condition.note}]

            response_data = self._epic_fhir_post(access_token, url, fhir_payload)
            epic_id = response_data.get('id')
            if not epic_id:
                raise exceptions.UserError(
                    "Epic created the condition but did not return a FHIR ID."
                )
            condition.epic_id = epic_id

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Condition successfully pushed to Epic.',
                'type': 'success',
                'sticky': False,
            },
        }

    def _parse_code(self, resource):
        code_obj = resource.get('code', {})
        codings = code_obj.get('coding', [])
        text = code_obj.get('text', '')
        if codings:
            display = codings[0].get('display', '') or text or 'Unknown'
            return display, codings[0].get('code', ''), codings[0].get('system', '')
        return text or 'Unknown', '', ''

    def _build_condition_coding(self, condition):
        return {
            "coding": [{
                "system": condition.condition_system,
                "code": condition.condition_code,
                "display": condition.condition_name,
            }],
            "text": condition.condition_name,
        }
