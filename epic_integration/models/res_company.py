from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    # --- NHS Trust Identity ---
    nhs_ods_code = fields.Char(string='ODS Organisation Code', help='NHS Organisation Data Service code (e.g. RJ1, RQM).')
    nhs_cqc_number = fields.Char(string='CQC Registration Number', help='Care Quality Commission registration number.')
    nhs_trust_type = fields.Selection([
        ('acute', 'Acute Trust'),
        ('mental_health', 'Mental Health Trust'),
        ('community', 'Community Trust'),
        ('ambulance', 'Ambulance Trust'),
        ('foundation', 'NHS Foundation Trust'),
        ('specialist', 'Specialist Trust'),
        ('integrated', 'Integrated Care Board'),
    ], string='Trust Type')
    nhs_trust_region = fields.Char(string='NHS England Region', help='e.g. London, South East, North West.')

    # --- Epic API Connection ---
    epic_client_id = fields.Char(string='Epic Client ID')
    epic_non_production_client_id = fields.Char(string='Epic Non-Production Client ID')
    epic_environment = fields.Selection([
        ('sandbox', 'Sandbox (Testing)'),
        ('production', 'Production'),
    ], string='Epic Environment', default='sandbox')
    epic_private_key = fields.Text(string='Epic Private Key')
    epic_jwks = fields.Text(string='Epic JWKS (Public Key)')
    epic_token_endpoint = fields.Char(string='Epic Token Endpoint')
    epic_fhir_base_url = fields.Char(string='Epic FHIR Base URL')

    # --- Practitioner Search ---
    epic_practitioner_search_identifier = fields.Char(string='Practitioner Search Identifier')
    epic_practitioner_search_family = fields.Char(string='Practitioner Search Family')
    epic_practitioner_search_given = fields.Char(string='Practitioner Search Given')
    epic_practitioner_search_name = fields.Char(string='Practitioner Search Name')

    # --- Appointment Search ---
    epic_appointment_search_date = fields.Date(string='Appointment Search Date From')
    epic_appointment_search_status = fields.Char(string='Appointment Search Status')
    epic_appointment_search_patient = fields.Char(string='Appointment Search Patient ID')

    # --- Allergy Search ---
    epic_allergy_search_patient = fields.Char(string='Allergy Search Patient Epic ID')

    # --- Clinical Notes Search ---
    epic_clinical_note_search_patient = fields.Char(string='Clinical Note Search Patient Epic ID')
    epic_clinical_note_search_type = fields.Char(string='Clinical Note Type Filter')

    # --- Condition Search ---
    epic_condition_search_patient = fields.Char(string='Condition Search Patient Epic ID')
    epic_condition_search_category = fields.Selection([
        ('problem-list-item', 'Problem List'),
        ('encounter-diagnosis', 'Encounter Diagnosis'),
        ('health-concern', 'Health Concern'),
    ], string='Condition Category Filter')

    # --- Patient Search ---
    epic_patient_search_name = fields.Char(string='Patient Search Name')
    epic_patient_search_family = fields.Char(string='Patient Search Family')
    epic_patient_search_given = fields.Char(string='Patient Search Given')
    epic_patient_search_identifier = fields.Char(string='Patient Search Identifier (MRN)')
    epic_patient_search_birthdate = fields.Date(string='Patient Search Birthdate')
