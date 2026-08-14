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
from odoo import fields, models


class NhsComplianceGate(models.AbstractModel):
    """Service model: determines whether a bank member is compliant (and
    therefore bookable) at a given date.

    This gate isolates ALL knowledge of the Mandatory Training module — if
    that module changes, only this file needs to change. It reads
    odoo_nhs_training where installed (via the member's `workforce_member_id`
    Reference field, never a hard Many2one, so the co-model is not required
    to exist), and falls back to a light in-module flag when the Training
    module is absent, so the gate always functions.

    The gate is enforced at OFFER time (only eligible+compliant members are
    offered) and re-checked at BOOKING time (compliance can lapse between
    offer and booking); `compliant_at_booking` is then snapshotted on the
    booking for the audit trail.
    """
    _name = 'nhs.compliance.gate'
    _description = 'Bank Compliance Gate (service)'

    def is_member_compliant(self, member, at_date=None):
        """True if `member` is currently compliant (mandatory training and
        professional registration both in date, at `at_date` — defaults to
        today). Delegates to odoo_nhs_training when linked and installed;
        otherwise falls back to the member's own checks-confirmed +
        in-module compliance flag."""
        compliant, _reason = self.is_member_compliant_with_reason(member, at_date=at_date)
        return compliant

    def is_member_compliant_with_reason(self, member, at_date=None):
        """Same as `is_member_compliant`, but also returns a human-readable
        reason string (empty when compliant) explaining what is out of date —
        surfaced to the coordinator wherever a member is excluded."""
        workforce_member = self._resolve_workforce_member(member)
        if workforce_member:
            if hasattr(workforce_member, 'is_training_compliant') and not workforce_member.is_training_compliant():
                return False, (
                    "Mandatory training or professional registration has lapsed"
                    " (via NHS Mandatory Training)."
                )
            return True, ''
        # Standalone fallback: odoo_nhs_training absent, or no link set.
        if not member.checks_confirmed:
            return False, "Employment checks are not confirmed for this member."
        if not member.manual_compliance_flag:
            return False, member.manual_compliance_note or (
                "Marked non-compliant (no Mandatory Training module installed;"
                " manual compliance flag is off).")
        return True, ''

    def _resolve_workforce_member(self, member):
        """Resolve the linked odoo_nhs_training workforce member, if the
        Training module is installed and the member is linked to it."""
        ref = member.workforce_member_id
        if ref and ref._name == 'nhs.workforce.member' and 'nhs.workforce.member' in self.env:
            return ref
        return False

    def eligibility(self, shift, member):
        """Combine role/band + skills + area + availability + compliance
        into a single eligible/ineligible result with human-readable reasons,
        for a candidate `member` against an open `shift`."""
        reasons = []
        if shift.band_id and member.band_id and shift.band_id != member.band_id:
            reasons.append("Band mismatch (needs %s, member is %s)." % (
                shift.band_id.name, member.band_id.name))
        if shift.role and member.role_ids:
            role_text = shift.role.strip().lower()
            if not any(role_text in r.name.lower() or r.name.lower() in role_text
                       for r in member.role_ids):
                reasons.append("Role mismatch (needs '%s')." % shift.role)
        if shift.skill_ids and not shift.skill_ids <= member.skill_ids:
            missing = shift.skill_ids - member.skill_ids
            reasons.append("Missing skill(s): %s." % ', '.join(missing.mapped('name')))
        if shift.org_unit_id and member.area_ids and shift.org_unit_id not in member.area_ids:
            reasons.append("Not cleared to work in %s." % shift.org_unit_id.display_name)
        if member.state != 'active':
            reasons.append("Member is not active (%s)." % member.state)
        if not member._is_available_for(shift.shift_start, shift.shift_end):
            reasons.append("Not available for these dates/times.")
        compliant, reason = self.is_member_compliant_with_reason(member, at_date=fields.Date.to_date(shift.shift_start))
        if not compliant:
            reasons.append(reason)
        return {'eligible': not reasons, 'reasons': reasons}

    def reason(self, member, at_date=None):
        """Human-readable reason `member` is currently ineligible/non-compliant
        (empty string when compliant)."""
        _compliant, reason = self.is_member_compliant_with_reason(member, at_date=at_date)
        return reason
