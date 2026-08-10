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
    'name': 'NHS Recruitment Pipeline',
    'version': '19.0.1.0.0',
    'category': 'Healthcare/NHS',
    'summary': 'Vacancy-to-hire recruitment for the NHS — vacancy approval against '
               'funded posts, adverts, portal applications, shortlisting, interviews, '
               'offers and the NHS Employment Check Standards, with onboarding into the '
               'establishment.',
    'description': """
NHS Recruitment Pipeline manages the whole vacancy-to-hire journey: turning a
funded vacancy into a filled post. It raises and approves vacancies against
funded establishment posts, advertises them, captures applications through a
public portal form, shortlists and interviews candidates, makes offers, runs
the NHS pre-employment checks, and hands the successful hire back to the
Establishment Register as an updated in-post position.
""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base','odoo_nhs_establishment','mail','portal'],
    'data': [
        'security/nhs_recruitment_security.xml',
        'security/ir.model.access.csv',
        'data/nhs_recruitment_sequence_data.xml',
        'data/nhs_check_type_data.xml',
        'data/nhs_check_profile_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'wizards/nhs_shortlist_wizard_views.xml',
        'wizards/nhs_bulk_communicate_wizard_views.xml',
        'wizards/nhs_onboard_wizard_views.xml',
        'wizards/nhs_interview_reschedule_wizard_views.xml',
        'views/nhs_vacancy_views.xml',
        'views/nhs_application_views.xml',
        'views/nhs_candidate_views.xml',
        'views/nhs_interview_views.xml',
        'views/nhs_offer_views.xml',
        'views/nhs_check_views.xml',
        'views/nhs_recruitment_portal_templates.xml',
        'views/nhs_recruitment_config_views.xml',
        'views/nhs_recruitment_dashboard_views.xml',
        'report/nhs_vacancy_advert_report.xml',
        'report/nhs_offer_letter_report.xml',
        'report/nhs_shortlist_summary_report.xml',
        'report/nhs_check_certificate_report.xml',
        'views/nhs_recruitment_menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'odoo_nhs_recruitment/static/src/css/public_application.css',
            'odoo_nhs_recruitment/static/src/js/public_application.js',
        ],
        'web.assets_backend': [
            'odoo_nhs_recruitment/static/src/dashboard/recruitment_dashboard.js',
            'odoo_nhs_recruitment/static/src/dashboard/recruitment_dashboard.xml',
            'odoo_nhs_recruitment/static/src/dashboard/recruitment_dashboard.scss',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
