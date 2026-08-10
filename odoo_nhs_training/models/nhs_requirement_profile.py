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


class NhsRequirementProfile(models.Model):
    _name = 'nhs.requirement.profile'
    _description = 'Requirement Profile — bundle of training requirements for a role'
    _order = 'name'

    name = fields.Char(
        string='Profile Name',
        required=True,
        help="Profile name (e.g. 'Ward Nurse', 'Administrator', 'Consultant')."
    )
    description = fields.Text(
        string='Description',
        help="What roles this profile suits."
    )
    requirement_ids = fields.One2many(
        'nhs.training.requirement',
        'profile_id',
        string='Requirements',
        help="The subjects (and levels) this profile requires."
    )
    requirement_count = fields.Integer(
        string='Requirement Count',
        compute='_compute_requirement_count',
    )
    post_ids = fields.One2many(
        'nhs.establishment.post',
        'training_requirement_profile_id',
        string='Posts',
        help="Posts assigned this profile — every holder inherits its requirements."
    )
    post_count = fields.Integer(
        string='Post Count',
        compute='_compute_post_count',
        help="Posts currently assigned this profile."
    )
    member_ids = fields.One2many(
        'nhs.workforce.member',
        'requirement_profile_id',
        string='Members',
        help="Workforce members currently on this profile."
    )
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        help="Members currently on this profile."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    def _compute_requirement_count(self):
        for profile in self:
            profile.requirement_count = len(profile.requirement_ids)

    def _compute_post_count(self):
        for profile in self:
            profile.post_count = len(profile.post_ids)

    def _compute_member_count(self):
        member_data = self.env['nhs.workforce.member']._read_group(
            [('requirement_profile_id', 'in', self.ids)],
            ['requirement_profile_id'], ['__count'],
        )
        counts = {profile.id: count for profile, count in member_data}
        for profile in self:
            profile.member_count = counts.get(profile.id, 0)

    def action_view_posts(self):
        self.ensure_one()
        return {
            'name': 'Posts',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.establishment.post',
            'view_mode': 'list,form',
            'domain': [('training_requirement_profile_id', '=', self.id)],
        }

    def action_view_members(self):
        self.ensure_one()
        return {
            'name': 'Members',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.workforce.member',
            'view_mode': 'list,kanban,form',
            'domain': [('requirement_profile_id', '=', self.id)],
        }

    def action_assign_posts(self):
        self.ensure_one()
        return {
            'name': 'Assign Posts',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.profile.assign.posts.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_profile_id': self.id},
        }
