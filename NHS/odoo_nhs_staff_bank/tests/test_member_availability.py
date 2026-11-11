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
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import NhsStaffBankCommon


@tagged('post_install', '-at_install')
class TestMemberAvailability(NhsStaffBankCommon):
    """Test suite for nhs.member.availability: member state guard, date constraints,
    recurring boundaries, and non-overlapping window validation."""

    def test_availability_requires_active_member(self):
        """Availability can only be declared for active bank members."""
        draft_member = self._create_member(state='draft')
        now = fields.Datetime.now()
        with self.assertRaises(ValidationError):
            self.Availability.create({
                'member_id': draft_member.id,
                'date_from': now + timedelta(days=1),
                'date_to': now + timedelta(days=2),
            })

    def test_availability_date_constraints(self):
        """Rejects past dates and 'To' before or equal to 'From'."""
        member = self._create_member(state='active')
        now = fields.Datetime.now()

        # Past date_from
        with self.assertRaises(ValidationError):
            self.Availability.create({
                'member_id': member.id,
                'date_from': now - timedelta(days=1),
                'date_to': now + timedelta(days=1),
            })

        # date_to before date_from
        with self.assertRaises(ValidationError):
            self.Availability.create({
                'member_id': member.id,
                'date_from': now + timedelta(days=2),
                'date_to': now + timedelta(days=1),
            })

        # date_to equal to date_from
        with self.assertRaises(ValidationError):
            self.Availability.create({
                'member_id': member.id,
                'date_from': now + timedelta(days=2),
                'date_to': now + timedelta(days=2),
            })

    def test_availability_recurring_end_date_constraint(self):
        """Recurring pattern end date cannot be earlier than start date."""
        member = self._create_member(state='active')
        now = fields.Datetime.now()
        with self.assertRaises(ValidationError):
            self.Availability.create({
                'member_id': member.id,
                'date_from': now + timedelta(days=5),
                'date_to': now + timedelta(days=6),
                'recurring': True,
                'weekday': '0',
                'recurrence_end_date': (now + timedelta(days=2)).date(),
            })

    def test_availability_no_overlapping_non_recurring_windows(self):
        """A member cannot have two non-recurring windows overlapping in time."""
        member = self._create_member(state='active')
        now = fields.Datetime.now()

        # Window 1: Day 2 to Day 4
        self.Availability.create({
            'member_id': member.id,
            'date_from': now + timedelta(days=2),
            'date_to': now + timedelta(days=4),
            'availability_type': 'available',
        })

        # Overlapping window: Day 3 to Day 5
        with self.assertRaises(ValidationError):
            self.Availability.create({
                'member_id': member.id,
                'date_from': now + timedelta(days=3),
                'date_to': now + timedelta(days=5),
                'availability_type': 'available',
            })

