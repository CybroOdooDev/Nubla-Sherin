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
    'name': 'NHS Establishment Register',
    'summary': 'The funded-post register for NHS workforce — funded vs in-post vs '
               'vacant FTE by team, Agenda for Change band and cost centre, with '
               'establishment change control. Foundation of the NHS Workforce suite.',
    'description': """
NHS Establishment Register
===========================
The master record of an organisation's FUNDED POSTS — the budgeted shape of the
workforce, defined in positions rather than people. Tracks funded establishment
against staff actually in post, exposing the vacancy gap that drives recruitment,
safe staffing and pay-budget planning.

* Organisational hierarchy: Directorate -> Division -> Department -> Team
* Funded-post register with Agenda for Change band, staff group and cost centre
* Funded vs in-post vs vacant FTE and headcount, rolled up at every level
* Vacancy register and vacancy-rate reporting
* Establishment change control with workforce + finance approval workflow
* Agenda for Change pay-band reference data and indicative pay-cost roll-ups
* A stable post API for the Training, Recruitment, Staff Bank and Rostering modules
""",
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'OPL-1',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base', 'mail', 'web_hierarchy'],
    'data': [
        'security/nhs_establishment_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_establishment_sequence_data.xml',
        'data/nhs_staff_group_data.xml',
        'data/nhs_afc_band_data.xml',
        'data/ir_cron_data.xml',
        'wizards/nhs_establishment_change_wizard_views.xml',
        'views/nhs_org_unit_views.xml',
        'views/nhs_establishment_post_views.xml',
        'views/nhs_afc_band_views.xml',
        'views/nhs_establishment_change_views.xml',
        'views/nhs_establishment_config_views.xml',
        'views/nhs_establishment_dashboard_views.xml',
        'views/nhs_establishment_menus.xml',
        'report/nhs_establishment_report.xml',
        'report/nhs_vacancy_register_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_establishment/static/src/js/nhs_establishment_dashboard.js',
            'odoo_nhs_establishment/static/src/xml/nhs_establishment_dashboard.xml',
            'odoo_nhs_establishment/static/src/css/nhs_establishment_dashboard.css',
        ],
        'web.assets_backend_lazy': [
            'odoo_nhs_establishment/static/src/js/hierarchy_patch.js',
        ],
    },
    'demo': [],
    'images': ['static/description/banner.jpg'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
