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
#    You should have received a copy of the GNU LESSER PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'NHS Governance Management',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Board & committee management for the NHS — terms of reference, '
               'meeting cycles, agendas, papers, minutes, actions, declarations of '
               'interest and the Board Assurance Framework, linked to the risk register.',
    'description': """NHS Governance Management is the corporate-governance layer of the Nubla NHS suite.
    It manages the committee structure and terms of reference, the meeting cycle (agendas, papers,
    minutes), the actions arising, declarations of interest, and the Board Assurance Framework (BAF)
    that links the organisation's strategic risks to their controls and assurances.
    """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'odoo_nhs_trust_management',
    ],
    'data': [
        'security/nhs_governance_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_gov_sequence_data.xml',
        'data/nhs_gov_committee_type_data.xml',
        'data/nhs_gov_interest_category_data.xml',
        'data/nhs_gov_assurance_line_data.xml',
        'data/nhs_gov_month_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'wizards/nhs_meeting_generate_wizard_views.xml',
        'wizards/nhs_agenda_from_cycle_wizard_views.xml',
        'wizards/nhs_board_pack_wizard_views.xml',
        'views/nhs_committee_views.xml',
        'views/res_partner_views.xml',
        'views/nhs_director_views.xml',
        'views/nhs_meeting_views.xml',
        'views/nhs_agenda_item_views.xml',
        'views/nhs_cycle_of_business_views.xml',
        'views/nhs_meeting_action_views.xml',
        'views/nhs_declaration_views.xml',
        'views/nhs_baf_views.xml',
        'views/nhs_governance_calendar_views.xml',
        'views/nhs_governance_dashboard_views.xml',
        'views/nhs_governance_config_views.xml',
        'report/nhs_board_pack_report.xml',
        'report/nhs_baf_report.xml',
        'report/nhs_doi_register_report.xml',
        'report/nhs_action_log_report.xml',
        'views/nhs_governance_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_governance/static/src/dashboard/governance_dashboard.js',
            'odoo_nhs_governance/static/src/dashboard/governance_dashboard.xml',
            'odoo_nhs_governance/static/src/dashboard/governance_dashboard.scss',
        ],
        'web.assets_backend_lazy': [
            'odoo_nhs_governance/static/src/baf_pivot_color/baf_pivot_color.js',
            'odoo_nhs_governance/static/src/baf_pivot_color/baf_pivot_color.xml',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
