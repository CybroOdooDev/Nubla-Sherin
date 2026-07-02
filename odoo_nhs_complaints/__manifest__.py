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
    'name': 'NHS Complaints & PALS Management',
    'summary': 'Statutory complaints handling, PALS concern resolution, KO41a '
               'returns and PHSO escalation — integrated with NHS Incident & Risk',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'OPL-1',
    'price': 0,
    'currency': 'EUR',
    'depends': [
        'odoo_nhs_incident_risk',
    ],
    'data': [
        'security/nhs_complaints_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_complaint_sequence_data.xml',
        'data/nhs_complaint_subject_data.xml',
        'data/nhs_complaint_timescale_data.xml',
        'data/nhs_complaint_letter_templates.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/nhs_complaint_phso_views.xml',
        'views/nhs_complaint_views.xml',
        'views/nhs_complaint_correspondence_views.xml',
        'views/nhs_complainant_views.xml',
        'views/nhs_complaint_investigation_views.xml',
        'views/nhs_complaint_config_views.xml',
        'views/nhs_complaint_dashboard_views.xml',
        'views/nhs_incident_views_inherit.xml',
        'views/nhs_action_views_inherit.xml',
        'wizards/nhs_complaint_escalate_wizard_views.xml',
        'wizards/nhs_complaint_response_wizard_views.xml',
        'wizards/nhs_complaint_link_incident_wizard_views.xml',
        'wizards/nhs_ko41a_export_wizard_views.xml',
        'report/nhs_complaint_response_report.xml',
        'report/nhs_complaint_ack_report.xml',
        'report/nhs_ko41a_report.xml',
        'views/nhs_complaint_menus.xml',
        'views/public_complaint_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'odoo_nhs_complaints/static/src/js/public_complaint.js',
            'odoo_nhs_complaints/static/src/css/public_complaint.css',
        ],
    },
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
