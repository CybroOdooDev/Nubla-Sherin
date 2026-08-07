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
from odoo import api, fields, models
from odoo.exceptions import ValidationError

OVERRIDE_TYPES = [
    ('add', 'Add Requirement'),
    ('waive', 'Waive Requirement'),
]


class NhsTrainingRequirement(models.Model):
    _name = 'nhs.training.requirement'
    _description = 'Training requirement — subject+level required by a profile, staff group or individual'
    _order = 'subject_id'

    profile_id = fields.Many2one(
        'nhs.requirement.profile',
        string='Requirement Profile',
        ondelete='cascade',
        index=True,
        help="Owning profile, when this requirement is part of a role bundle."
    )
    staff_group_id = fields.Many2one(
        'nhs.staff.group',
        string='Staff Group',
        ondelete='cascade',
        index=True,
        help="Requirement applied to an entire staff group (alternative to a profile)."
    )
    member_id = fields.Many2one(
        'nhs.workforce.member',
        string='Individual Member',
        ondelete='cascade',
        index=True,
        help="Individual-level override — an added or waived requirement for this person only."
    )
    subject_id = fields.Many2one(
        'nhs.training.subject',
        string='Subject',
        required=True,
        ondelete='restrict',
        help="Required subject (the subject already encodes its level)."
    )
    frequency_months_override = fields.Integer(
        string='Refresh Override (Months)',
        help="Override the subject's default refresh frequency for this requirement."
    )
    effective_from = fields.Date(
        string='Effective From',
        help="When this requirement starts applying (e.g. a newly introduced subject)."
    )
    is_mandatory = fields.Boolean(
        string='Mandatory',
        default=True,
        help="Hard requirement vs recommended. Both are reported, but weighted differently"
             " in the compliance percentage."
    )
    override_type = fields.Selection(
        OVERRIDE_TYPES,
        string='Override Type',
        help="For an individual-level requirement: Add a subject the person's profile/staff"
             " group wouldn't otherwise require, or Waive one that it would."
    )
    exemption_reason = fields.Text(
        string='Exemption / Waiver Reason',
        help="Justification for waiving this requirement for the individual."
    )
    exemption_review_date = fields.Date(
        string='Exemption Review Date',
        help="Date the exemption should be reviewed."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    @api.depends('subject_id', 'profile_id', 'staff_group_id', 'member_id')
    def _compute_display_name(self):
        """Build a display name combining the owning scope (profile/staff group/member)
        with the required subject."""
        for req in self:
            target = ""
            if req.profile_id:
                target = req.profile_id.name
            elif req.staff_group_id:
                target = req.staff_group_id.name
            elif req.member_id:
                target = req.member_id.name

            subject = req.subject_id.complete_name or req.subject_id.name or "Unknown Subject"
            if target:
                req.display_name = f"{target} — {subject}"
            else:
                req.display_name = subject

    @api.constrains('profile_id', 'staff_group_id', 'member_id')
    def _check_single_scope(self):
        """Ensure the requirement is attached to exactly one scope: a profile, a staff
        group, or an individual member."""
        for req in self:
            scopes = [bool(req.profile_id), bool(req.staff_group_id), bool(req.member_id)]
            if sum(scopes) != 1:
                raise ValidationError(
                    'A training requirement must be attached to exactly one of:'
                    ' a Requirement Profile, a Staff Group, or an individual Member.')

    @api.constrains('member_id', 'override_type')
    def _check_member_override_type(self):
        """Ensure an individual-level requirement always states Add or Waive."""
        for req in self:
            if req.member_id and not req.override_type:
                raise ValidationError(
                    'An individual-level requirement must specify whether it Adds or'
                    ' Waives the subject.')

    @api.constrains('override_type', 'exemption_reason')
    def _check_waiver_reason(self):
        """Ensure a waived requirement always records its exemption reason."""
        for req in self:
            if req.override_type == 'waive' and not req.exemption_reason:
                raise ValidationError(
                    'A waived requirement must record a reason for the exemption.')

    @api.onchange('member_id')
    def _onchange_member_id(self):
        """Default individual-level requirements to Add when a member is set."""
        if self.member_id and not self.override_type:
            self.override_type = 'add'
