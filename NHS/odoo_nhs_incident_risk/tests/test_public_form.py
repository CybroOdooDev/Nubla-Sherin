# -*- coding: utf-8 -*-
"""HttpCase coverage for the public (auth='public') incident report controller:
token gating, form render, and an end-to-end anonymous submission."""
import re

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestPublicForm(HttpCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.write({
            'public_form_enabled': True,
            'anonymous_reporting_allowed': True,
            'provider_type': 'nhs_trust',
        })
        self.token = self.company._get_public_form_token()
        self.location = self.env['nhs.location'].create({
            'name': 'Public Ward', 'location_type': 'unit',
            'company_id': self.company.id})
        self.category = self.env['nhs.incident.category'].create(
            {'name': 'Public Category'})

    def test_form_renders_for_valid_token(self):
        """The token URL renders the public report form with a CSRF token."""
        resp = self.url_open('/incident/report/%s' % self.token)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('csrf_token', resp.text)

    def test_unknown_token_returns_404(self):
        """An unknown/forged token must not expose any form."""
        resp = self.url_open('/incident/report/deadbeefdeadbeef0000')
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_submission_creates_incident(self):
        """A valid public POST creates an incident tagged reported_via=public_form."""
        form = self.url_open('/incident/report/%s' % self.token)
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', form.text)
        self.assertTrue(match, 'CSRF token missing from public form')
        desc = 'Public submission test - wet floor near reception.'
        resp = self.url_open('/incident/report/%s/submit' % self.token, data={
            'csrf_token': match.group(1),
            'incident_kind': 'incident',
            'occurred_at': '2026-05-01T09:30',
            'location_id': str(self.location.id),
            'category_id': str(self.category.id),
            'description': desc,
            'is_anonymous': '1',
        })
        self.assertEqual(resp.status_code, 200)
        inc = self.env['nhs.incident'].search([('description', '=', desc)], limit=1)
        self.assertTrue(inc, 'public submission should create an incident')
        self.assertEqual(inc.reported_via, 'public_form')
        self.assertTrue(inc.is_anonymous)
