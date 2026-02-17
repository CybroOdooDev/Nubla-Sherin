# -*- coding: utf-8 -*-
{
    'name': 'Background PDF Report',
    'version': '18.0.1.0.0',
    'summary': 'Print button generates PDF in background via queue_job',
    'author': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base','queue_job'],

    'data': [
        'security/ir.model.access.csv',
        'data/queue_job_channel.xml',
    ],

    'installable': True,
    'license': 'LGPL-3',
}
