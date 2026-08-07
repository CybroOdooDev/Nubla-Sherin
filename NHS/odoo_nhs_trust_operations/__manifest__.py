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
    'name': 'NHS Trust Management — Operations & Compliance',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Sites, departments, CQC compliance, financials, and workforce for NHS Trusts',
    'description': """
NHS Trust Management — Operations & Compliance extends the 
Foundation module with NHS operational management including Trust sites, departments,
 CQC inspections, workforce tracking, financial governance, compliance workflows, and role-based security access.
    """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'depends': ['odoo_nhs_trust_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/odoo_nhs_trust_operations_security.xml',
        'views/nhs_trust_department_views.xml',
        'views/nhs_trust_site_views.xml',
        'views/nhs_trust_specialty_views.xml',
        'views/nhs_trust_cqc_inspection_views.xml',
        'views/nhs_trust_views_inherit.xml',
        'views/nhs_trust_menus_inherit.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'application': False,
    'installable': True,
    'auto_install': False,
}
