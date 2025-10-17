{
    'name': 'Hospital Management System',
    'version': '18.0.1.0.0',
    'category': 'Healthcare',
    'summary': 'Complete Hospital Management System with Patient, Doctor, Appointment, Billing, Pharmacy, Lab',
    'description': """
        Hospital Management System
        ==========================
        * Patient Registration and Management
        * Appointment Scheduling
        * Doctor and Staff Management
        * Medical Records (EMR/EHR)
        * Pharmacy Management
        * Laboratory Management
        * Billing and Invoicing
        * Ward and Bed Management
        * Surgery/OT Management
        * Patient Portal
        * Automated Workflows
        * Reports and Analytics
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'calendar',
        'account',
        'stock',
        'web',
        'portal',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence.xml',
        'data/data.xml',
        'data/email_templates.xml',
        'data/cron_jobs.xml',

        # Wizards
        'wizards/appointment_wizard_views.xml',
        'wizards/discharge_wizard_views.xml',
        'wizards/billing_wizard_views.xml',
        'wizards/bed_transfer_wizard_views.xml',

        # Views
        'views/hospital_menu.xml',
        'views/hospital_patient_views.xml',
        'views/hospital_appointment_views.xml',
        'views/hospital_doctor_views.xml',
        'views/hospital_department_views.xml',
        'views/hospital_consultation_views.xml',
        'views/hospital_prescription_views.xml',
        'views/hospital_medicine_views.xml',
        'views/hospital_lab_views.xml',
        'views/hospital_ward_views.xml',
        'views/hospital_insurance_views.xml',
        'views/hospital_surgery_views.xml',
        'views/hospital_billing_views.xml',

        # Portal
        'views/portal_templates.xml',

        # Reports
        'views/report.xml',
        'views/patient_report.xml',
        'views/prescription_report.xml',
        'views/invoice_report.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            'hospital_management/static/src/css/hospital_dashboard.css',
            'hospital_management/static/src/js/hospital_dashboard.js',
            'hospital_management/static/src/xml/hospital_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
