{
    'name': 'Epic Integration',
    'version': '19.0.2.0.0',
    'category': 'Integration',
    'summary': 'Fetch Practitioners, Appointments, and Patients from Epic FHIR API',
    'description': """
        Integrates Odoo with Epic's FHIR API using Backend Systems Authentication (OAuth2 Client Credentials with JWT).
        Supports syncing Practitioners, Appointments, and Patients from Epic's FHIR R4 endpoints.
    """,
    'author': 'Cybrosys',
    'depends': ['base', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/epic_appointment_views.xml',
        'views/epic_patient_views.xml',
        'views/epic_practitioner_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
