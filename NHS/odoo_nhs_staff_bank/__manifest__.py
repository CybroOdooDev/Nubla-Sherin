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
    'name': 'NHS Staff Bank Management',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'NHS internal staff bank management for workforce, shifts, availability, bookings and compliance.',
    'description': """
    NHS Staff Bank Management manages bank members, open shifts, availability, shift offers,
bookings, rates and workforce compliance. It helps NHS organisations manage flexible staffing
requirements, fill temporary shifts efficiently, and monitor bank and agency staffing costs.
""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base', 'mail', 'portal', 'odoo_nhs_establishment', 'odoo_nhs_training'],
    'data': [
        'security/nhs_staff_bank_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_bank_sequence_data.xml',
        'data/nhs_shift_type_data.xml',
        'data/nhs_skill_data.xml',
        'data/nhs_weekday_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'wizards/nhs_offer_shift_wizard_views.xml',
        'wizards/nhs_bulk_shift_wizard_views.xml',
        'wizards/nhs_escalate_agency_wizard_views.xml',
        'wizards/nhs_bank_report_wizard_views.xml',
        'views/nhs_bank_member_views.xml',
        'views/nhs_member_availability_views.xml',
        'views/nhs_bank_shift_views.xml',
        'views/nhs_shift_offer_views.xml',
        'views/nhs_shift_booking_views.xml',
        'views/nhs_bank_rate_views.xml',
        'views/nhs_skill_views.xml',
        'views/nhs_shift_type_views.xml',
        'views/nhs_bank_portal_templates.xml',
        'views/nhs_bank_config_views.xml',
        'views/nhs_bank_dashboard_views.xml',
        'report/nhs_fill_rate_report.xml',
        'report/nhs_bank_spend_report.xml',
        'report/nhs_member_statement_report.xml',
        'views/nhs_bank_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_staff_bank/static/src/dashboard/nhs_bank_dashboard.js',
            'odoo_nhs_staff_bank/static/src/dashboard/nhs_bank_dashboard.xml',
            'odoo_nhs_staff_bank/static/src/dashboard/nhs_bank_dashboard.scss',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,

}
