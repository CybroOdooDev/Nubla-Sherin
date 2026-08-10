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
    'name': 'NHS Incident & Risk — Trust Suite Bridge',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Links NHS Incident & Risk to Trust Operations: sites, departments, and CQC inspections.',
    'description': """
    Auto-installing bridge module that seamlessly connects NHS Incident & Risk
     with NHS Trust Operations by syncing Trust Sites
     and Departments as Incident Locations and linking incidents to Trust and CQC Inspection records.
    """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'depends': ['odoo_nhs_incident_risk','odoo_nhs_trust_management','odoo_nhs_trust_operations'],
    'data': [
        'security/nhs_bridge_security.xml',
        'security/ir.model.access.csv',
        'wizards/nhs_trust_location_setup_wizard_views.xml',
        'views/nhs_incident_bridge_views.xml',
        'views/nhs_location_bridge_views.xml',
        'views/nhs_trust_bridge_views.xml',
        'views/nhs_trust_site_bridge_views.xml',
        'views/nhs_trust_department_bridge_views.xml',
        'views/nhs_trust_cqc_inspection_bridge_views.xml',
        'views/nhs_cqc_notification_bridge_views.xml',
        'views/nhs_sync_actions.xml',
    ],
    'images': ['static/description/banner.png'],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
    'auto_install': ['odoo_nhs_incident_risk', 'odoo_nhs_trust_operations'],
}
