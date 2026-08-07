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
import re

from odoo.tests.common import HttpCase, tagged

TOKEN = 'unit-test-token-abc123'


@tagged('post_install', '-at_install')
class TestPublicComplaintController(HttpCase):
    """Public /complaint/submit/<token> portal controller."""

    def setUp(self):
        """Ensure a root complaint subject exists so the controller's fallback lookup always succeeds."""
        super().setUp()
        self.IrParam = self.env['ir.config_parameter'].sudo()
        # Ensure a root subject exists for the controller's fallback lookup.
        self.subject = self.env.ref(
            'odoo_nhs_complaints.subject_clinical_treatment', raise_if_not_found=False)
        if not self.subject:
            self.subject = self.env['nhs.complaint.subject'].create(
                {'name': 'General', 'ko41a_code': 'GEN'})

    def _enable_form(self):
        """Enable the public complaint form and set the expected access token."""
        self.IrParam.set_param('odoo_nhs_complaints.public_form_enabled', 'True')
        self.IrParam.set_param('odoo_nhs_complaints.public_form_token', TOKEN)

    def test_form_disabled_returns_404(self):
        """With the public form disabled, the route is not found."""
        self.IrParam.set_param('odoo_nhs_complaints.public_form_enabled', 'False')
        self.IrParam.set_param('odoo_nhs_complaints.public_form_token', TOKEN)
        resp = self.url_open('/complaint/submit/%s' % TOKEN)
        self.assertEqual(resp.status_code, 404)

    def test_wrong_token_returns_404(self):
        """An incorrect token is rejected even when the form is enabled."""
        self._enable_form()
        resp = self.url_open('/complaint/submit/wrong-token')
        self.assertEqual(resp.status_code, 404)

    def test_form_renders_when_enabled(self):
        """The public form renders (HTTP 200) when enabled with the right token."""
        self._enable_form()
        resp = self.url_open('/complaint/submit/%s' % TOKEN)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Submit a Complaint', resp.text)

    def test_public_submission_creates_complaint(self):
        """A valid POST creates a website-sourced nhs.complaint record."""
        self._enable_form()
        url = '/complaint/submit/%s' % TOKEN
        page = self.url_open(url)
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.text)
        self.assertTrue(match, 'CSRF token must be present in the public form.')
        csrf = match.group(1)

        before = self.env['nhs.complaint'].search_count(
            [('received_via', '=', 'website')])
        resp = self.url_open(url, data={
            'csrf_token': csrf,
            'record_type': 'pals',
            'subject_summary': 'Long wait in A&E',
            'description': 'Waited nine hours to be seen.',
            'complainant_name': 'Public Submitter',
            'complainant_email': 'public@submitter.test',
        })
        self.assertEqual(resp.status_code, 200)
        after = self.env['nhs.complaint'].search([('received_via', '=', 'website')])
        self.assertEqual(len(after) - before, 1,
                         'Exactly one website complaint should be created.')
        complaint = after.sorted('id')[-1]
        self.assertEqual(complaint.subject_summary, 'Long wait in A&E')
        self.assertTrue(complaint.complainant_id,
                        'A complainant record should be created for a named submission.')

    def test_missing_required_fields_no_record(self):
        """A POST missing summary/description re-renders the form without creating."""
        self._enable_form()
        url = '/complaint/submit/%s' % TOKEN
        page = self.url_open(url)
        csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.text).group(1)
        before = self.env['nhs.complaint'].search_count(
            [('received_via', '=', 'website')])
        resp = self.url_open(url, data={
            'csrf_token': csrf,
            'record_type': 'pals',
            'subject_summary': '',
            'description': '',
        })
        self.assertEqual(resp.status_code, 200)
        after = self.env['nhs.complaint'].search_count(
            [('received_via', '=', 'website')])
        self.assertEqual(after, before, 'No record should be created on invalid input.')
