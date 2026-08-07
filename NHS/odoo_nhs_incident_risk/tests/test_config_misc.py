# -*- coding: utf-8 -*-
"""Configuration & supporting models: working-day maths, location/category
hierarchy depth limits, terminology packs, provider setup wizard, company token."""
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import NhsCommon


@tagged('post_install', '-at_install')
class TestConfigMisc(NhsCommon):

    def test_holiday_working_days_skip_weekends_and_holidays(self):
        """add_working_days skips weekends, and a bank holiday adds one more day."""
        Holiday = self.env['nhs.holiday']
        Holiday.search([]).unlink()
        from odoo import fields
        start = fields.Date.to_date('2026-06-01')  # Monday
        # 5 working days, no holidays -> Monday 8 Jun.
        self.assertEqual(Holiday.add_working_days(start, 5),
                         fields.Date.to_date('2026-06-08'))
        # Introduce a holiday inside the window -> result shifts by one day.
        Holiday.create({'name': 'Test Day', 'date': fields.Date.to_date('2026-06-03')})
        self.assertEqual(Holiday.add_working_days(start, 5),
                         fields.Date.to_date('2026-06-09'))

    def test_location_hierarchy_and_depth_limit(self):
        """Locations allow 3 levels; a 4th raises, and complete_name concatenates."""
        site = self.env['nhs.location'].create({
            'name': 'Main Hospital', 'location_type': 'site',
            'company_id': self.company.id})
        unit = self.env['nhs.location'].create({
            'name': 'Ward 7', 'location_type': 'unit', 'parent_id': site.id,
            'company_id': self.company.id})
        room = self.env['nhs.location'].create({
            'name': 'Bay 3', 'location_type': 'room', 'parent_id': unit.id,
            'company_id': self.company.id})
        self.assertEqual(room.complete_name, 'Main Hospital / Ward 7 / Bay 3')
        with self.assertRaises(ValidationError):
            self.env['nhs.location'].create({
                'name': 'Too deep', 'location_type': 'room', 'parent_id': room.id,
                'company_id': self.company.id})

    def test_category_depth_limit(self):
        """Incident categories allow 2 levels; a 3rd raises."""
        top = self.env['nhs.incident.category'].create({'name': 'Clinical'})
        sub = self.env['nhs.incident.category'].create(
            {'name': 'Medication', 'parent_id': top.id})
        with self.assertRaises(ValidationError):
            self.env['nhs.incident.category'].create(
                {'name': 'Too deep', 'parent_id': sub.id})

    def test_terminology_lookup(self):
        """t() returns the provider-specific label, or a title-cased fallback."""
        Term = self.env['nhs.terminology']
        Term.create({'provider_type': 'nhs_trust', 'logical_key': 'person_affected',
                     'label': 'Patient'})
        self.assertEqual(Term.t('person_affected', 'nhs_trust'), 'Patient')
        self.assertEqual(Term.t('care_recipient', 'nhs_trust'), 'Care Recipient')

    def test_provider_setup_wizard_applies(self):
        """The provider setup wizard sets the company provider type and a form token."""
        wiz = self.env['nhs.provider.setup.wizard'].create({'provider_type': 'care_home'})
        wiz.action_apply()
        self.assertEqual(self.company.provider_type, 'care_home')
        self.assertTrue(self.company.public_form_token)

    def test_public_form_token_is_stable(self):
        """_get_public_form_token generates once and returns the same value thereafter."""
        self.company.public_form_token = False
        token1 = self.company._get_public_form_token()
        token2 = self.company._get_public_form_token()
        self.assertTrue(token1)
        self.assertEqual(token1, token2)
