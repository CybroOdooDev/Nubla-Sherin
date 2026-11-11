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
#    This program is distributed in the hope it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestThemeNhsUI(HttpCase):
    """UI and HTTP test cases for NHS Backend Theme."""

    def test_01_web_login_page_renders_theme_assets(self):
        """Verify the login page renders successfully with status 200."""
        response = self.url_open('/web/login')
        self.assertEqual(response.status_code, 200, "Login page should return HTTP 200")
        self.assertIn(b'web.assets_frontend', response.content, "Frontend assets should be included in login page")

    def test_02_webclient_backend_access(self):
        """Verify the authenticated backend page renders with HTTP 200 or redirect."""
        self.authenticate('admin', 'admin')
        response = self.url_open('/odoo')
        self.assertIn(response.status_code, [200, 303], "Backend /odoo should return HTTP 200 or redirect")

    def test_03_theme_nhs_tour(self):
        """Execute the NHS theme interactive tour to verify sidebar and home menu navigation."""
        self.start_tour('/odoo', 'theme_nhs_tour', login='admin')

