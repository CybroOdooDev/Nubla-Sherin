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
class TestBankRate(NhsStaffBankCommon):
    """Test suite for nhs.bank.rate: date range constraints, rate lookup specificity,
    enhancement calculations, and company scoping."""

    def test_rate_date_range_constraint(self):
        """Effective To cannot be before Effective From."""
        today = fields.Date.today()
        with self.assertRaises(ValidationError):
            self.Rate.create({
                'name': 'Invalid Date Rate',
                'band_id': self.band_5.id,
                'role_id': self.role_nurse.id,
                'shift_type_id': self.shift_type_day.id,
                'hourly_rate': 20.0,
                'effective_from': today,
                'effective_to': today - timedelta(days=1),
            })

    def test_rate_compute_payable(self):
        """compute_payable properly calculates base hours and enhancement percentage."""
        rate = self.Rate.create({
            'name': 'Night Enhanced Rate',
            'band_id': self.band_5.id,
            'role_id': self.role_nurse.id,
            'shift_type_id': self.shift_type_night.id,
            'hourly_rate': 20.0,
            'enhancement_pct': 30.0,
            'effective_from': fields.Date.today(),
        })
        # 10 hours * £20 * 1.30 = £260.0
        self.assertAlmostEqual(rate.compute_payable(10.0), 260.0)

    def test_rate_find_rate_specificity_hierarchy(self):
        """_find_rate prefers specific (band + role + shift_type) over generic rates."""
        today = fields.Date.today()

        # Specific rate
        specific_rate = self.Rate.create({
            'name': 'Specific Nurse Day Rate',
            'company_id': self.company.id,
            'band_id': self.band_5.id,
            'role_id': self.role_nurse.id,
            'shift_type_id': self.shift_type_day.id,
            'hourly_rate': 28.0,
            'effective_from': today - timedelta(days=10),
        })

        found = self.Rate._find_rate(
            band_id=self.band_5.id,
            role_id=self.role_nurse.id,
            shift_type_id=self.shift_type_day.id,
            date=today,
            company_id=self.company.id,
        )
        self.assertEqual(found, specific_rate)

    def test_rate_find_rate_date_filtering(self):
        """_find_rate respects effective_from and effective_to boundaries."""
        today = fields.Date.today()

        # Expired rate
        self.Rate.create({
            'name': 'Expired Rate',
            'company_id': self.company.id,
            'band_id': self.band_6.id,
            'role_id': self.role_nurse.id,
            'shift_type_id': self.shift_type_day.id,
            'hourly_rate': 30.0,
            'effective_from': today - timedelta(days=30),
            'effective_to': today - timedelta(days=5),
        })

        found_expired = self.Rate._find_rate(
            band_id=self.band_6.id,
            role_id=self.role_nurse.id,
            shift_type_id=self.shift_type_day.id,
            date=today,
            company_id=self.company.id,
        )
        self.assertFalse(found_expired)

        # Future rate
        self.Rate.create({
            'name': 'Future Rate',
            'company_id': self.company.id,
            'band_id': self.band_6.id,
            'role_id': self.role_nurse.id,
            'shift_type_id': self.shift_type_day.id,
            'hourly_rate': 35.0,
            'effective_from': today + timedelta(days=5),
        })

        found_future = self.Rate._find_rate(
            band_id=self.band_6.id,
            role_id=self.role_nurse.id,
            shift_type_id=self.shift_type_day.id,
            date=today,
            company_id=self.company.id,
        )
        self.assertFalse(found_future)

    def test_rate_company_isolation(self):
        """Rates configured in Company 1 are not found for Company 2."""
        today = fields.Date.today()
        self.Rate.create({
            'name': 'Company 1 Only Rate',
            'company_id': self.company.id,
            'band_id': self.band_5.id,
            'role_id': self.role_doctor.id,
            'shift_type_id': self.shift_type_day.id,
            'hourly_rate': 45.0,
            'effective_from': today - timedelta(days=1),
        })

        found_comp2 = self.Rate._find_rate(
            band_id=self.band_5.id,
            role_id=self.role_doctor.id,
            shift_type_id=self.shift_type_day.id,
            date=today,
            company_id=self.company_2.id,
        )
        self.assertFalse(found_comp2)

