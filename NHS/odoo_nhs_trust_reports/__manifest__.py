# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'NHS Trust Management — Reports & Documents',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Trust Profile PDF, Excel directory export and document attachments for NHS Trusts',
    'description': """
NHS Trust Management — Reports & Documents provides NHS Trust reporting and document generation features including 
Trust Profile PDF reports, Excel directory exports, attachment management, and integrated reporting workflows within Odoo.
    """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'license': 'LGPL-3',
    'website': 'https://www.cybrosys.com',
    'depends': ['odoo_nhs_trust_operations'],
    'external_dependencies': {'python': ['xlsxwriter']},
    'data': [
        'security/ir.model.access.csv',
        'wizards/nhs_trust_directory_export_wizard_views.xml',
        'views/nhs_trust_menus_inherit.xml',
        'report/nhs_trust_profile_report.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'application': False,
    'installable': True,
    'auto_install': False,

}
