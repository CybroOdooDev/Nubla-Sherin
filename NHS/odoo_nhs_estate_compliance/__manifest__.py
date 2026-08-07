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
    'name': 'NHS Estates Compliance',
    'summary': 'Statutory estates compliance scheduling for the NHS — water, fire, '
               'electrical, ventilation, asbestos, LOLER and medical gas — with '
               'HTM references, accountable persons, certificates and ERIC-ready reporting.',
    'description': """NHS Estates Compliance is a comprehensive Odoo module designed to manage statutory compliance 
    activities across healthcare estates. It enables organizations to schedule and track recurring compliance 
    inspections, record test results, manage certificates, remedial actions, contractor visits, duty role assignments, 
    and compliance responsibilities. The module provides automated reminders, status tracking, dashboards, reports, 
    and audit-ready records to help ensure compliance with NHS standards and statutory regulations across sites, 
    buildings, spaces, and equipment.""",
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
        'maintenance',
        'mail',
        'resource',
    ],
    'data': [
        'security/nhs_estate_compliance_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_compliance_sequence_data.xml',
        'data/nhs_duty_role_data.xml',
        'data/nhs_compliance_discipline_data.xml',
        'data/nhs_compliance_accreditation_data.xml',
        'data/nhs_compliance_type_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/nhs_compliance_type_views.xml',
        'views/nhs_compliance_discipline_views.xml',
        'views/nhs_compliance_remedial_views.xml',
        'views/nhs_compliance_test_views.xml',
        'views/nhs_compliance_item_views.xml',
        'views/nhs_duty_role_views.xml',
        'views/nhs_compliance_contractor_views.xml',
        'views/nhs_compliance_config_views.xml',
        'views/nhs_compliance_dashboard_views.xml',
        'report/nhs_compliance_position_report.xml',
        'report/nhs_compliance_board_report.xml',
        'report/nhs_certificate_pack_report.xml',
        'wizards/nhs_compliance_bulk_apply_wizard_views.xml',
        'wizards/nhs_compliance_eric_export_wizard_views.xml',
        'wizards/nhs_compliance_reschedule_wizard_views.xml',
        'wizards/nhs_compliance_position_report_wizard_views.xml',
        'wizards/nhs_certificate_pack_wizard_views.xml',
        'wizards/nhs_compliance_pam_wizard_views.xml',
        'wizards/nhs_compliance_register_excel_wizard_views.xml',
        'views/maintenance_equipment_views.xml',
        'views/maintenance_request_views.xml',
        'views/nhs_compliance_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_estate_compliance/static/src/dashboard/dashboard.js',
            'odoo_nhs_estate_compliance/static/src/dashboard/dashboard.xml',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
