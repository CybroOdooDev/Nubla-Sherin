# -*- coding: utf-8 -*-
#######################################################################################
#
#    Hai Cheung (China) Limited
#
#    Copyright (C) Hai Cheung (China) Limited.
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
########################################################################################
{
    'name': "Megawin Contract Report",
    'version': '16.0.1.0.0',
    'summary': "Megawin Employee Contract Report in Contract",
    'description': "Megawin Contract Report",
    'author': 'Hai Cheung (China) Limited',
    'depends': ['hr_contract'],
    'data': [
        'data/paperformat.xml',
        'report/megawin_employee_report.xml',
        'report/ir_actions_report.xml'


    ],
    'assets': {
        'web.report_assets_common': [
        ],

    },
    'license': 'OPL-1',
    'application': False,
}
