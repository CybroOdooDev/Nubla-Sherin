# -*- coding: utf-8 -*-
{
    'name': 'NHS Patient Simple',
    'version': '19.0.1.0.0',
    'category': 'Healthcare',
    'summary': 'Simple Patient management with one-click NHS lookup',
    'description': """
NHS Patient Simple
==================
A minimal Odoo module that demonstrates NHS API integration:

* Single Patient model with name, NHS Number, DOB, gender, address, phone
* "Fetch from NHS" button on the patient form
* Click the button → calls NHS PDS Sandbox → fills in the demographics
* Configurable API key and environment in Settings
* Audit log of every NHS call

Sandbox test NHS Numbers: 9000000009, 9000000017, 9000000025, 9000000033
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'views/res_config_settings_views.xml',
        'views/nhs_simple_patient_views.xml',
        'views/nhs_simple_log_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
