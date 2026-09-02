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
    'name': 'NHS Medical Job Planning',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Annual job planning for consultants and SAS doctors - programmed '
               'activities, DCC/SPA split, on-call, objectives, two-party sign-off, '
               'annual review, and team capacity & completeness reporting.',
    'description': """
Manages the annual job-planning cycle for consultants and SAS doctors against their
funded Establishment post: the weekly timetable of Programmed Activities (DCC/SPA/
Additional/External), on-call frequency and category, personal objectives, doctor-and-
manager two-party sign-off with a full discussion trail, in-year revision, annual
rollover, and team-level capacity and completeness reporting for the board.
    """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base', 'mail', 'odoo_nhs_establishment'],
    'data': [
        'security/nhs_job_planning_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_job_plan_sequence_data.xml',
        'data/nhs_job_plan_session_category_data.xml',
        'data/nhs_oncall_supplement_rate_data.xml',
        'data/nhs_plan_year_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'wizards/nhs_job_plan_rollover_wizard_views.xml',
        'wizards/nhs_job_plan_reminder_wizard_views.xml',
        'views/nhs_establishment_post_views.xml',
        'views/nhs_plan_year_views.xml',
        'views/nhs_job_plan_session_category_views.xml',
        'views/nhs_oncall_profile_views.xml',
        'views/nhs_job_plan_views.xml',
        'views/nhs_job_plan_team_views.xml',
        'views/nhs_job_plan_dashboard_views.xml',
        'views/nhs_job_planning_config_views.xml',
        'report/nhs_job_plan_report.xml',
        'report/nhs_job_plan_team_capacity_report.xml',
        'report/nhs_job_plan_completeness_report.xml',
        'views/nhs_job_planning_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_nhs_job_planning/static/src/js/single_model_reference_field.js',
            'odoo_nhs_job_planning/static/src/dashboard/job_plan_dashboard.js',
            'odoo_nhs_job_planning/static/src/dashboard/job_plan_dashboard.xml',
            'odoo_nhs_job_planning/static/src/dashboard/job_plan_dashboard.scss',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
