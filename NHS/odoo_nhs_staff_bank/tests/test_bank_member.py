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
import psycopg2

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import NhsStaffBankCommon


@tagged('post_install', '-at_install')
class TestBankMember(NhsStaffBankCommon):
    """Test suite for nhs.bank.member lifecycle, compliance, availability,
    and portal-user synchronization."""

    def test_member_reference_sequenced(self):
        """A new member receives a sequenced bank reference."""
        member = self._create_member(name='John Sequence Test')
        self.assertTrue(member.reference)
        self.assertNotEqual(member.reference, 'New')
        self.assertTrue(member.reference.startswith('BNK/'))

    def test_member_state_transitions(self):
        """Member state changes via action methods."""
        member = self._create_member(state='draft')
        self.assertEqual(member.state, 'draft')

        member.action_activate()
        self.assertEqual(member.state, 'active')

        member.action_suspend()
        self.assertEqual(member.state, 'suspended')

        member.action_deactivate()
        self.assertEqual(member.state, 'inactive')

    def test_member_user_sync_group(self):
        """Linking a user to a member automatically grants group_nhs_bank_member."""
        test_user = self.env['res.users'].create({
            'name': 'Sync User Test',
            'login': 'sync_user_test',
            'email': 'sync@nhs.test',
            'group_ids': [(6, 0, [self.group_user.id])],
        })
        self.assertNotIn(self.group_member, test_user.group_ids)

        member = self._create_member(user_id=test_user.id)
        self.assertIn(self.group_member, member.user_id.group_ids)

    def test_member_unique_user_constraint(self):
        """A portal user cannot be linked to more than one bank member."""
        self._create_member(user_id=self.user_portal_member.id, email='member1@nhs.test')
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(psycopg2.IntegrityError):
                with self.cr.savepoint():
                    self._create_member(
                        name='Duplicate User Link',
                        user_id=self.user_portal_member.id,
                        email='member2@nhs.test'
                    )

    def test_member_compliance_status_computation(self):
        """Compliance status reflects active status, checks, and manual fallback flags."""
        # Inactive member is always 'unknown'
        member = self._create_member(state='draft', checks_confirmed=True, manual_compliance_flag=True)
        self.assertEqual(member.compliance_status, 'unknown')
        self.assertIn('not active', member.compliance_reason)

        # Active without checks confirmed
        member.write({'state': 'active', 'checks_confirmed': False})
        self.assertEqual(member.compliance_status, 'non_compliant')
        self.assertIn('Employment checks', member.compliance_reason)

        # Active with checks confirmed but manual flag off
        member.write({
            'checks_confirmed': True,
            'manual_compliance_flag': False,
            'manual_compliance_note': 'Training expired',
        })
        self.assertEqual(member.compliance_status, 'non_compliant')
        self.assertEqual(member.compliance_reason, 'Training expired')

        # Fully compliant
        member.write({'manual_compliance_flag': True})
        self.assertEqual(member.compliance_status, 'compliant')
        self.assertFalse(member.compliance_reason)

    def test_member_availability_check_non_recurring(self):
        """_is_available_for validates covering windows and blackout overlaps."""
        member = self._create_member()
        now = fields.Datetime.now()
        shift_start = now + timedelta(days=2, hours=8)
        shift_end = shift_start + timedelta(hours=8)

        # No availability record -> False
        self.assertFalse(member._is_available_for(shift_start, shift_end))

        # Availability covering entire window -> True
        avail = self._create_availability(
            member,
            date_from=shift_start - timedelta(hours=1),
            date_to=shift_end + timedelta(hours=1),
            availability_type='available',
        )
        self.assertTrue(member._is_available_for(shift_start, shift_end))

        # Overlapping blackout window takes precedence -> False
        self._create_availability(
            member,
            date_from=shift_start + timedelta(hours=2),
            date_to=shift_end + timedelta(hours=2),
            availability_type='unavailable',
        )
        self.assertFalse(member._is_available_for(shift_start, shift_end))

    def test_member_availability_check_recurring(self):
        """_is_available_for handles recurring availability rules."""
        member = self._create_member()
        now = fields.Datetime.now()
        shift_start = now + timedelta(days=3, hours=8)
        shift_end = shift_start + timedelta(hours=8)
        target_weekday = str(shift_start.weekday())

        # Recurring matching day
        self._create_availability(
            member,
            date_from=shift_start - timedelta(days=1),
            date_to=shift_end + timedelta(days=1),
            availability_type='available',
            recurring=True,
            weekday=target_weekday,
            recurrence_end_date=(shift_start + timedelta(days=30)).date(),
        )
        self.assertTrue(member._is_available_for(shift_start, shift_end))

        # Recurring but past recurrence_end_date
        past_end_start = shift_start + timedelta(days=40)
        past_end_end = past_end_start + timedelta(hours=8)
        self.assertFalse(member._is_available_for(past_end_start, past_end_end))

    def test_member_working_time_calculations(self):
        """Member booked hours sum and working time breach check."""
        member = self._create_member(weekly_hours_limit=48.0, substantive_weekly_hours=37.5)
        now = fields.Datetime.now()
        shift = self._create_shift()

        # Add booked booking for 8 hours
        b_start = now + timedelta(days=1, hours=8)
        b_end = b_start + timedelta(hours=8)
        self.Booking.create({
            'shift_id': shift.id,
            'member_id': member.id,
            'shift_start': b_start,
            'shift_end': b_end,
            'state': 'booked',
        })

        booked_hours = member.get_booked_hours(now, now + timedelta(days=5))
        self.assertAlmostEqual(booked_hours, 8.0)

        # 37.5 substantive + 8 booked + 2 additional = 47.5 <= 48.0 -> No breach
        self.assertFalse(member.check_working_time_breach(
            additional_hours=2.0, date_from=now, date_to=now + timedelta(days=5)))

        # 37.5 + 8 + 3 = 48.5 > 48.0 -> Breach
        self.assertTrue(member.check_working_time_breach(
            additional_hours=3.0, date_from=now, date_to=now + timedelta(days=5)))

    def test_member_action_view_buttons(self):
        """Action view methods return correct window actions."""
        member = self._create_member()
        avail_action = member.action_view_availability()
        self.assertEqual(avail_action['res_model'], 'nhs.member.availability')
        self.assertEqual(avail_action['context']['default_member_id'], member.id)

        offers_action = member.action_view_offers()
        self.assertEqual(offers_action['res_model'], 'nhs.shift.offer')
        self.assertEqual(offers_action['context']['default_member_id'], member.id)

        bookings_action = member.action_view_bookings()
        self.assertEqual(bookings_action['res_model'], 'nhs.shift.booking')
        self.assertEqual(bookings_action['context']['default_member_id'], member.id)

    def test_member_action_create_portal_user_validations(self):
        """Validates prerequisites when manually creating portal users."""
        member = self._create_member(email=False)
        with self.assertRaises(UserError):
            member.action_create_portal_user()

        member.write({'email': 'new_portal@nhs.test', 'user_id': self.user_portal_member.id})
        with self.assertRaises(UserError):
            member.action_create_portal_user()

    def test_member_cron_recompute_compliance(self):
        """The cron action recomputes compliance for all active bank members."""
        member = self._create_member(state='active', checks_confirmed=False)
        self.assertEqual(member.compliance_status, 'non_compliant')

        # Fix condition directly in DB or write without compute trigger
        self.env.cr.execute(
            "UPDATE nhs_bank_member SET checks_confirmed = TRUE WHERE id = %s",
            (member.id,)
        )
        self.Member._cron_recompute_compliance()
        member.invalidate_recordset(['compliance_status', 'checks_confirmed'])
        self.assertEqual(member.compliance_status, 'compliant')

