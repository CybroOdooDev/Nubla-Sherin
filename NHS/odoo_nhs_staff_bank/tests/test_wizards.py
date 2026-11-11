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
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import NhsStaffBankCommon


@tagged('post_install', '-at_install')
class TestStaffBankWizards(NhsStaffBankCommon):
    """Test suite for staff bank wizards: offer wizard, decline wizard,
    bulk recurring shift creation, agency escalation, and report wizards."""

    def test_offer_shift_wizard_default_get_and_broadcast(self):
        """Offer shift wizard pre-populates candidates and sends broadcast offers."""
        shift = self._create_shift()
        member_eligible = self._create_member(name='Candidate A', email='ca@nhs.test')
        self._make_available(member_eligible, shift)

        # Ineligible member (mismatched band)
        member_ineligible = self._create_member(
            name='Candidate B', email='cb@nhs.test', band_id=self.band_6.id)

        wizard_model = self.env['nhs.offer.shift.wizard'].with_context(default_shift_id=shift.id)
        defaults = wizard_model.default_get(['shift_id', 'broadcast', 'line_ids'])
        wizard = wizard_model.create(defaults)

        # Candidate A should be eligible and selected by default
        line_a = wizard.line_ids.filtered(lambda l: l.member_id == member_eligible)
        self.assertTrue(line_a.eligible)
        self.assertTrue(line_a.selected)

        # Candidate B should not be eligible
        line_b = wizard.line_ids.filtered(lambda l: l.member_id == member_ineligible)
        self.assertFalse(line_b.eligible)

        # Send broadcast offers
        wizard.action_send_offers()
        offer = self.Offer.search([('shift_id', '=', shift.id), ('member_id', '=', member_eligible.id)])
        self.assertEqual(len(offer), 1)
        self.assertEqual(offer.response, 'pending')

    def test_offer_shift_wizard_targeted_mode_validation(self):
        """Targeted offer mode raises error if attempting to offer to an ineligible candidate."""
        shift = self._create_shift()
        member_ineligible = self._create_member(band_id=self.band_6.id)

        wizard = self.env['nhs.offer.shift.wizard'].create({
            'shift_id': shift.id,
            'broadcast': False,
            'line_ids': [(0, 0, {
                'member_id': member_ineligible.id,
                'eligible': False,
                'selected': True,
            })],
        })
        with self.assertRaises(UserError):
            wizard.action_send_offers()

    def test_offer_decline_wizard(self):
        """Decline offer wizard records the required decline reason and declines the offer."""
        shift = self._create_shift()
        member = self._create_member()
        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        wizard = self.env['nhs.offer.decline.wizard'].create({
            'offer_id': offer.id,
            'reason': 'Childcare obligations',
        })
        wizard.action_confirm()
        self.assertEqual(offer.response, 'declined')
        self.assertEqual(offer.decline_reason, 'Childcare obligations')

    def test_bulk_shift_wizard_creation(self):
        """Bulk shift wizard creates open shifts for chosen weekdays and handles overnight shifts."""
        today = fields.Date.today()
        # Set future range 7 days to 14 days out
        date_from = today + timedelta(days=7)
        date_to = today + timedelta(days=13)

        wizard = self.env['nhs.bulk.shift.wizard'].create({
            'org_unit_id': self.org_unit_acute.id,
            'band_id': self.band_5.id,
            'role_id': self.role_nurse.id,
            'shift_type_id': self.shift_type_night.id,
            'headcount': 1,
            'date_from': date_from,
            'date_to': date_to,
            'start_time': 20.0,  # 20:00
            'end_time': 8.0,    # 08:00 next day (overnight)
            'weekday_ids': [(6, 0, self.Weekday.search([]).ids)],
        })
        action = wizard.action_create_shifts()
        created_shift_ids = action['domain'][0][2]
        self.assertEqual(len(created_shift_ids), 7)

        # Check an overnight shift
        first_shift = self.Shift.browse(created_shift_ids[0])
        self.assertEqual(first_shift.state, 'open')
        self.assertEqual(first_shift.shift_end.date(), first_shift.shift_start.date() + timedelta(days=1))

    def test_bulk_shift_wizard_validations(self):
        """Bulk shift wizard validates date range and weekday selection."""
        today = fields.Date.today()
        # date_to before date_from
        with self.assertRaises(UserError):
            self.env['nhs.bulk.shift.wizard'].create({
                'org_unit_id': self.org_unit_acute.id,
                'date_from': today + timedelta(days=5),
                'date_to': today + timedelta(days=2),
                'weekday_ids': [(6, 0, self.Weekday.search([]).ids)],
            }).action_create_shifts()

        # No weekdays
        with self.assertRaises(UserError):
            self.env['nhs.bulk.shift.wizard'].create({
                'org_unit_id': self.org_unit_acute.id,
                'date_from': today + timedelta(days=2),
                'date_to': today + timedelta(days=5),
                'weekday_ids': [(5, 0, 0)],
            }).action_create_shifts()

    def test_escalate_agency_wizard(self):
        """Agency escalation captures agency, cost and reason, and withdraws pending bank offers."""
        shift = self._create_shift(state='open')
        member = self._create_member()
        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
            'response': 'pending',
        })

        wizard = self.env['nhs.escalate.agency.wizard'].create({
            'shift_id': shift.id,
            'agency_name': 'Acme Locums',
            'agency_cost': 550.0,
            'reason': 'No bank cover available',
        })
        wizard.action_confirm()

        self.assertEqual(shift.state, 'to_agency')
        self.assertEqual(shift.agency_name, 'Acme Locums')
        self.assertEqual(shift.agency_cost, 550.0)
        self.assertEqual(shift.agency_escalation_reason, 'No bank cover available')
        self.assertEqual(shift.agency_escalated_by_id, self.env.user)
        self.assertTrue(shift.agency_escalated_at)
        self.assertEqual(offer.response, 'withdrawn')

    def test_bank_report_wizard_computations_and_actions(self):
        """Report wizard computes fill rate data and spend data, and returns report actions."""
        today = fields.Date.today()
        wizard = self.env['nhs.bank.report.wizard'].create({
            'date_from': today - timedelta(days=30),
            'date_to': today + timedelta(days=30),
            'org_unit_id': self.org_unit_acute.id,
        })

        # Test fill rate data
        fill_data = wizard.get_fill_rate_data()
        self.assertIn('total_resolved', fill_data)
        self.assertIn('fill_rate', fill_data)
        self.assertIn('bank_spend', fill_data)
        self.assertIn('agency_spend', fill_data)

        # Test spend data
        spend_data = wizard.get_spend_data()
        self.assertIn('band_rows', spend_data)
        self.assertIn('total_bank_cost', spend_data)
        self.assertIn('total_agency_cost', spend_data)

        # Test report trigger actions
        fill_action = wizard.action_print_fill_rate()
        self.assertEqual(fill_action['report_name'], 'odoo_nhs_staff_bank.report_nhs_fill_rate')

        spend_action = wizard.action_print_spend()
        self.assertEqual(spend_action['report_name'], 'odoo_nhs_staff_bank.report_nhs_bank_spend')

