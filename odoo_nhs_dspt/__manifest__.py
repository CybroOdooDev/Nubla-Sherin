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
    'name': 'NHS DSPT Compliance',
    'summary': 'Manage the annual NHS Data Security and Protection Toolkit (DSPT) '
               'self-assessment — assertions, evidence, ownership, gaps, improvement '
               'plans and submission. Versioned to the NHS England edition. For NHS '
               'organisations and every supplier handling NHS data.',
    'description': """
Manages an organisation's Data Security and Protection Toolkit (DSPT) — the mandatory
annual self-assessment every NHS organisation and every supplier handling NHS data
must complete and publish. Turns the toolkit from a once-a-year spreadsheet scramble
into a year-round, owned, evidenced and auditable process.
""",
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'currency': 'EUR',
    'depends': ['base','mail'],
    'data': [
        'security/nhs_dspt_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_dspt_sequence_data.xml',
        'data/nhs_dspt_edition_2025_26_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'data/nhs_dspt_baseline_data.xml',
        'wizards/nhs_dspt_generate_wizard_views.xml',
        'wizards/nhs_dspt_carry_forward_wizard_views.xml',
        'wizards/nhs_dspt_new_edition_wizard_views.xml',
        'wizards/nhs_dspt_bulk_owner_wizard_views.xml',
        'views/nhs_dspt_edition_views.xml',
        'views/nhs_dspt_assertion_views.xml',
        'views/nhs_dspt_evidence_views.xml',
        'views/nhs_dspt_action_views.xml',
        'views/nhs_dspt_assessment_views.xml',
        'views/nhs_dspt_config_views.xml',
        'views/nhs_dspt_dashboard_views.xml',
        'report/nhs_dspt_status_report.xml',
        'report/nhs_dspt_improvement_plan_report.xml',
        'report/nhs_dspt_assurance_summary_report.xml',
        'views/nhs_dspt_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_dspt/static/src/dashboard/dspt_dashboard.js',
            'odoo_nhs_dspt/static/src/dashboard/dspt_dashboard.xml',
            'odoo_nhs_dspt/static/src/dashboard/dspt_dashboard.scss',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}
