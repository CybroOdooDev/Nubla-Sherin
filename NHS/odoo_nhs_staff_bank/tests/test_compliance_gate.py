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
from .common import NhsStaffBankCommon
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestComplianceGate(NhsStaffBankCommon):
    """Test suite for nhs.compliance.gate service model: compliance resolution,
    eligibility filtering (role, band, skills, area, availability), and gate policies."""

    def test_compliance_gate_fallback_mode(self):
        """Fallback mode tests checks_confirmed and manual_compliance_flag."""
        member = self._create_member(checks_confirmed=False)
        compliant, reason = self.Gate.is_member_compliant_with_reason(member)
        self.assertFalse(compliant)
        self.assertIn('Employment checks', reason)

        member.write({'checks_confirmed': True, 'manual_compliance_flag': False})
        compliant, reason = self.Gate.is_member_compliant_with_reason(member)
        self.assertFalse(compliant)
        self.assertIn('non-compliant', reason)

        member.write({'manual_compliance_flag': True})
        compliant, reason = self.Gate.is_member_compliant_with_reason(member)
        self.assertTrue(compliant)
        self.assertEqual(reason, '')

    def test_eligibility_role_mismatch(self):
        """Member with different role is flagged ineligible."""
        shift = self._create_shift(role_id=self.role_doctor.id)
        member = self._create_member(role_ids=[(6, 0, [self.role_nurse.id])])
        self._make_available(member, shift)

        outcome = self.Gate.eligibility(shift, member)
        self.assertFalse(outcome['eligible'])
        self.assertTrue(any('Role mismatch' in r for r in outcome['reasons']))

    def test_eligibility_band_mismatch(self):
        """Member with different band is flagged ineligible."""
        shift = self._create_shift(band_id=self.band_6.id)
        member = self._create_member(band_id=self.band_5.id)
        self._make_available(member, shift)

        outcome = self.Gate.eligibility(shift, member)
        self.assertFalse(outcome['eligible'])
        self.assertTrue(any('Band mismatch' in r for r in outcome['reasons']))

    def test_eligibility_missing_skills(self):
        """Member missing required shift skills is flagged ineligible."""
        shift = self._create_shift(skill_ids=[(6, 0, [self.skill_iv.id, self.skill_paediatric.id])])
        member = self._create_member(skill_ids=[(6, 0, [self.skill_iv.id])])
        self._make_available(member, shift)

        outcome = self.Gate.eligibility(shift, member)
        self.assertFalse(outcome['eligible'])
        self.assertTrue(any('Missing skill' in r for r in outcome['reasons']))

    def test_eligibility_area_mismatch(self):
        """Member not cleared to work in the ward is flagged ineligible."""
        shift = self._create_shift(org_unit_id=self.org_unit_surgical.id)
        member = self._create_member(area_ids=[(6, 0, [self.org_unit_acute.id])])
        self._make_available(member, shift)

        outcome = self.Gate.eligibility(shift, member)
        self.assertFalse(outcome['eligible'])
        self.assertTrue(any('Not cleared to work' in r for r in outcome['reasons']))

    def test_eligibility_inactive_member(self):
        """Inactive member is flagged ineligible."""
        shift = self._create_shift()
        member = self._create_member(state='draft')
        self._make_available(member, shift)

        outcome = self.Gate.eligibility(shift, member)
        self.assertFalse(outcome['eligible'])
        self.assertTrue(any('not active' in r for r in outcome['reasons']))

    def test_eligibility_availability_mismatch(self):
        """Member without covering availability is flagged ineligible."""
        shift = self._create_shift()
        member = self._create_member()
        # No availability declared

        outcome = self.Gate.eligibility(shift, member)
        self.assertFalse(outcome['eligible'])
        self.assertTrue(any('Not available' in r for r in outcome['reasons']))

    def test_eligibility_gate_policy_soft_vs_hard(self):
        """Hard policy blocks eligibility on non-compliance; soft policy warns only."""
        shift = self._create_shift()
        member = self._create_member(checks_confirmed=False)
        self._make_available(member, shift)

        # Hard policy
        self.company.nhs_bank_gate_policy = 'hard'
        outcome_hard = self.Gate.eligibility(shift, member)
        self.assertFalse(outcome_hard['eligible'])

        # Soft policy
        self.company.nhs_bank_gate_policy = 'soft'
        outcome_soft = self.Gate.eligibility(shift, member)
        self.assertTrue(outcome_soft['eligible'])
        self.assertTrue(any('Warning (Gate Policy is Warn Only' in r for r in outcome_soft['reasons']))

