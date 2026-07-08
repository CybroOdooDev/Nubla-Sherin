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
    'name': 'NHS Mandatory Training Register',
    'summary': 'Statutory & mandatory training compliance for the NHS — CSTF-aligned '
               'subjects, role-based requirements, expiry tracking, professional '
               'registration and team compliance reporting.',
    'description': """
NHS Mandatory Training Register
================================
Tracks whether every member of staff holds the statutory and mandatory training
their role requires, and whether it is still in date — turning the training-matrix
spreadsheet into a live, role-driven compliance system.

* CSTF-aligned training-subject catalogue with levels and refresh frequencies
* Role-based requirement matrix (staff group / post / individual overrides)
* Completion records with automatic expiry and status (compliant/due soon/expired)
* Professional-registration tracking (NMC / GMC / HCPC / GPhC / GDC…)
* Individual, team, department and organisation compliance % roll-ups
* The signature Training Matrix — members x subjects, colour-coded
* Reminders, escalation and a weekly compliance digest
* Board assurance, team matrix and CQC evidence-pack reporting
* Builds on the NHS Establishment Register (posts, staff groups, org hierarchy)
""",
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'OPL-1',
    'price': 0,
    'currency': 'EUR',
    'depends': [
        'odoo_nhs_establishment',
        'mail',
        'portal',
    ],
    'data': [
        'security/nhs_training_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_training_sequence_data.xml',
        'data/nhs_regulator_data.xml',
        'data/nhs_training_subject_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'wizards/nhs_bulk_completion_wizard_views.xml',
        'views/nhs_training_subject_views.xml',
        'views/nhs_requirement_profile_views.xml',
        'views/nhs_training_requirement_views.xml',
        'views/nhs_workforce_member_views.xml',
        'views/nhs_training_record_views.xml',
        'views/nhs_registration_views.xml',
        'views/nhs_regulator_views.xml',
        'views/nhs_establishment_post_views.xml',
        'views/nhs_org_unit_views.xml',
        'views/nhs_training_config_views.xml',
        'views/nhs_training_dashboard_views.xml',
        'views/nhs_training_menus.xml',
        'report/nhs_training_matrix_report.xml',
        'report/nhs_training_board_report.xml',
        'report/nhs_individual_record_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_training/static/src/matrix/training_matrix.js',
            'odoo_nhs_training/static/src/matrix/training_matrix.xml',
            'odoo_nhs_training/static/src/matrix/training_matrix.scss',
            'odoo_nhs_training/static/src/dashboard/training_dashboard.js',
            'odoo_nhs_training/static/src/dashboard/training_dashboard.xml',
        ],
    },
    'demo': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}
