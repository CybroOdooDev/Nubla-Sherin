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


class NhsCheckType(models.Model):
    """One of the six NHS Employment Check Standards (identity, right to
    work, professional registration, references, DBS, occupational health)."""
    _name = 'nhs.check.type'
    _description = 'NHS Employment Check Standard (check type)'
    _order = 'sequence, id'

    name = fields.Char(
        string='Name',
        required=True,
        help="Check name, e.g. Identity, Right to Work, Professional Registration,"
             " Employment History & References, Criminal Record (DBS), Occupational Health."
    )
    code = fields.Char(
        string='Code',
        required=True,
        help="Short code, e.g. ID / RTW / REG / REF / DBS / OH."
    )
    sequence = fields.Integer(string='Sequence', default=10)
    is_sensitive = fields.Boolean(
        string='Sensitive',
        help="Health/criminal-record data — heightened access restriction"
             " (visible only to the Pre-Employment Checks role and Recruitment Manager)."
    )
    has_level = fields.Boolean(
        string='Has Level',
        help="Whether this check type carries a level (e.g. DBS standard/enhanced)."
    )
    default_required = fields.Boolean(
        string='Required by Default',
        default=True,
        help="Included by default when building a new check profile."
    )
    active = fields.Boolean(string='Active', default=True)

    _code_uniq = models.Constraint(
        'unique(code)',
        'A check type with this code already exists.'
    )


class NhsCheckProfileLine(models.Model):
    """One check type (and level) required within a check profile."""
    _name = 'nhs.check.profile.line'
    _description = 'Check profile line — a required check type within a profile'
    _order = 'sequence, id'

    profile_id = fields.Many2one(
        'nhs.check.profile',
        string='Profile',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    check_type_id = fields.Many2one(
        'nhs.check.type',
        string='Check Type',
        required=True,
        help="Which of the six standards this line requires."
    )
    level = fields.Selection([
        ('standard', 'Standard'),
        ('enhanced', 'Enhanced'),
        ('enhanced_barred', 'Enhanced with Barred List'),
    ], string='Level',
        help="Level required, where relevant (e.g. DBS standard vs enhanced)."
    )
    is_required = fields.Boolean(
        string='Required',
        default=True,
        help="Unticked to record the check type as tracked-but-not-mandatory for this profile."
    )

    _profile_check_type_uniq = models.Constraint(
        'unique(profile_id, check_type_id)',
        'Each check type can only appear once per profile.'
    )


class NhsCheckProfile(models.Model):
    """Bundles which check types (and levels) apply to a role/staff group, so
    a vacancy generates the right check set for the successful candidate."""
    _name = 'nhs.check.profile'
    _description = 'Pre-employment check profile (by role/staff group)'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Leave blank to make the profile available to all companies."
    )
    staff_group_id = fields.Many2one(
        'nhs.staff.group',
        string='Staff Group',
        help="Default profile offered for vacancies in this staff group."
    )
    line_ids = fields.One2many(
        'nhs.check.profile.line',
        'profile_id',
        string='Required Checks',
    )
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def _get_default_for_staff_group(self, staff_group_id):
        """Return the first active profile configured for staff_group_id, if any."""
        if not staff_group_id:
            return self.browse()
        return self.search([('staff_group_id', '=', staff_group_id)], limit=1)
