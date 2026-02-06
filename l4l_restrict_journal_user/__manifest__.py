# -*- coding: utf-8 -*-
################################################################################
#
#	Cats and Dogs Solution
#
#	Copyright (C) Cats and Dogs Solution.
#
#	This program is under the terms of the Odoo Proprietary License v1.0
#	(OPL-1)
#	It is forbidden to publish, distribute, sublicense, or sell copies of the
#	Software or modified copies of the Software.
#
################################################################################
{
    'name': "Access Restriction of Journals",
    'category': 'Invoicing',
    'version': '18.0.1.0.0',
    'sequence': 1,
    'summary': """Restrict Journal, Restrict Journal For Users, Users, Restrict, Restrict Users, Restrict Journal, Visibility, User Journal, Security, Restrict Journal For User, Journal, Journal Security, Allow Users, Journal Visibility, Sales, Account, Invoicing, Bill, L4L, Leap, 4, Logic, Leap4Logic""",
    'description': """Odoo Currently Displays All Journals to Every User. Our Module Helps You to Restrict Journal For Users Means that Display Specific Journal to the User""",
    'author': 'Cats and Dogs Solutions',
    'company': 'Cats and Dogs Solutions',
    'maintainer': 'Cats and Dogs Solutions',
    'depends': ['mail', 'account'],
    'data': [
        'security/res_groups.xml',
        'views/res_users_view.xml',
    ],
    'application': True,
    'installation': True,
    'license': 'OPL-1',
}
