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
    'name': 'Employee Salary Report',
    'version': '16.0.1.0.0',
    'summary': 'Employee Salary Report',
    'description': 'Employee Salary Report',
    'author': 'Hai Cheung (China) Limited',
    'depends': ['hr', 'hc_employee_updation','hc_employee_retirement_report','hc_employee_contract_tabs'],
    'data': [
        'views/hr_employee_views.xml',
    ],

}
