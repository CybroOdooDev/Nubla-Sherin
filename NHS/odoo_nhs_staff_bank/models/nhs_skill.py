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


class NhsSkill(models.Model):
    """A skill/competency that a bank member can hold and a shift can
    require, driving shift eligibility (e.g. 'IV administration',
    'paediatric')."""
    _name = 'nhs.skill'
    _description = 'Bank Skill / Competency'
    _order = 'category, name'

    name = fields.Char(
        string='Skill',
        required=True,
        help="Skill/competency name, e.g. 'IV administration', 'Paediatric'."
    )
    category = fields.Selection([
        ('clinical', 'Clinical'),
        ('technical', 'Technical'),
        ('language', 'Language'),
        ('mandatory', 'Mandatory'),
    ],
        string='Category',
        help="Grouping for the skill catalogue."
    )
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        help="Number of active bank members currently holding this skill."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag. Archived skills are hidden but retained for history."
    )

    _name_uniq = models.Constraint(
        'UNIQUE(name)',
        'A skill with this name already exists!'
    )

    def _compute_member_count(self):
        """Count active bank members holding each skill."""
        member_data = self.env['nhs.bank.member']._read_group(
            [('skill_ids', 'in', self.ids)],
            ['skill_ids'], ['__count'],
        )
        counts = {skill.id: count for skill, count in member_data}
        for skill in self:
            skill.member_count = counts.get(skill.id, 0)
