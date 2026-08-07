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
    'name': 'NHS ERIC Returns',
    'summary': 'Generate the mandatory annual Estates Returns Information Collection '
               '(ERIC) automatically from the NHS Estate Register and Estates '
               'Compliance — versioned to the NHS England data set, validated and export-ready.',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': [
        'odoo_nhs_estate',
        'odoo_nhs_estate_compliance',
    ],
    'data': [
        'security/nhs_eric_security.xml',
        'security/ir.model.access.csv',
        'views/nhs_eric_dataset_views.xml',
        'views/nhs_eric_return_views.xml',
        'views/nhs_eric_value_views.xml',
        'views/nhs_eric_config_views.xml',
        'views/nhs_eric_dashboard_views.xml',
        'views/nhs_eric_menus.xml',
        'report/nhs_eric_return_report.xml',
        'report/nhs_eric_gap_report.xml',
        'wizards/nhs_eric_new_year_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_eric/static/src/dashboard/dashboard.js',
            'odoo_nhs_eric/static/src/dashboard/dashboard.xml',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}

