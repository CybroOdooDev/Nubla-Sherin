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
    'name': "Multi Dashboard",
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': """Odoo Dynamic Dashboard, Dynamic Dashboard, Odoo AI, Odoo19, 
    Odoo19 Dashboards, Dashboard with AI, AI Dashboard, Odoo Dashboard,Graph View,""",
    'description': """Create Configurable Odoo Dynamic Dashboard to get the 
    information that are relevant to your business, department, or a specific 
    process or need""",
    'live_test_url': 'https://www.youtube.com/watch?v=bSUashq4_D8',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['web', 'mail'],
    'data': [
        'data/mail_template_data.xml',
        'data/multi_dashboard_data.xml',
        'data/multi_dashboard_alert_data.xml',
        'security/multi_dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/multi_dashboards_views.xml',
        'views/multi_dashboard_charts_views.xml',
        'views/multi_dashboard_alert_views.xml',
        'wizard/import_chart_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/dom-to-image-more/3.5.0/dom-to-image-more.min.js',

            'multi_dashboard/static/src/lib/amCharts/index.js',
            'multi_dashboard/static/src/lib/amCharts/xy.js',
            'multi_dashboard/static/src/lib/amCharts/percent.js',
            'multi_dashboard/static/src/lib/amCharts/Animated.js',
            'multi_dashboard/static/src/lib/amCharts/Micro.js',
            'multi_dashboard/static/src/lib/amCharts/Dataviz.js',
            'multi_dashboard/static/src/lib/amCharts/Material.js',
            'multi_dashboard/static/src/lib/amCharts/radar.js',
            'multi_dashboard/static/src/lib/amCharts/vfs_fonts.js',

            'multi_dashboard/static/src/js/**/*.js',
            'multi_dashboard/static/src/xml/**/*.xml',
            'multi_dashboard/static/src/css/**/*.css',
            'multi_dashboard/static/src/css/**/*.scss',
            'multi_dashboard/static/src/lib/gridstack/**/*',
            'multi_dashboard/static/src/lib/tools/**/*',
            'multi_dashboard/static/src/lib/amCharts/exporting.js',
        ],
    },
    'external_dependencies': {
        'python': ['google-genai'],
    },
    'uninstall_hook': 'uninstall_hook',
    'license': "AGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
}
