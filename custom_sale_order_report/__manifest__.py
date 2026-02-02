# -*- coding: utf-8 -*-
################################################################################
#
#    Cats and Dogs Solution
#
#    Copyright (C) Cats and Dogs Solution.
#
#    This program is under the terms of the Odoo Proprietary License v1.0
#    (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
################################################################################
{
    'name': "SaleOrder Report",
    'version': '18.0.1.0.0',
    'depends': ['sale'],
    'summary': 'Custom SaleOrder report',
    'author': 'Cats and Dogs Solutions',
    'company': 'Cats and Dogs Solutions',
    'maintainer': 'Cats and Dogs Solutions',
    'data': [
        'views/sale_report.xml',
    ],
'assets': {
   'web.report_assets_common': [
       'custom_sale_order_report/static/src/webclient/actions/reports/report_tables.scss',

   ],

},

    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}
