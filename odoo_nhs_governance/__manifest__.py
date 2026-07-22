# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    Odoo Proprietary License v1.0 (OPL-1)
#
#############################################################################
{
    'name': 'NHS Governance Management',
    'summary': 'Board and committee management for the NHS — terms of reference, '
               'meeting cycles, agendas, papers, minutes, actions, declarations of '
               'interest and the Board Assurance Framework, linked to the risk register.',
    'description': """
NHS Governance Management is the corporate-governance layer of the NHS suite. It
supports the Company Secretary and Board Office with committee structures, terms
of reference, meeting cycles, agendas, board papers, minutes, action tracking,
declarations of interest and the Board Assurance Framework (BAF).
""",
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'OPL-1',
    'currency': 'EUR',
    'depends': ['odoo_nhs_trust_management', 'mail'],
    'data': [
        'security/nhs_governance_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_gov_sequence_data.xml',
        'data/nhs_gov_committee_type_data.xml',
        'data/nhs_gov_interest_category_data.xml',
        'data/nhs_gov_assurance_line_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
      
        'views/nhs_committee_views.xml',
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
        
        'views/nhs_governance_menus.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
