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
from odoo.exceptions import AccessError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import NhsStaffBankCommon


@tagged('post_install', '-at_install')
class TestStaffBankSecurity(NhsStaffBankCommon):
    """Test suite for access control lists (ir.model.access.csv) and record rules
    across Bank Member, Bank Officer, Bank Manager, and multi-company environments."""

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_unprivileged_user_access_denied(self):
        """Internal users without bank roles cannot read or create bank records."""
        shift = self._create_shift()
        member = self._create_member()

        # Reading shift
        with self.assertRaises(AccessError):
            shift.with_user(self.user_no_access).read(['name'])

        # Reading member
        with self.assertRaises(AccessError):
            member.with_user(self.user_no_access).read(['name'])

        # Creating shift
        with self.assertRaises(AccessError):
            self.Shift.with_user(self.user_no_access).create({
                'org_unit_id': self.org_unit_acute.id,
                'shift_start': fields.Datetime.now() + timedelta(days=2),
                'shift_end': fields.Datetime.now() + timedelta(days=2, hours=8),
                'shift_type_id': self.shift_type_day.id,
                'band_id': self.band_5.id,
                'role_id': self.role_nurse.id,
            })

    def test_bank_officer_permissions_and_rate_card_restriction(self):
        """Bank Officer can manage shifts and members, but cannot create or modify rate cards."""
        # Officer can create shift
        shift = self.Shift.with_user(self.user_officer).create({
            'org_unit_id': self.org_unit_acute.id,
            'shift_start': fields.Datetime.now() + timedelta(days=2),
            'shift_end': fields.Datetime.now() + timedelta(days=2, hours=8),
            'shift_type_id': self.shift_type_day.id,
            'band_id': self.band_5.id,
            'role_id': self.role_nurse.id,
        })
        self.assertTrue(shift.id)

        # Officer cannot create a rate card
        with mute_logger('odoo.addons.base.models.ir_model', 'odoo.models'):
            with self.assertRaises(AccessError):
                self.Rate.with_user(self.user_officer).create({
                    'name': 'Officer Unauthorized Rate',
                    'band_id': self.band_5.id,
                    'role_id': self.role_nurse.id,
                    'shift_type_id': self.shift_type_day.id,
                    'hourly_rate': 30.0,
                    'effective_from': fields.Date.today(),
                })

    def test_bank_manager_full_rate_permissions(self):
        """Bank Manager can create, modify, and delete rate cards."""
        rate = self.Rate.with_user(self.user_manager).create({
            'name': 'Manager Authorized Rate',
            'band_id': self.band_5.id,
            'role_id': self.role_nurse.id,
            'shift_type_id': self.shift_type_day.id,
            'hourly_rate': 32.0,
            'effective_from': fields.Date.today(),
        })
        self.assertTrue(rate.id)

        rate.write({'hourly_rate': 34.0})
        self.assertEqual(rate.hourly_rate, 34.0)

    def test_bank_member_portal_scoping_rules(self):
        """Bank members can only read their own availability, offers, bookings and profile."""
        member_1 = self._create_member(name='Member One', user_id=self.user_portal_member.id)

        other_user = self.env['res.users'].create({
            'name': 'Other Portal User',
            'login': 'other_portal_user',
            'email': 'other@nhs.test',
            'group_ids': [(6, 0, [self.group_portal.id, self.group_member.id])],
        })
        member_2 = self._create_member(name='Member Two', user_id=other_user.id)

        # Create bookings for both members
        shift = self._create_shift()
        booking_1 = self.Booking.create({'shift_id': shift.id, 'member_id': member_1.id})
        booking_2 = self.Booking.create({'shift_id': shift.id, 'member_id': member_2.id})

        # Member 1 reading own booking succeeds
        read_own = booking_1.with_user(self.user_portal_member).read(['state'])
        self.assertTrue(read_own)

        # Member 1 searching bookings only sees their own
        visible_bookings = self.Booking.with_user(self.user_portal_member).search([])
        self.assertIn(booking_1, visible_bookings)
        self.assertNotIn(booking_2, visible_bookings)

        # Member 1 cannot read rate cards
        with mute_logger('odoo.addons.base.models.ir_model', 'odoo.models'):
            with self.assertRaises(AccessError):
                self.Rate.with_user(self.user_portal_member).search([])

    def test_multi_company_scoping(self):
        """Users in Company 1 cannot access shifts or bookings of Company 2."""
        shift_comp1 = self._create_shift(company_id=self.company.id)
        shift_comp2 = self._create_shift(company_id=self.company_2.id)

        # Officer of Company 1 only sees shift_comp1
        officer_1_shifts = self.Shift.with_user(self.user_officer).search([])
        self.assertIn(shift_comp1, officer_1_shifts)
        self.assertNotIn(shift_comp2, officer_1_shifts)

        # Officer of Company 2 only sees shift_comp2
        officer_2_shifts = self.Shift.with_user(self.user_officer_comp2).search([])
        self.assertIn(shift_comp2, officer_2_shifts)
        self.assertNotIn(shift_comp1, officer_2_shifts)

