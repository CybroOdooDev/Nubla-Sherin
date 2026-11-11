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
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytz

from odoo import fields
from odoo.tests.common import tagged

from .common import NhsStaffBankCommon
from ..controllers.portal import NhsStaffBankPortal


@tagged('post_install', '-at_install')
class TestPortalController(NhsStaffBankCommon):
    """Test suite for NhsStaffBankPortal controller endpoints, helpers,
    and self-service workflows."""

    def setUp(self):
        super().setUp()
        self.controller = NhsStaffBankPortal()

    def test_parse_portal_datetime_helper(self):
        """_parse_portal_datetime converts HTML input to naive UTC datetime."""
        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_user = MagicMock()
            mock_user.tz = 'Europe/London'
            mock_req.env.user = mock_user

            # Valid string in London summer time (UTC+1)
            parsed = self.controller._parse_portal_datetime('2026-07-15T14:30')
            self.assertEqual(parsed, datetime(2026, 7, 15, 13, 30))

            # Malformed string
            self.assertFalse(self.controller._parse_portal_datetime('invalid-datetime'))

            # None or empty
            self.assertFalse(self.controller._parse_portal_datetime(''))
            self.assertFalse(self.controller._parse_portal_datetime(None))

    def test_local_now_str_helper(self):
        """_local_now_str returns valid YYYY-MM-DDTHH:MM format string."""
        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_user = MagicMock()
            mock_user.tz = 'UTC'
            mock_req.env.user = mock_user

            now_str = self.controller._local_now_str()
            self.assertTrue(now_str)
            # Should parse back without error
            self.assertTrue(datetime.strptime(now_str, '%Y-%m-%dT%H:%M'))

    def test_prepare_home_portal_values(self):
        """_prepare_home_portal_values injects bank_shift_count for bank members."""
        member = self._create_member(user_id=self.user_portal_member.id)
        shift = self._create_shift()
        self._make_available(member, shift)

        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_req.env = self.env(user=self.user_portal_member)

            values = self.controller._prepare_home_portal_values({})
            self.assertIn('bank_shift_count', values)
            self.assertEqual(values['bank_shift_count'], 1)

            # For user without bank member
            mock_req.env = self.env(user=self.user_no_access)
            values_no_member = self.controller._prepare_home_portal_values({})
            self.assertIsNone(values_no_member['bank_shift_count'])

    def test_portal_bank_home_not_member(self):
        """Users without a linked bank member receive the not-member template."""
        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_req.env = self.env(user=self.user_no_access)
            mock_req.render = MagicMock(return_value='rendered_not_member')

            res = self.controller.portal_bank_home()
            mock_req.render.assert_called_once_with('odoo_nhs_staff_bank.portal_bank_not_member', {})
            self.assertEqual(res, 'rendered_not_member')

    def test_portal_bank_home_member_view(self):
        """Bank members receive the bank home template with eligible shifts and upcoming bookings."""
        member = self._create_member(user_id=self.user_portal_member.id)
        shift = self._create_shift()
        self._make_available(member, shift)

        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_req.env = self.env(user=self.user_portal_member)
            mock_req.render = MagicMock(return_value='rendered_home')

            res = self.controller.portal_bank_home()
            mock_req.render.assert_called_once()
            template, vals = mock_req.render.call_args[0]
            self.assertEqual(template, 'odoo_nhs_staff_bank.portal_bank_home')
            self.assertEqual(vals['member'], member)
            self.assertIn(shift, vals['eligible_shifts'])
            self.assertEqual(res, 'rendered_home')

    def test_portal_bank_shifts_view(self):
        """Lists open shifts the member is eligible for."""
        member = self._create_member(user_id=self.user_portal_member.id)
        shift = self._create_shift()
        self._make_available(member, shift)

        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_req.env = self.env(user=self.user_portal_member)
            mock_req.render = MagicMock(return_value='rendered_shifts')

            res = self.controller.portal_bank_shifts()
            template, vals = mock_req.render.call_args[0]
            self.assertEqual(template, 'odoo_nhs_staff_bank.portal_bank_shifts')
            self.assertIn(shift, vals['shifts'])
            self.assertEqual(res, 'rendered_shifts')

    def test_portal_bank_shift_accept(self):
        """Accepting an eligible shift via portal creates offer, accepts it, and redirects."""
        member = self._create_member(user_id=self.user_portal_member.id)
        shift = self._create_shift()
        self._make_available(member, shift)

        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_req.env = self.env(user=self.user_portal_member)
            mock_req.redirect = MagicMock(return_value='redirect_success')

            res = self.controller.portal_bank_shift_accept(shift_id=shift.id)
            mock_req.redirect.assert_called_once_with('/my/bank/shifts?accepted=1')
            self.assertEqual(res, 'redirect_success')

            # Offer was created and accepted
            offer = self.Offer.search([('shift_id', '=', shift.id), ('member_id', '=', member.id)])
            self.assertEqual(len(offer), 1)
            self.assertEqual(offer.response, 'accepted')
            self.assertTrue(offer.booking_id)

    def test_portal_bank_offer_decline(self):
        """Declining an offer via portal updates response and stores reason."""
        member = self._create_member(user_id=self.user_portal_member.id)
        shift = self._create_shift()
        offer = self.Offer.create({
            'shift_id': shift.id,
            'member_id': member.id,
        })

        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_req.env = self.env(user=self.user_portal_member)
            mock_req.redirect = MagicMock(return_value='redirect_declined')

            res = self.controller.portal_bank_offer_decline(
                offer_id=offer.id, reason='Not available on this day')
            mock_req.redirect.assert_called_once_with('/my/bank/shifts')
            self.assertEqual(res, 'redirect_declined')

            offer.invalidate_recordset(['response', 'decline_reason'])
            self.assertEqual(offer.response, 'declined')
            self.assertEqual(offer.decline_reason, 'Not available on this day')

    def test_portal_bank_bookings_view(self):
        """Displays bookings for the logged-in member and calculates total worked pay."""
        rate = self._create_rate(hourly_rate=20.0)
        member = self._create_member(user_id=self.user_portal_member.id)
        shift = self._create_shift()

        booking = self.Booking.create({
            'shift_id': shift.id,
            'member_id': member.id,
            'rate_id': rate.id,
            'state': 'worked',
            'shift_start': shift.shift_start,
            'shift_end': shift.shift_end,
        })

        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_req.env = self.env(user=self.user_portal_member)
            mock_req.render = MagicMock(return_value='rendered_bookings')

            res = self.controller.portal_bank_bookings()
            template, vals = mock_req.render.call_args[0]
            self.assertEqual(template, 'odoo_nhs_staff_bank.portal_bank_bookings')
            self.assertIn(booking, vals['bookings'])
            self.assertEqual(vals['total_pay'], booking.payable_amount)

    def test_portal_bank_availability_add(self):
        """Bank member can add availability window through portal form."""
        member = self._create_member(user_id=self.user_portal_member.id)
        now = fields.Datetime.now()
        start_str = (now + timedelta(days=2)).strftime('%Y-%m-%dT10:00')
        end_str = (now + timedelta(days=2)).strftime('%Y-%m-%dT18:00')

        with patch('odoo.addons.odoo_nhs_staff_bank.controllers.portal.request') as mock_req:
            mock_user = MagicMock()
            mock_user.id = self.user_portal_member.id
            mock_user.tz = 'UTC'
            mock_req.env = self.env(user=self.user_portal_member)
            mock_req.env.user = mock_user
            mock_req.redirect = MagicMock(return_value='redirect_avail')

            res = self.controller.portal_bank_availability_add(
                date_from=start_str,
                date_to=end_str,
                availability_type='available',
                note='Available for day shift',
            )
            mock_req.redirect.assert_called_once_with('/my/bank/availability')
            self.assertEqual(res, 'redirect_avail')

            created = self.Availability.search([('member_id', '=', member.id)])
            self.assertEqual(len(created), 1)
            self.assertEqual(created.note, 'Available for day shift')

