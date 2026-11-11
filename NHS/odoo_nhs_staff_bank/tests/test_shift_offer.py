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
class TestShiftOffer(NhsStaffBankCommon):
    """Test suite for nhs.shift.offer: creation validation, eligibility audit snapshot,
    accept/decline workflows, manager allocation mode, and cron expiration."""

    def test_offer_creation_shift_state_constraint(self):
        """Offers can only be created for open or partially_filled shifts."""
        draft_shift = self._create_shift(state='draft')
        member = self._create_member()

        with self.assertRaises(ValidationError):
            self.Offer.create({
                'shift_id': draft_shift.id,
                'member_id': member.id,
            })

    def test_offer_creation_overlapping_booking_constraint(self):
        """Cannot offer a shift to a member already booked on an overlapping shift."""
        shift_1 = self._create_shift()
        member = self._create_member()

        # Book member on shift_1
        self.Booking.create({
            'shift_id': shift_1.id,
            'member_id': member.id,
            'state': 'booked',
        })

        # Create shift_2 overlapping with shift_1
        shift_2 = self._create_shift(
            shift_start=shift_1.shift_start,
            shift_end=shift_1.shift_end,
        )

        with self.assertRaises(ValidationError):
            self.Offer.create({
                'shift_id': shift_2.id,
                'member_id': member.id,
            })

    def test_offer_snapshots_eligibility_at_creation(self):
        """Offer creation snapshots member eligibility status and reasons."""
        shift = self._create_shift()
        # Member with role/band match, area match, but no availability declared
        member = self._create_member()
        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        self.assertFalse(offer.eligible)
        self.assertIn('Not available', offer.eligibility_reasons)

        # Member with availability declared
        self._make_available(member, shift)
        offer_2 = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        self.assertTrue(offer_2.eligible)
        self.assertFalse(offer_2.eligibility_reasons)

    def test_offer_accept_first_come_mode(self):
        """In First-Come mode, accepting an offer automatically creates a booking."""
        self.company.nhs_bank_booking_mode = 'first_come'
        shift = self._create_shift(headcount=1)
        member = self._create_member()
        self._make_available(member, shift)

        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        self.assertEqual(offer.response, 'pending')

        offer.action_accept()
        self.assertEqual(offer.response, 'accepted')
        self.assertTrue(offer.responded_at)
        self.assertTrue(offer.booking_id)
        self.assertEqual(offer.booking_id.member_id, member)
        self.assertEqual(offer.booking_id.shift_id, shift)
        self.assertEqual(shift.state, 'filled')

        # Cannot accept an already responded offer
        with self.assertRaises(UserError):
            offer.action_accept()

    def test_offer_accept_manager_allocated_mode(self):
        """In Manager-Allocated mode, accepting an offer does not create a booking until allocated."""
        self.company.nhs_bank_booking_mode = 'manager_allocated'
        shift = self._create_shift(headcount=1)
        member = self._create_member()
        self._make_available(member, shift)

        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        offer.action_accept()
        self.assertEqual(offer.response, 'accepted')
        self.assertFalse(offer.booking_id)

        # Bank officer cannot allocate
        with self.assertRaises(UserError):
            offer.with_user(self.user_officer).action_allocate_booking()

        # Bank manager allocates
        offer.with_user(self.user_manager).action_allocate_booking()
        self.assertTrue(offer.booking_id)
        self.assertEqual(offer.booking_id.member_id, member)

        # Allocating again raises UserError
        with self.assertRaises(UserError):
            offer.with_user(self.user_manager).action_allocate_booking()

    def test_offer_decline_requires_reason(self):
        """Declining an offer strictly requires a documented reason."""
        shift = self._create_shift()
        member = self._create_member()
        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })

        # No reason -> error
        with self.assertRaises(UserError):
            offer.action_decline(reason=None)

        offer.action_decline(reason='Personal commitment')
        self.assertEqual(offer.response, 'declined')
        self.assertEqual(offer.decline_reason, 'Personal commitment')
        self.assertTrue(offer.responded_at)

    def test_offer_withdraw(self):
        """Withdrawing pending offers changes their status to withdrawn."""
        shift = self._create_shift()
        member = self._create_member()
        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })
        offer.action_withdraw()
        self.assertEqual(offer.response, 'withdrawn')

    def test_offer_cron_expire_offers(self):
        """Scheduled action auto-expires pending offers past their expiry datetime."""
        shift = self._create_shift()
        member = self._create_member()
        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
            'expiry_datetime': fields.Datetime.now() - timedelta(hours=1),
        })
        self.Offer._cron_expire_offers()
        offer.invalidate_recordset(['response', 'responded_at'])
        self.assertEqual(offer.response, 'expired')
        self.assertTrue(offer.responded_at)

