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
class TestShiftBooking(NhsStaffBankCommon):
    """Test suite for nhs.shift.booking: sequence, compliance gate enforcement,
    payable amount calculation, working time breach detection, state actions,
    and deletion prevention."""

    def test_booking_sequence_and_defaults(self):
        """Booking gets sequenced reference and defaults times from shift."""
        shift = self._create_shift()
        member = self._create_member()

        booking = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        self.assertTrue(booking.name)
        self.assertTrue(booking.name.startswith('BKG/'))
        self.assertEqual(booking.shift_start, shift.shift_start)
        self.assertEqual(booking.shift_end, shift.shift_end)

    def test_booking_time_constraints(self):
        """Rejects end time earlier than or equal to start time for booked and actual times."""
        shift = self._create_shift()
        member = self._create_member()

        now = fields.Datetime.now()
        with self.assertRaises(ValidationError):
            self.Booking.create({
                'shift_id': shift.id,
                'member_id': member.id,
                'shift_start': now + timedelta(hours=8),
                'shift_end': now + timedelta(hours=4),
            })

        booking = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        with self.assertRaises(ValidationError):
            booking.write({
                'actual_start': now + timedelta(hours=8),
                'actual_end': now + timedelta(hours=4),
            })

    def test_booking_compliance_gate_hard_policy(self):
        """With hard compliance gate policy, non-compliant member cannot be booked."""
        self.company.nhs_bank_gate_policy = 'hard'
        shift = self._create_shift()
        non_compliant_member = self._create_member(checks_confirmed=False)

        with self.assertRaises(UserError):
            self.Booking.create({
                'shift_id': shift.id,
                'member_id': non_compliant_member.id,
            })

    def test_booking_compliance_gate_soft_policy(self):
        """With soft compliance gate policy, non-compliant member can be booked with audit snapshot."""
        self.company.nhs_bank_gate_policy = 'soft'
        shift = self._create_shift()
        non_compliant_member = self._create_member(checks_confirmed=False)

        booking = self.Booking.create({
            'shift_id': shift.id,
            'member_id': non_compliant_member.id,
        })
        self.assertFalse(booking.compliant_at_booking)

        compliant_member = self._create_member(checks_confirmed=True, manual_compliance_flag=True)
        booking_2 = self.Booking.create({
            'shift_id': shift.id,
            'member_id': compliant_member.id,
        })
        self.assertTrue(booking_2.compliant_at_booking)

    def test_booking_payable_amount_calculation(self):
        """Payable amount computes hours * hourly rate (+ enhancement), or honors rate_override."""
        # £20/hr + 50% enhancement = £30/hr
        rate = self._create_rate(hourly_rate=20.0, enhancement_pct=50.0)
        shift = self._create_shift()
        member = self._create_member()

        start = fields.Datetime.now() + timedelta(days=2, hours=8)
        end = start + timedelta(hours=10)

        booking = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member.id,
            'shift_start': start,
            'shift_end': end,
            'rate_id': rate.id,
        })
        # 10 hours * £30 = £300
        self.assertEqual(booking.payable_amount, 300.0)

        # Rate override takes precedence
        booking.write({
            'rate_override': 350.0,
            'rate_override_reason': 'Manager discretionary uplift',
        })
        self.assertEqual(booking.payable_amount, 350.0)

    def test_booking_working_time_breach_detection(self):
        """Flags when this booking pushes member past weekly hours limit."""
        member = self._create_member(weekly_hours_limit=48.0, substantive_weekly_hours=40.0)
        shift = self._create_shift()

        start = fields.Datetime.now() + timedelta(days=2, hours=8)
        end = start + timedelta(hours=10)

        booking = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member.id,
            'shift_start': start,
            'shift_end': end,
        })
        # 40 substantive + 10 hours = 50 > 48
        self.assertTrue(booking.working_time_breach)

    def test_booking_action_lifecycle(self):
        """Booking state transitions: confirm worked, no show, authorise, cancel."""
        shift = self._create_shift()
        member = self._create_member()
        booking = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        self.assertEqual(booking.state, 'booked')

        # Worked
        booking.action_confirm_worked()
        self.assertEqual(booking.state, 'worked')
        self.assertEqual(booking.actual_start, booking.shift_start)
        self.assertEqual(booking.actual_end, booking.shift_end)

        # Authorise
        booking.action_authorise()
        self.assertEqual(booking.authorised_by_id, self.env.user)
        self.assertTrue(booking.authorised_at)

        # No show
        booking.action_no_show()
        self.assertEqual(booking.state, 'no_show')

        # Cancel
        booking.action_cancel(reason='Shift unneeded')
        self.assertEqual(booking.state, 'cancelled')
        self.assertEqual(booking.cancel_reason, 'Shift unneeded')

    def test_booking_unlink_blocked(self):
        """Hard deletion of bookings is blocked to preserve audit trail."""
        shift = self._create_shift()
        member = self._create_member()
        booking = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        with self.assertRaises(UserError):
            booking.unlink()

