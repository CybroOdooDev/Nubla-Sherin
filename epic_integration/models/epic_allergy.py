import logging
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)


class EpicAllergy(models.Model):
    _name = 'epic.allergy'
    _description = 'Epic AllergyIntolerance'
    _inherit = ['epic.fhir.mixin']
    _order = 'recorded_date desc, id desc'

    epic_id = fields.Char(string='Epic FHIR ID', index=True)
    patient_id = fields.Many2one('epic.patient', string='Patient', ondelete='cascade')
    patient_epic_id = fields.Char(string='Patient Epic ID')

    clinical_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('resolved', 'Resolved'),
    ], string='Clinical Status', default='active')

    verification_status = fields.Selection([
        ('unconfirmed', 'Unconfirmed'),
        ('presumed', 'Presumed'),
        ('confirmed', 'Confirmed'),
        ('refuted', 'Refuted'),
        ('entered-in-error', 'Entered in Error'),
    ], string='Verification Status', default='unconfirmed')

    allergy_type = fields.Selection([
        ('allergy', 'Allergy'),
        ('intolerance', 'Intolerance'),
    ], string='Type', default='allergy')

    category = fields.Selection([
        ('food', 'Food'),
        ('medication', 'Medication'),
        ('environment', 'Environment'),
        ('biologic', 'Biologic'),
    ], string='Category')

    criticality = fields.Selection([
        ('low', 'Low'),
        ('high', 'High'),
        ('unable-to-assess', 'Unable to Assess'),
    ], string='Criticality')

    substance = fields.Char(string='Substance / Allergen', required=True)
    substance_code = fields.Char(string='Substance Code')
    substance_system = fields.Char(string='Substance Code System')

    onset_date = fields.Date(string='Onset Date')
    recorded_date = fields.Date(string='Recorded Date')

    reaction = fields.Char(string='Reaction / Manifestation')
    reaction_severity = fields.Selection([
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], string='Reaction Severity')

    note = fields.Text(string='Notes')

    def action_sync_allergies(self):
        company = self.env.company

        # Build patient list: specific ID from settings OR all Odoo patients with Epic IDs
        specific_id = (company.epic_allergy_search_patient or '').strip()
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
                    "Settings > Epic Integration > Allergy Sync Defaults."
                )

        access_token, granted_scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        if not self._epic_has_scope('system/AllergyIntolerance.read', granted_scope):
            _logger.warning(
                "system/AllergyIntolerance.read not in granted scopes (%s) — attempting anyway.", granted_scope
            )

        url = self._epic_fhir_url(company, 'AllergyIntolerance')
        created = updated = skipped = 0

        for patient_epic_id in patient_ids:
            try:
                bundle = self._epic_fhir_get(access_token, url, params={'patient': patient_epic_id})
            except Exception as e:
                _logger.warning("Failed to fetch allergies for patient %s: %s", patient_epic_id, e)
                skipped += 1
                continue

            for entry in bundle.get('entry', []):
                resource = entry.get('resource', {})
                if resource.get('resourceType') != 'AllergyIntolerance':
                    continue

                epic_id = resource.get('id')
                if not epic_id:
                    continue

                substance, substance_code, substance_system = self._parse_substance(resource)
                clinical_status = (
                    resource.get('clinicalStatus', {})
                    .get('coding', [{}])[0].get('code', 'active')
                )
                verification_status = (
                    resource.get('verificationStatus', {})
                    .get('coding', [{}])[0].get('code', 'confirmed')
                )
                category_list = resource.get('category', [])
                category = category_list[0] if category_list else False
                reaction_text, reaction_severity = self._parse_reaction(resource)

                patient_ref = resource.get('patient', {}).get('reference', '')
                pat_epic_id = patient_ref.split('/')[-1] if '/' in patient_ref else patient_ref
                patient_rec = self.env['epic.patient'].search([('epic_id', '=', pat_epic_id)], limit=1)

                vals = {
                    'clinical_status': clinical_status if clinical_status in ('active', 'inactive', 'resolved') else 'active',
                    'verification_status': verification_status if verification_status in (
                        'unconfirmed', 'presumed', 'confirmed', 'refuted', 'entered-in-error') else 'confirmed',
                    'allergy_type': resource.get('type', 'allergy'),
                    'category': category if category in ('food', 'medication', 'environment', 'biologic') else False,
                    'criticality': resource.get('criticality') or False,
                    'substance': substance,
                    'substance_code': substance_code,
                    'substance_system': substance_system,
                    'onset_date': (resource.get('onsetDateTime') or '')[:10] or False,
                    'recorded_date': (resource.get('recordedDate') or '')[:10] or False,
                    'reaction': reaction_text,
                    'reaction_severity': reaction_severity,
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

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Allergy Sync Complete',
                'message': f'Synced allergies from Epic across {len(patient_ids)} patient(s). Created: {created}, Updated: {updated}' + (f', Skipped: {skipped}' if skipped else '') + '.',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_push_to_epic(self):
        company = self.env.company
        access_token, granted_scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        if not self._epic_has_scope('system/AllergyIntolerance.write', granted_scope):
            _logger.warning(
                "system/AllergyIntolerance.write not in granted scopes (%s) — attempting push anyway.", granted_scope
            )

        url = self._epic_fhir_url(company, 'AllergyIntolerance')

        for allergy in self:
            if allergy.epic_id:
                raise exceptions.UserError(
                    f"Allergy '{allergy.substance}' already has an Epic FHIR ID ({allergy.epic_id})."
                )

            patient_ref = allergy.patient_epic_id or (allergy.patient_id.epic_id if allergy.patient_id else '')
            if not patient_ref:
                raise exceptions.UserError(
                    f"Allergy '{allergy.substance}' has no linked patient. "
                    "Set the Patient field or Patient Epic ID before pushing."
                )

            if not allergy.substance_code or not allergy.substance_system:
                raise exceptions.UserError(
                    f"Allergy '{allergy.substance}' is missing a Substance Code or Substance Code System.\n\n"
                    "Epic requires a coded substance. Please fill in both fields:\n"
                    "  • Substance Code: the SNOMED CT or RxNorm code\n"
                    "  • Substance Code System: the code system URI\n\n"
                    "Common examples:\n"
                    "  Penicillin  → Code: 372687004  System: http://snomed.info/sct\n"
                    "  Aspirin     → Code: 387458008   System: http://snomed.info/sct\n"
                    "  Amoxicillin → Code: 372687004   System: http://snomed.info/sct\n"
                    "  Latex       → Code: 1003752004  System: http://snomed.info/sct"
                )

            fhir_payload = {
                "resourceType": "AllergyIntolerance",
                "clinicalStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                        "code": allergy.clinical_status or "active",
                    }]
                },
                "verificationStatus": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                        "code": allergy.verification_status or "unconfirmed",
                    }]
                },
                "patient": {"reference": f"Patient/{patient_ref}"},
                "code": self._build_substance_coding(allergy),
            }

            if allergy.allergy_type:
                fhir_payload['type'] = allergy.allergy_type
            if allergy.category:
                fhir_payload['category'] = [allergy.category]
            if allergy.criticality:
                fhir_payload['criticality'] = allergy.criticality
            if allergy.onset_date:
                fhir_payload['onsetDateTime'] = str(allergy.onset_date)
            if allergy.recorded_date:
                fhir_payload['recordedDate'] = str(allergy.recorded_date)
            if allergy.reaction:
                reaction_entry = {
                    "manifestation": [{"coding": [{"display": allergy.reaction}]}]
                }
                if allergy.reaction_severity:
                    reaction_entry['severity'] = allergy.reaction_severity
                fhir_payload['reaction'] = [reaction_entry]
            if allergy.note:
                fhir_payload['note'] = [{"text": allergy.note}]

            response_data = self._epic_fhir_post(access_token, url, fhir_payload)
            epic_id = response_data.get('id')
            if not epic_id:
                raise exceptions.UserError(
                    "Epic created the allergy but did not return a FHIR ID."
                )
            allergy.epic_id = epic_id

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Allergy/Intolerance successfully pushed to Epic.',
                'type': 'success',
                'sticky': False,
            },
        }

    def _parse_substance(self, resource):
        code_obj = resource.get('code', {})
        codings = code_obj.get('coding', [])
        text = code_obj.get('text', '')
        if codings:
            display = codings[0].get('display', '') or text or 'Unknown'
            return display, codings[0].get('code', ''), codings[0].get('system', '')
        return text or 'Unknown', '', ''

    def _parse_reaction(self, resource):
        reactions = resource.get('reaction', [])
        if not reactions:
            return False, False
        first = reactions[0]
        manifestations = first.get('manifestation', [])
        texts = []
        for m in manifestations:
            codings = m.get('coding', [])
            t = m.get('text', '')
            texts.append(codings[0].get('display', t) if codings else t)
        severity = first.get('severity') or False
        if severity not in ('mild', 'moderate', 'severe'):
            severity = False
        return ', '.join(filter(None, texts)) or False, severity

    def _build_substance_coding(self, allergy):
        if allergy.substance_code and allergy.substance_system:
            return {
                "coding": [{
                    "system": allergy.substance_system,
                    "code": allergy.substance_code,
                    "display": allergy.substance,
                }],
                "text": allergy.substance,
            }
        return {"text": allergy.substance}
