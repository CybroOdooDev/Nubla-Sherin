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
    'name': 'Employee Probation Email Notification',
    'version': '16.0.1.0.0',
    'summary': 'Automatically sends email reminders during employee probation period.',
    'description': 'This module automates the process of sending email notifications to managers'
                   ' when employees complete 30 days after their onboarding date.',
    'author': 'Hai Cheung (China) Limited',
    'depends': ['hr'],
    'data': [
        'data/ir_cron.xml',
        'data/mail_template.xml',
    ],
}