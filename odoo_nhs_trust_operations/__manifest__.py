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
    'depends': ['odoo_nhs_trust_management'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'data': [
        'security/ir.model.access.csv',
        'security/odoo_nhs_trust_operations_security.xml',
        'views/nhs_trust_department_views.xml',
        'views/nhs_trust_site_views.xml',
        'views/nhs_trust_cqc_inspection_views.xml',
        'views/nhs_trust_views_inherit.xml',
        'views/nhs_trust_menus_inherit.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
}
