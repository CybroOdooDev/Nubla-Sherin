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

PREFERENCE_TYPES = [
    ('prefer', 'Prefer to Work'),
    ('avoid', 'Prefer to Avoid'),
]


class NhsRosterPreference(models.Model):
    """Self-rostering input: a member's preference for (or against) a
    specific date/shift, submitted ahead of the manager building the
    roster. Informational - it feeds the build, it never auto-allocates."""
    _name = 'nhs.roster.preference'
    _description = 'Roster Preference'
    _order = 'date'

    member_id = fields.Many2one(
        'nhs.workforce.member', string='Member', required=True, index=True)
    unit_id = fields.Many2one(
        'nhs.roster.unit', string='Unit', required=True,
        default=lambda self: self._default_unit_id())
    company_id = fields.Many2one(
        'res.company', related='unit_id.company_id', store=True)
    period_id = fields.Many2one(
        'nhs.roster.period', string='Roster Period',
        domain="[('unit_id', '=', unit_id)]",
        help="The period this preference is meant for, if known.")
    date = fields.Date(string='Date', required=True)
    shift_type_id = fields.Many2one(
        'nhs.roster.shift.type', string='Shift Type',
        domain="[('roster_unit_id', '=', unit_id)]",
        help="Leave blank for a whole-day preference.")
    preference_type = fields.Selection(
        PREFERENCE_TYPES, string='Preference', required=True, default='prefer')
    note = fields.Char(string='Note')

    def _default_unit_id(self):
        member = self.env['nhs.workforce.member'].browse(
            self.env.context.get('default_member_id'))
        return member.org_unit_id.roster_unit_ids[:1].id if member else False
