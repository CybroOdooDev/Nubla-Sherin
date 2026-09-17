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
    "name": "NHS Theme",
    "version": "19.0.1.0.0",
    "category": "Themes/Backend",
    "summary": "NHS Backend Theme is the official theme for NHS modules in Odoo",
    "description": """Minimalist and elegant backend theme tailored for NHS Trust Management and other NHS apps""",
    "author": "Cybrosys Techno Solutions",
    "company": "Cybrosys Techno Solutions",
    "maintainer": "Cybrosys Techno Solutions",
    "website": "https://www.cybrosys.com",
    "depends": ["web", "mail"],
    "data": [
    ],
    "assets": {
        "web.assets_backend": [
            "theme_nhs/static/src/xml/menu_panels.xml",
            "theme_nhs/static/src/xml/nav_bar_panel.xml",
            "theme_nhs/static/src/xml/home_menus.xml",
            "theme_nhs/static/src/xml/side_bar_panel.xml",
            "theme_nhs/static/src/scss/nav.scss",
            "theme_nhs/static/src/scss/sidebar.scss",
            "theme_nhs/static/src/css/style.css",
            "theme_nhs/static/src/js/home_menus.js",
            "theme_nhs/static/src/js/search_apps.js",
        ],
        "web.assets_frontend": [
            "theme_nhs/static/src/scss/login.scss",
        ],
    },
    "images": [
        "static/description/banner.jpg",
        "static/description/theme_screenshot.jpg",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
