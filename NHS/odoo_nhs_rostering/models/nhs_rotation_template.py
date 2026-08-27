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

WEEKDAYS = [
    ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'),
    ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
]


class NhsRotationTemplate(models.Model):
    """A repeating multi-week shift pattern (e.g. a 4-week rotation) that can
    be rolled across a roster period for a person or group in one action,
    rather than placing every shift by hand."""
    _name = 'nhs.rotation.template'
    _description = 'Rotation Template'
    _order = 'roster_unit_id, name'

    roster_unit_id = fields.Many2one(
        'nhs.roster.unit', string='Unit', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Template Name', required=True, help="e.g. '4-week Early/Late/Night'.")
    weeks = fields.Integer(
        string='Pattern Length (Weeks)', required=True, default=4,
        help="How many weeks the pattern repeats over before looping back to week 1."
    )
    line_ids = fields.One2many('nhs.rotation.template.line', 'template_id', string='Pattern Lines')
    line_count = fields.Integer(compute='_compute_line_count')
    active = fields.Boolean(string='Active', default=True)

    def _compute_line_count(self):
        for template in self:
            template.line_count = len(template.line_ids)


class NhsRotationTemplateLine(models.Model):
    """One day of a rotation template: which week of the pattern, which
    weekday, and which shift type (blank = day off)."""
    _name = 'nhs.rotation.template.line'
    _description = 'Rotation Template Line'
    _order = 'template_id, week_number, weekday'

    template_id = fields.Many2one(
        'nhs.rotation.template', string='Template', required=True, ondelete='cascade', index=True)
    week_number = fields.Integer(string='Week', required=True, default=1)
    weekday = fields.Selection(WEEKDAYS, string='Weekday', required=True)
    shift_type_id = fields.Many2one(
        'nhs.roster.shift.type', string='Shift Type',
        domain="[('roster_unit_id', '=', parent.roster_unit_id)]",
        help="Leave blank for a day off on this pattern day."
    )

    _week_weekday_uniq = models.Constraint(
        'UNIQUE(template_id, week_number, weekday)',
        'This template already has a line for that week/weekday!'
    )
