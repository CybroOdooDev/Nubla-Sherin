# -*- coding: utf-8 -*-
{
    'name': 'NHS Trust Management - Foundation',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Core foundation for the NHS Trust Management System in Odoo 19',
    'description': """
NHS Trust Management - Foundation
=================================
Establishes the foundational structures, workflow mechanisms, security groups, 
leadership configurations, and preloaded geographic/governance master data 
required by an NHS Trust Management framework.

Key Features:
- Master Data Setup: NHS Regions, Trust Types, Integrated Care Boards (ICBs), 
  Integrated Care Systems (ICSs), and Scottish Health Boards.
- England & Scotland Geographic Scopes.
- Core NHS Trust Record: Comprehensive ODS Code, address, leadership, vat, and region profiles.
- Strict Workflow State Control: Lock direct writes to state, requiring a 
  justified wizard state transition with immutable logging.
- Leadership Tracking: Extensive partner extensions for Board Chair, CEO, 
  Medical Director, Nursing Director, and other voting members.
- Dynamic Security Scoping: Restrict views based on User's allowed ICBs/Health Boards.
    """,
    'author': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'contacts',
    ],
    'data': [
        # Security definitions loaded first
        'security/odoo_nhs_trust_management_security.xml',
        'security/ir.model.access.csv',

        # Seed master data
        'data/nhs_region_data.xml',
        'data/nhs_trust_type_data.xml',
        'data/nhs_icb_data.xml',
        'data/nhs_health_board_data.xml',

        # Wizards loaded before base views
        'wizards/nhs_trust_state_change_wizard_views.xml',

        # Base and extended views
        'views/nhs_region_views.xml',
        'views/nhs_trust_type_views.xml',
        'views/nhs_icb_views.xml',
        'views/nhs_ics_views.xml',
        'views/nhs_health_board_views.xml',
        'views/nhs_trust_state_log_views.xml',
        'views/res_partner_views.xml',
        'views/nhs_trust_views.xml',

        # Menu structure loaded last
        'views/nhs_trust_menus.xml',

    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}

