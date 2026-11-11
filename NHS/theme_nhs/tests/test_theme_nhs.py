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

import os
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

from odoo.modules.module import get_manifest, get_module_path
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestThemeNhs(TransactionCase):
    """Test suite for the NHS Backend Theme module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module_name = 'theme_nhs'
        cls.module_path = get_module_path(cls.module_name)
        cls.manifest = get_manifest(cls.module_name)

    def test_01_module_installation_state(self):
        """Verify the module exists and is installed or installable."""
        module = self.env['ir.module.module'].search([('name', '=', self.module_name)])
        self.assertTrue(module.exists(), f"Module {self.module_name} should exist in ir.module.module")
        self.assertIn(
            module.state,
            ['installed', 'to install', 'to upgrade'],
            f"Module {self.module_name} should be installed or installable (current state: {module.state})",
        )
        self.assertNotEqual(module.state, 'uninstallable', "Module should not be in uninstallable state")
        self.assertTrue(self.manifest.get('installable'), "Module manifest should be marked as installable")
        self.assertTrue(module.application, "Module should be marked as an application")

    def test_02_manifest_dependencies(self):
        """Verify that necessary dependencies are configured in manifest."""
        depends = self.manifest.get('depends', [])
        self.assertIn('web', depends, "NHS Theme must depend on 'web'")
        self.assertIn('mail', depends, "NHS Theme must depend on 'mail'")

    def test_03_manifest_assets_exist(self):
        """Verify all static assets declared in __manifest__.py exist on the filesystem."""
        assets = self.manifest.get('assets', {})
        self.assertIn('web.assets_backend', assets, "Manifest should define web.assets_backend")
        self.assertIn('web.assets_frontend', assets, "Manifest should define web.assets_frontend")
        self.assertIn('point_of_sale._assets_pos', assets, "Manifest should define point_of_sale._assets_pos")

        for bundle_name, asset_list in assets.items():
            for asset_path in asset_list:
                if '*' in asset_path:
                    continue
                relative_path = asset_path
                if relative_path.startswith(f"{self.module_name}/"):
                    relative_path = relative_path[len(self.module_name) + 1:]
                full_path = os.path.join(self.module_path, relative_path)
                self.assertTrue(
                    os.path.exists(full_path),
                    f"Asset {asset_path} declared in bundle {bundle_name} does not exist at {full_path}",
                )
                self.assertGreater(
                    os.path.getsize(full_path),
                    0,
                    f"Asset {asset_path} is empty",
                )

    def test_04_xml_templates_syntax(self):
        """Verify all QWeb / Owl XML templates are well-formed XML."""
        xml_files = [
            'static/src/xml/menu_panels.xml',
            'static/src/xml/nav_bar_panel.xml',
            'static/src/xml/home_menus.xml',
            'static/src/xml/side_bar_panel.xml',
        ]
        for xml_rel_path in xml_files:
            xml_full_path = os.path.join(self.module_path, xml_rel_path)
            self.assertTrue(os.path.exists(xml_full_path), f"XML template missing: {xml_full_path}")
            with open(xml_full_path, 'rb') as f:
                content = f.read()
            try:
                parsed_xml = etree.fromstring(content)
                self.assertIsNotNone(parsed_xml, f"Failed to parse {xml_rel_path}")
            except etree.XMLSyntaxError as err:
                self.fail(f"XML Syntax Error in {xml_rel_path}: {err}")

    def test_05_inherited_templates_integrity(self):
        """Verify template structure and inheritance targets."""
        home_menu_path = os.path.join(self.module_path, 'static/src/xml/home_menus.xml')
        with open(home_menu_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('t-name="nhs_backend_theme.home_menus"', content)
            self.assertIn('class="app_container"', content)
            self.assertIn('class="app_list"', content)

        sidebar_path = os.path.join(self.module_path, 'static/src/xml/side_bar_panel.xml')
        with open(sidebar_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('t-inherit="web.NavBar"', content)
            self.assertIn('class="sidebar"', content)

        menu_panels_path = os.path.join(self.module_path, 'static/src/xml/menu_panels.xml')
        with open(menu_panels_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('t-inherit="web.NavBar.AppsMenu"', content)
            self.assertIn('data-hotkey="h"', content)
            self.assertIn('title="Home Menu"', content)

        nav_bar_path = os.path.join(self.module_path, 'static/src/xml/nav_bar_panel.xml')
        with open(nav_bar_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('t-inherit="web.NavBar"', content)
            self.assertIn('navbar navbar-expand-lg', content)

    def test_06_theme_images_and_icons_exist(self):
        """Verify that screenshots, icons, and referenced images exist."""
        # Check topbar left arrow SVG
        arrow_path = os.path.join(self.module_path, 'static/src/img/icon/topbar/left-arrow.svg')
        self.assertTrue(os.path.exists(arrow_path), f"Topbar arrow icon missing: {arrow_path}")

        # Check manifest images (banner, screenshot, icon)
        manifest_images = self.manifest.get('images', [])
        self.assertIn('static/description/icon.png', manifest_images, "Manifest images should include icon.png")
        self.assertIn('static/description/banner.jpg', manifest_images, "Manifest images should include banner.jpg")
        for img_rel_path in manifest_images:
            full_path = os.path.join(self.module_path, img_rel_path)
            self.assertTrue(
                os.path.exists(full_path),
                f"Referenced image/icon missing: {full_path}",
            )

    def test_07_load_menus_structure(self):
        """Verify that ir.ui.menu loads menus without throwing an error."""
        menus = self.env['ir.ui.menu'].load_menus(False)
        self.assertIsInstance(menus, dict, "load_menus should return a dictionary")
        self.assertIn('root', menus, "load_menus dictionary must have a 'root' entry")
        self.assertIn('children', menus['root'], "Root menu must contain 'children'")
