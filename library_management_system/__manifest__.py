# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Nublasherin k (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0(OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################
{
    'name': 'Library Management  System',
    'version': '19.0.1.0.2',
    'category': 'Industries',
    'summary': """Advanced Library Management Module to Manage Books, Books Borrowing, Members, etc.""",
    'description': """Library Management System, Library Management, Odoo19, Books, Borrowing, ISBN, Book Importing, Library""",
    'author': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['mail', 'product', 'contacts', 'account', 'stock',
                'sale_management'],
    'data': [
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'data/product_category_data.xml',
        'security/library_management_system_groups.xml',
        'security/library_management_system_rule.xml',
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/book_register_views.xml',
        'views/res_config_settings_views.xml',
        'views/library_award_views.xml',
        'views/library_dashboard.xml',
        'views/membership_type_views.xml',
        'views/book_author_views.xml',
        'views/book_publisher_views.xml',
        'views/library_fine_rule.xml',
        'wizard/renew_membership_views.xml',
        'wizard/import_book_views.xml',
        'wizard/create_book_views.xml',
        'views/library_fine.xml',
        'wizard/issued_books_report_views.xml',
        'wizard/member_report_views.xml',
        'wizard/books_report_views.xml',
        'reports/fine_report.xml',
        'reports/book_report_templates.xml',
        'reports/issued_book_report_templates.xml',
        'reports/member_report_templates.xml',
        'reports/product_template_templates.xml',
        'reports/res_partner_templates.xml',
        'views/library_management_system_menus.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js',
            'library_management_system/static/src/js/action_manager.js',
            'library_management_system/static/src/css/dashboard_views.css',
            'library_management_system/static/src/js/library_dashboard.js',
            'library_management_system/static/src/xml/dashboard.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'price': 99,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'application': True,
}
