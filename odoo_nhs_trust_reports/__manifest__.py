# -*- coding: utf-8 -*-
{
    'name': 'NHS Trust Management - Reports & Documents',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Trust Profile PDF, Excel directory export and document attachments for NHS Trusts',
    'description': """
NHS Trust Management - Reports & Documents
==========================================
Adds the document and output layer on top of the Foundation and Operations modules.

Key Features:
- Trust Profile PDF (QWeb, NHS blue #005EB8 branded):
    Header band · Identification · Organisational Hierarchy · Contact ·
    Governance (Chair, CEO, MD, DoN, Finance Director, Board Members table) ·
    Financials · Workforce & Capacity · Sites table · CQC Inspection History · Footer
- Trust Directory Excel Export (xlsxwriter):
    23-column sheet with NHS-blue header row, auto-filter, frozen panes.
    Filters: Health System, Status, Regions.
- Document attachments per Trust via standard Odoo chatter (no custom model).
- 'Print Trust Profile' button bound to the nhs.trust form via report binding_type.
- Reports submenu added to the root NHS Trusts menu.
    """,
    'author': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'depends': ['odoo_nhs_trust_operations'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'external_dependencies': {'python': ['xlsxwriter']},
    'data': [
        'security/ir.model.access.csv',
        'wizards/nhs_trust_directory_export_views.xml',
        'views/nhs_trust_menus_inherit.xml',
        'reports/nhs_trust_profile_report.xml',
        'reports/nhs_trust_profile_template.xml',
    ],
    'demo': [],
}
