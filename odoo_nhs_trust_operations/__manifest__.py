# -*- coding: utf-8 -*-
{
    'name': 'NHS Trust Management - Operations & Compliance',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Sites, departments, CQC compliance, financials, and workforce for NHS Trusts',
    'description': """
NHS Trust Management - Operations & Compliance
===============================================
Extends the Foundation module with the full operational picture of an NHS Trust.

Key Features:
- Trust Sites: Physical locations (hospitals, clinics, ambulance stations) with GPS,
  A&E type, bed capacity, opening hours, and clinical specialties.
- Departments: Sub-units within sites with head, specialty, staff count, and type
  (clinical / corporate / support / research).
- CQC Inspections: Full Care Quality Commission inspection history with all 5 KLOE
  ratings (Safe, Effective, Caring, Responsive, Well-Led) plus Overall rating.
- Financials: Budget, income, expenditure, surplus/deficit (auto-computed), capital
  CDEL, and PFI obligations — all in GBP, informational only.
- Workforce: Total FTE (manually maintained) and auto-summed bed capacity from sites.
- Security: Record rules scoping Site, Department, and CQC records to the user's
  allowed ICBs / Health Boards.
- Operations & Compliance menus added to the root NHS Trusts menu.
    """,
    'author': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'depends': ['odoo_nhs_trust_management'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'data': [
        # Security first
        'security/ir.model.access.csv',
        # Views for new operational models
        'views/nhs_trust_department_views.xml',
        'views/nhs_trust_site_views.xml',
        'views/nhs_trust_cqc_inspection_views.xml',
        # Inherited extension to nhs.trust form (adds tabs + stat buttons)
        'views/nhs_trust_views_inherit.xml',
        # Menu additions
        'views/nhs_trust_menus_inherit.xml',
    ],
    'demo': [],
}
