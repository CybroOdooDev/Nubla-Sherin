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
    'name': 'NHS Estate Register',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Master register of the NHS physical estate — sites, buildings, '
               'floors and spaces, with tenure, Six Facet condition and backlog. '
               'Foundation of the NHS Estates & Facilities suite.',
    'description': """
NHS Estate Register is the master inventory of the NHS physical estate — sites, buildings, floors and functional 
spaces — with tenure, Six Facet condition surveying, and backlog maintenance tracking. It provides hierarchical 
roll-ups of GIA, clinical/non-clinical area splits, and ERIC-aligned function taxonomy. Built independently with no 
governance-track dependencies, it serves as the foundation for the Estates & Facilities vertical including compliance, 
ERIC returns, assets, and energy modules. Includes estate register PDF reports, building passports, and lease expiry 
dashboards.
     """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base', 'mail', 'web_hierarchy'],
    'data': [
        'security/nhs_estate_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_estate_sequence_data.xml',
        'data/nhs_estate_tenure_data.xml',
        'data/nhs_estate_condition_data.xml',
        'data/nhs_estate_function_data.xml',
        'views/nhs_estate_site_views.xml',
        'views/nhs_estate_building_views.xml',
        'views/nhs_estate_floor_views.xml',
        'views/nhs_estate_space_views.xml',
        'views/nhs_estate_condition_views.xml',
        'views/nhs_estate_tenure_views.xml',
        'views/nhs_estate_backlog_views.xml',
        'views/nhs_estate_config_views.xml',
        'views/nhs_estate_reporting_view.xml',
        'views/nhs_estate_dashboard_views.xml',
        'report/nhs_estate_register_report.xml',
        'report/nhs_estate_building_passport.xml',
        'views/nhs_estate_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_estate/static/src/dashboard/dashboard.js',
            'odoo_nhs_estate/static/src/dashboard/dashboard.xml',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
