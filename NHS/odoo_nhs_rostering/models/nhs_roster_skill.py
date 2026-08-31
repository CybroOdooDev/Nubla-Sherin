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


class NhsRosterSkill(models.Model):
    """Reference data: a competency that can be required on a demand line
    (e.g. 'IV Competent', 'Mentor', 'ILS') and held by a workforce member.
    Owned locally by rostering (odoo_nhs_staff_bank has its own nhs.skill,
    but that module is only a soft/runtime link, so it cannot be depended
    on)."""
    _name = 'nhs.roster.skill'
    _description = 'Skill (Rostering)'
    _order = 'name'

    name = fields.Char(string='Skill', required=True, translate=True, help="Skill")
    code = fields.Char(string='Code', help="Short code, used in exports.")
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Leave blank to make this skill available to every company."
    )
    active = fields.Boolean(string='Active', default=True, help="Active")

    _name_uniq = models.Constraint(
        'UNIQUE(name, company_id)',
        'A skill with this name already exists for this company!'
    )
