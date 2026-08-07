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
    'name': 'NHS Medical Devices and Equipment Management',
    'summary': 'Medical-device & equipment register for the NHS — inventory, PPM & '
               'calibration scheduling, lifecycle & replacement planning, and MHRA/CAS '
               'safety-alert handling. Community-first: no Enterprise (account_asset) dependency.',
    'description': """NHS Medical Devices & Equipment Management provides a complete register for medical devices and 
    equipment, covering maintenance, calibration, lifecycle, replacement planning, warranties, and service contracts. 
    It also manages MHRA/CAS safety alerts with affected-device tracking and action history. Includes dashboards, 
    reporting, reminders, and audit-ready records for NHS estates and EBME teams.""",
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': [
        'odoo_nhs_estate',
        'maintenance',
    ],
    'data': [
        'security/nhs_estate_assets_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_device_sequence_data.xml',
        'data/nhs_schedule_type_data.xml',
        'data/nhs_device_category_data.xml',
        'data/ir_cron_data.xml',
        'views/nhs_device_views.xml',
        'views/nhs_device_category_views.xml',
        'views/nhs_device_schedule_views.xml',
        'views/nhs_device_service_views.xml',
        'views/nhs_device_alert_views.xml',
        'views/nhs_device_warranty_views.xml',
        'views/nhs_device_config_views.xml',
        'views/nhs_device_dashboard_views.xml',
        'views/maintenance_request_views.xml',
        'views/maintenance_equipment_views.xml',
        'report/nhs_device_passport_report.xml',
        'report/nhs_replacement_forecast_report.xml',
        'report/nhs_alert_response_report.xml',
        'wizards/nhs_device_bulk_schedule_wizard_views.xml',
        'wizards/nhs_device_service_wizard_views.xml',
        'wizards/nhs_alert_match_wizard_views.xml',
        'wizards/nhs_device_decommission_wizard_views.xml',
        'wizards/nhs_device_passport_wizard_views.xml',
        'wizards/nhs_alert_response_wizard_views.xml',
        'views/nhs_device_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_estate_assets/static/src/dashboard/device_dashboard.js',
            'odoo_nhs_estate_assets/static/src/dashboard/device_dashboard.xml',
            'odoo_nhs_estate_assets/static/src/dashboard/device_dashboard.css',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
