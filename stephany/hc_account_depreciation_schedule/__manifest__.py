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
    'name': "Account Depreciation Schedule",
    'version': '16.0.1.0.0',
    'summary': "Add Analytic Account and Not Depreciable Value to the Depreciation Schedule report",
    'description': "Add Analytic Account and Not Depreciable Value to the Depreciation Schedule report",
    'author': 'Hai Cheung (China) Limited',
    'depends': ['account_asset_custom'],
    'data': [
        'data/asset_report.xml',
    ],
    'license': 'OPL-1',
    'application': False,
}
