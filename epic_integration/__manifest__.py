{
    'name': 'NHS Trust | Epic Integration',
    'version': '19.0.1.0.0',
    'category': 'Healthcare',
    'summary': 'NHS Trust management with Epic EHR — sync patients, clinical notes, appointments, allergies and conditions via FHIR R4',
    'description': """
NHS Trust | Epic Integration
============================

A complete Odoo module for NHS Trusts integrating with the Epic Electronic Health Record (EHR)
system using the FHIR R4 API and Epic SMART Backend Services authentication.

Features:
---------
* Ward & Department management with bed capacity tracking
* NHS Patient records — NHS Number, ward assignment, GP details, blood type, next of kin, NHS ethnic group (16+1)
* Appointment synchronisation with status management
* Clinical Notes — sync DocumentReference notes including full HTML/text content from Epic Binary
* Allergy & Intolerance records — bidirectional sync (pull from Epic, push to Epic)
* Medical Conditions / Diagnoses — bidirectional sync with ICD-10/SNOMED coding
* Clinical Staff (Practitioners) — GMC number, NMC Pin, specialty, role
* Role-based security: Trust Administrator, Clinician, Receptionist
* Secure FHIR authentication via OAuth2 Client Credentials + RS384 JWT Bearer
* JWKS public key served automatically at /epic/jwks.json
* NHS Trust configuration — ODS Organisation Code, CQC Registration Number

Authentication:
---------------
Uses Epic SMART on FHIR Backend Services (system-level scopes).
Supports both Open Epic sandbox (non-production) and production environments.

Requirements:
-------------
* Python: PyJWT >= 2.0 (`pip install PyJWT`)
* Epic App Orchard app with Backend Systems audience
    """,
    'author': 'Cybrosys Technologies',
    'website': 'https://www.cybrosys.com',
    'support': 'support@cybrosys.com',
    'depends': ['base', 'base_setup'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/nhs_ward_views.xml',
        'views/epic_appointment_views.xml',
        'views/epic_patient_views.xml',
        'views/epic_practitioner_views.xml',
        'views/epic_allergy_views.xml',
        'views/epic_allergy_dashboard_views.xml',
        'views/epic_condition_views.xml',
        'views/epic_clinical_note_views.xml',
        'views/epic_dashboard_views.xml',
        'views/epic_appointment_menu_restore.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'epic_integration/static/src/components/epic_dashboard/epic_dashboard.scss',
            'epic_integration/static/src/components/epic_dashboard/epic_dashboard.xml',
            'epic_integration/static/src/components/epic_dashboard/epic_dashboard.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
