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
"""Shared fixtures and factories for NHS Staff Bank test suite."""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class NhsStaffBankCommon(TransactionCase):
    """Shared base test case providing models, seed data references,
    test users across security groups, and reusable factory methods."""

    @classmethod
    def setUpClass(cls):
        """Set up module seed data, test users, reference models and factories."""
        super().setUpClass()
        cls.company = cls.env.company

        # Model handles
        cls.Member = cls.env['nhs.bank.member']
        cls.Shift = cls.env['nhs.bank.shift']
        cls.Offer = cls.env['nhs.shift.offer']
        cls.Booking = cls.env['nhs.shift.booking']
        cls.Rate = cls.env['nhs.bank.rate']
        cls.Availability = cls.env['nhs.member.availability']
        cls.Skill = cls.env['nhs.skill']
        cls.ShiftType = cls.env['nhs.shift.type']
        cls.Weekday = cls.env['nhs.weekday']
        cls.Gate = cls.env['nhs.compliance.gate']

        # Seed data shipped by data/*.xml
        cls.shift_type_day = cls.env.ref(
            'odoo_nhs_staff_bank.nhs_shift_type_day', raise_if_not_found=False)
        if not cls.shift_type_day:
            cls.shift_type_day = cls.ShiftType.create({
                'name': 'Day', 'code': 'DAY', 'is_unsocial': False,
            })
        cls.shift_type_night = cls.env.ref(
            'odoo_nhs_staff_bank.nhs_shift_type_night', raise_if_not_found=False)
        if not cls.shift_type_night:
            cls.shift_type_night = cls.ShiftType.create({
                'name': 'Night', 'code': 'NIGHT', 'is_unsocial': True,
            })
        cls.shift_type_weekend = cls.env.ref(
            'odoo_nhs_staff_bank.nhs_shift_type_weekend', raise_if_not_found=False)
        if not cls.shift_type_weekend:
            cls.shift_type_weekend = cls.ShiftType.create({
                'name': 'Weekend', 'code': 'WKND', 'is_unsocial': True,
            })

        cls.skill_iv = cls.env.ref(
            'odoo_nhs_staff_bank.nhs_skill_iv_administration', raise_if_not_found=False)
        if not cls.skill_iv:
            cls.skill_iv = cls.Skill.create({
                'name': 'IV Administration', 'category': 'clinical',
            })
        cls.skill_paediatric = cls.env.ref(
            'odoo_nhs_staff_bank.nhs_skill_paediatric', raise_if_not_found=False)
        if not cls.skill_paediatric:
            cls.skill_paediatric = cls.Skill.create({
                'name': 'Paediatric', 'category': 'clinical',
            })

        # Security groups
        cls.group_member = cls.env.ref('odoo_nhs_staff_bank.group_nhs_bank_member')
        cls.group_officer = cls.env.ref('odoo_nhs_staff_bank.group_nhs_bank_officer')
        cls.group_manager = cls.env.ref('odoo_nhs_staff_bank.group_nhs_bank_manager')
        cls.group_user = cls.env.ref('base.group_user')
        cls.group_portal = cls.env.ref('base.group_portal')

        # Test users (Odoo 19: res.users.group_ids, NOT groups_id)
        cls.user_officer = cls.env['res.users'].create({
            'name': 'Test Bank Officer',
            'login': 'nhs_test_bank_officer',
            'email': 'officer@nhs.test',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [
                cls.group_user.id,
                cls.group_officer.id,
            ])],
        })

        cls.user_manager = cls.env['res.users'].create({
            'name': 'Test Bank Manager',
            'login': 'nhs_test_bank_manager',
            'email': 'manager@nhs.test',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [
                cls.group_user.id,
                cls.group_manager.id,
            ])],
        })

        cls.user_portal_member = cls.env['res.users'].create({
            'name': 'Test Bank Member',
            'login': 'nhs_test_bank_member',
            'email': 'member@nhs.test',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [
                cls.group_portal.id,
                cls.group_member.id,
            ])],
        })

        cls.user_no_access = cls.env['res.users'].create({
            'name': 'Test No Access User',
            'login': 'nhs_test_no_access',
            'email': 'noaccess@nhs.test',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'group_ids': [(6, 0, [cls.group_user.id])],
        })

        # Multi-company isolation test environment
        cls.company_2 = cls.env['res.company'].create({
            'name': 'Secondary NHS Trust',
        })
        cls.user_officer_comp2 = cls.env['res.users'].create({
            'name': 'Officer Company 2',
            'login': 'nhs_test_officer_comp2',
            'email': 'officer2@nhs.test',
            'company_id': cls.company_2.id,
            'company_ids': [(6, 0, [cls.company_2.id])],
            'group_ids': [(6, 0, [
                cls.group_user.id,
                cls.group_officer.id,
            ])],
        })

        # Supporting reference records (Establishment models)
        cls.band_5 = cls.env['nhs.afc.band'].create({'name': 'Band 5'})
        cls.band_6 = cls.env['nhs.afc.band'].create({'name': 'Band 6'})
        cls.role_nurse = cls.env['nhs.staff.group'].create({'name': 'Registered Nurse'})
        cls.role_doctor = cls.env['nhs.staff.group'].create({'name': 'Junior Doctor'})
        cls.org_unit_acute = cls.env['nhs.org.unit'].create({
            'name': 'Acute Ward',
            'manager_id': cls.user_manager.id,
        })
        cls.org_unit_surgical = cls.env['nhs.org.unit'].create({
            'name': 'Surgical Ward',
            'manager_id': cls.user_manager.id,
        })

    # ── Factory Helpers ──────────────────────────────────────────────────
    @classmethod
    def _create_member(cls, **overrides):
        """Create a standard active and compliant bank member."""
        vals = {
            'name': 'Jane Nurse',
            'email': 'jane.nurse@nhs.test',
            'phone': '07123456789',
            'company_id': cls.company.id,
            'member_type': 'bank_only',
            'band_id': cls.band_5.id,
            'role_ids': [(6, 0, [cls.role_nurse.id])],
            'area_ids': [(6, 0, [cls.org_unit_acute.id])],
            'skill_ids': [(6, 0, [cls.skill_iv.id])],
            'checks_confirmed': True,
            'manual_compliance_flag': True,
            'state': 'active',
        }
        vals.update(overrides)
        return cls.Member.create(vals)

    @classmethod
    def _create_shift(cls, **overrides):
        """Create an open shift set in the future (default: 2 days from now)."""
        start = fields.Datetime.now() + timedelta(days=2, hours=8)
        end = start + timedelta(hours=8)
        vals = {
            'org_unit_id': cls.org_unit_acute.id,
            'shift_start': start,
            'shift_end': end,
            'shift_type_id': cls.shift_type_day.id,
            'band_id': cls.band_5.id,
            'role_id': cls.role_nurse.id,
            'skill_ids': [(6, 0, [cls.skill_iv.id])],
            'headcount': 1,
            'company_id': cls.company.id,
            'state': 'open',
            'urgency': 'planned',
        }
        vals.update(overrides)
        return cls.Shift.create(vals)

    @classmethod
    def _create_rate(cls, **overrides):
        """Create an effective rate card."""
        vals = {
            'name': 'Band 5 RN Day Rate',
            'company_id': cls.company.id,
            'band_id': cls.band_5.id,
            'role_id': cls.role_nurse.id,
            'shift_type_id': cls.shift_type_day.id,
            'hourly_rate': 25.0,
            'enhancement_pct': 0.0,
            'effective_from': fields.Date.context_today(cls.env.user) - timedelta(days=30),
        }
        vals.update(overrides)
        return cls.Rate.create(vals)

    @classmethod
    def _create_availability(cls, member, date_from, date_to, **overrides):
        """Create an availability window for an active bank member."""
        vals = {
            'member_id': member.id,
            'date_from': date_from,
            'date_to': date_to,
            'availability_type': 'available',
        }
        vals.update(overrides)
        return cls.Availability.create(vals)

    @classmethod
    def _make_available(cls, member, shift):
        """Declare availability covering the entire span of the given shift."""
        return cls._create_availability(
            member,
            date_from=shift.shift_start - timedelta(hours=1),
            date_to=shift.shift_end + timedelta(hours=1),
        )

