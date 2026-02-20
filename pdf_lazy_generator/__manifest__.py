# -*- coding: utf-8 -*-
{
    'name': 'PDF Lazy Generator',
    'version': '18.0.1.0.0',
    'summary': 'PDF Generation Using Thread',
    'description': "PDF Generation Using Thread",
    'author': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base','account'],
    'data': [
        'views/res_config_settings_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'pdf_lazy_generator/static/src/js/report_notification.js',
        ],
    },
    'license': 'AGPL-3',
    'auto_install': False,
    'installable': True,
    'application': True,
}
