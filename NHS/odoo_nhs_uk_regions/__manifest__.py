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
    'name': 'NHS Trust Management — UK Regions Extension',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Extend NHS Trust management for Wales and Northern Ireland',
    'description': """
This module extends NHS Trust Management by adding support for NHS Wales
and Health and Social Care Northern Ireland organisations.
It includes Welsh Local Health Boards, HSC Trusts, and NIAS records.
""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['odoo_nhs_trust_management', 'odoo_nhs_ods_sync'],
    'data': [
        'security/odoo_nhs_uk_regions_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_region_data.xml',
        'data/nhs_trust_type_data.xml',
        'data/nhs_welsh_lhb_data.xml',
        'data/nhs_trust_data_wales.xml',
        'data/nhs_trust_data_ni.xml',
        'views/nhs_welsh_lhb_views.xml',
        'views/nhs_trust_views_inherit.xml',
        'views/nhs_ods_organisation_views_inherit.xml',
        'views/res_users_views_inherit.xml',
        'views/nhs_trust_menus_inherit.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,

}
