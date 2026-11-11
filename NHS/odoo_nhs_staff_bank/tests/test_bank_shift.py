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
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import NhsStaffBankCommon


@tagged('post_install', '-at_install')
class TestBankShift(NhsStaffBankCommon):
    """Test suite for nhs.bank.shift: constraints, rate lookup, state transitions,
    cancellations, dashboard metrics, and cron jobs."""

    def test_shift_sequence_and_computed_name(self):
        """Shifts get a sequenced reference, human-readable name, and formatted time range."""
        shift = self._create_shift()
        self.assertTrue(shift.reference)
        self.assertNotEqual(shift.reference, 'New')
        self.assertTrue(shift.reference.startswith('SFT/'))
        self.assertIn('Acute Ward', shift.name)
        self.assertTrue(shift.time_range)
        self.assertIn('-', shift.time_range)

    def test_shift_time_constraints(self):
        """Shifts reject start in the past, or end before or equal to start."""
        now = fields.Datetime.now()
        # Shift start in the past
        with self.assertRaises(ValidationError):
            self._create_shift(
                shift_start=now - timedelta(days=1),
                shift_end=now + timedelta(hours=2)
            )

        # Shift end before start
        with self.assertRaises(ValidationError):
            self._create_shift(
                shift_start=now + timedelta(days=2),
                shift_end=now + timedelta(days=2) - timedelta(hours=1)
            )

        # Shift end equal to start
        with self.assertRaises(ValidationError):
            self._create_shift(
                shift_start=now + timedelta(days=2),
                shift_end=now + timedelta(days=2)
            )

    def test_shift_headcount_constraint(self):
        """Headcount must be at least 1."""
        with self.assertRaises(ValidationError):
            self._create_shift(headcount=0)

    def test_shift_estimated_cost_computation(self):
        """Estimated cost reflects applicable rate card or flags rate_found=False."""
        # Create rate for Band 5, Nurse, Day: £25/hr
        self._create_rate(hourly_rate=25.0, enhancement_pct=0.0)

        # 8 hour shift
        start = fields.Datetime.now() + timedelta(days=2, hours=8)
        end = start + timedelta(hours=8)
        shift = self._create_shift(shift_start=start, shift_end=end, headcount=2)

        self.assertTrue(shift.rate_found)
        # 8 hours * £25 * 2 headcount = £400
        self.assertEqual(shift.estimated_cost, 400.0)

        # Shift with no rate card
        unmatched_shift = self._create_shift(
            band_id=self.band_6.id,
            shift_start=start,
            shift_end=end,
        )
        self.assertFalse(unmatched_shift.rate_found)
        self.assertEqual(unmatched_shift.estimated_cost, 0.0)

    def test_shift_state_lifecycle_and_filled_count(self):
        """Shift state transitions according to confirmed bookings vs headcount."""
        shift = self._create_shift(state='draft', headcount=2)
        self.assertEqual(shift.state, 'draft')

        shift.action_open()
        self.assertEqual(shift.state, 'open')

        member_1 = self._create_member(name='Nurse One', email='n1@nhs.test')
        member_2 = self._create_member(name='Nurse Two', email='n2@nhs.test')

        # 1 confirmed booking out of 2 headcount
        b1 = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member_1.id,
            'state': 'booked',
        })
        shift.invalidate_recordset(['filled_count', 'state', 'filled_member_names'])
        self.assertEqual(shift.filled_count, 1)
        self.assertEqual(shift.state, 'partially_filled')
        self.assertIn('Nurse One', shift.filled_member_names)

        # 2nd booking -> fully filled
        b2 = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member_2.id,
            'state': 'booked',
        })
        shift.invalidate_recordset(['filled_count', 'state', 'filled_member_names'])
        self.assertEqual(shift.filled_count, 2)
        self.assertEqual(shift.state, 'filled')
        self.assertIn('Nurse One', shift.filled_member_names)
        self.assertIn('Nurse Two', shift.filled_member_names)

        # Cancelling a booking drops it back to partially_filled
        b2.action_cancel()
        shift.invalidate_recordset(['filled_count', 'state'])
        self.assertEqual(shift.filled_count, 1)
        self.assertEqual(shift.state, 'partially_filled')

    def test_shift_action_cancel_withdraws_pending_offers(self):
        """Cancelling a shift marks it cancelled and withdraws pending offers."""
        shift = self._create_shift(state='open')
        member = self._create_member()
        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
            'response': 'pending',
        })

        shift.action_cancel()
        self.assertEqual(shift.state, 'cancelled')
        self.assertEqual(offer.response, 'withdrawn')

    def test_shift_action_reset_open_and_agency_filled_lock(self):
        """A cancelled shift can be reopened, but a confirmed agency shift cannot."""
        shift = self._create_shift(state='cancelled')
        shift.action_reset_open()
        self.assertEqual(shift.state, 'open')

        # Escalate to agency
        shift.write({'state': 'to_agency'})
        shift.action_confirm_agency_filled()
        self.assertEqual(shift.state, 'agency_filled')
        self.assertTrue(shift.agency_confirmed)

        # Agency-filled shift cannot be reopened
        with self.assertRaises(UserError):
            shift.action_reset_open()

    def test_shift_cron_expire_stale_shifts(self):
        """Scheduled action marks stale open shifts past shift_end as expired."""
        shift = self._create_shift(state='open')
        past_start = fields.Datetime.now() - timedelta(days=2)
        past_end = fields.Datetime.now() - timedelta(days=1)

        # Direct SQL bypass of @api.constrains past check to simulate time elapsed
        self.cr.execute(
            "UPDATE nhs_bank_shift SET shift_start = %s, shift_end = %s WHERE id = %s",
            (past_start, past_end, shift.id)
        )
        shift.invalidate_recordset(['shift_start', 'shift_end', 'state'])

        self.Shift._cron_expire_stale_shifts()
        shift.invalidate_recordset(['state'])
        self.assertEqual(shift.state, 'expired')

    def test_shift_get_bank_dashboard_data(self):
        """Bank dashboard helper aggregates metrics and KPI calculations correctly."""
        rate = self._create_rate(hourly_rate=20.0)
        shift = self._create_shift(state='open')
        member = self._create_member()

        # Add a worked booking
        booking = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member.id,
            'rate_id': rate.id,
            'state': 'worked',
            'actual_start': shift.shift_start,
            'actual_end': shift.shift_end,
        })

        # Add an agency shift
        self._create_shift(
            state='to_agency',
            agency_name='Pulse Healthcare',
            agency_cost=450.0,
        )

        data = self.Shift.get_bank_dashboard_data()
        self.assertIn('fill_rate', data)
        self.assertIn('open_count', data)
        self.assertIn('bank_spend', data)
        self.assertIn('agency_spend', data)
        self.assertIn('cost_avoidance', data)
        self.assertIn('hotspots', data)
        self.assertGreaterEqual(data['agency_spend'], 450.0)

