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
    'name': 'NHS e-Rostering',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Safe, rule-checked NHS staff rostering on the funded establishment - demand-based '
               'rotas, working-time and skill-mix rules, the training compliance gate, staff '
               'self-service, and automatic escalation of unfilled duties to the Staff Bank.',
    'description': """
    NHS e-Rostering builds and manages staff rotas against the funded establishment: shift
types and rotation templates, demand (required staffing per shift), a rule-checked roster
grid, the training/registration compliance gate, leave handling, staff self-service,
duty-swap requests, publication, and automatic escalation of unfilled duties into the
Staff Bank (and on to agency) with cost visibility.
""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base', 'mail', 'portal', 'odoo_nhs_establishment', 'odoo_nhs_training'],
    'data': [
        'security/nhs_rostering_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_roster_sequence_data.xml',
        'data/nhs_roster_rule_data.xml',
        'data/nhs_leave_type_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'wizards/nhs_apply_template_wizard_views.xml',
        'wizards/nhs_copy_period_wizard_views.xml',
        'wizards/nhs_publish_wizard_views.xml',
        'wizards/nhs_escalate_wizard_views.xml',
        'views/nhs_roster_unit_views.xml',
        'views/nhs_roster_shift_type_views.xml',
        'views/nhs_roster_skill_views.xml',
        'views/nhs_rotation_template_views.xml',
        'views/nhs_demand_template_views.xml',
        'views/nhs_roster_period_views.xml',
        'views/nhs_duty_views.xml',
        'views/nhs_duty_assignment_views.xml',
        'views/nhs_roster_rule_views.xml',
        'views/nhs_rule_violation_views.xml',
        'views/nhs_leave_type_views.xml',
        'views/nhs_leave_entitlement_views.xml',
        'views/nhs_leave_request_views.xml',
        'views/nhs_swap_request_views.xml',
        'views/nhs_roster_preference_views.xml',
        'views/nhs_roster_escalation_views.xml',
        'views/nhs_org_unit_views.xml',
        'views/nhs_workforce_member_views.xml',
        'views/nhs_roster_portal_templates.xml',
        'views/nhs_roster_config_views.xml',
        'views/nhs_roster_dashboard_views.xml',
        'report/nhs_roster_unit_rota_report.xml',
        'report/nhs_roster_personal_rota_report.xml',
        'report/nhs_roster_fill_gaps_report.xml',
        'views/nhs_rostering_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_rostering/static/src/js/roster_grid/roster_grid.js',
            'odoo_nhs_rostering/static/src/xml/roster_grid/roster_grid.xml',
            'odoo_nhs_rostering/static/src/scss/roster_grid.scss',
            'odoo_nhs_rostering/static/src/js/dashboard/roster_dashboard.js',
            'odoo_nhs_rostering/static/src/xml/dashboard/roster_dashboard.xml',
            'odoo_nhs_rostering/static/src/scss/roster_dashboard.scss',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
