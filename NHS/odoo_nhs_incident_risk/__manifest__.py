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
    'name': 'NHS Incident & Risk Management',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'NHS Bckoffice Operations in Odoo, NHS Incident, Investigation, Compliance and Risk Management system.',
    'description': """NHS Incident & Risk Management,Datix Alternative,Risk Management, 
    Incident Management,Datix,NHS,NHS Odoo, NHS Trust Management,
    Healthcare Risk Management,athin code open avoolla Healthcare Incident Management, UK Healthcare,NHS Backoffice, 
    NHS Operations, NHS Governanceodoo, odoo nhs, odoo in nhs, odoo apps for nhs, nhs, ODOO NHS,""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base', 'mail', 'portal'],
    'data': [
        'security/nhs_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_sequence_data.xml',
        'data/nhs_matrix_data.xml',
        'data/nhs_holiday_data.xml',
        'data/nhs_terminology_data.xml',
        'data/nhs_category_data.xml',
        'data/nhs_notification_rule_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/nhs_location_views.xml',
        'views/nhs_incident_views.xml',
        'views/nhs_investigation_views.xml',
        'views/nhs_statutory_views.xml',
        'views/nhs_action_views.xml',
        'views/nhs_risk_views.xml',
        'views/nhs_config_views.xml',
        'views/nhs_dashboard_views.xml',
        'views/public_report_templates.xml',
        'report/nhs_incident_reports.xml',
        'report/nhs_risk_reports.xml',
        'report/nhs_board_pack_report.xml',
        'wizards/nhs_triage_wizard_views.xml',
        'wizards/nhs_riddor_wizard_views.xml',
        'wizards/nhs_risk_escalate_wizard_views.xml',
        'wizards/nhs_lfpse_export_wizard_views.xml',
        'wizards/nhs_risk_review_wizard_views.xml',
        'wizards/nhs_provider_setup_wizard_views.xml',
        'wizards/nhs_risk_close_wizard_views.xml',
        'views/nhs_menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'odoo_nhs_incident_risk/static/src/js/public_form.js',
            'odoo_nhs_incident_risk/static/src/css/public_form.css',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,

}
