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

SHIFT_CATEGORIES = [
    ('early', 'Early'),
    ('late', 'Late'),
    ('long_day', 'Long Day'),
    ('night', 'Night'),
    ('twilight', 'Twilight'),
    ('on_call', 'On-Call'),
    ('other', 'Other'),
]

# Bootstrap-ish colour per category, used by the roster grid to colour-code cells.
CATEGORY_COLORS = {
    'early': '#f4b400', 'late': '#ff7043', 'long_day': '#ab47bc',
    'night': '#3949ab', 'twilight': '#00897b', 'on_call': '#6d4c41',
    'other': '#78909c',
}


class NhsRosterShiftType(models.Model):
    """A kind of working day for one rostered unit: early / late / long day /
    night / twilight / on-call, with its times, break rule and paid hours."""
    _name = 'nhs.roster.shift.type'
    _description = 'Shift Type'
    _order = 'roster_unit_id, sequence, name'

    roster_unit_id = fields.Many2one(
        'nhs.roster.unit', string='Unit', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Shift Type', required=True, help="e.g. 'Early', 'Night'.")
    code = fields.Char(string='Code', help="Short code, used on the roster grid/exports.")
    category = fields.Selection(
        SHIFT_CATEGORIES, string='Category', required=True, default='other',
        help="Drives colour-coding on the roster grid and the MAX_CONSEC_NIGHTS rule."
    )
    sequence = fields.Integer(string='Sequence', default=10)
    time_start = fields.Float(string='Start Time', required=True, default=7.5)
    time_end = fields.Float(string='End Time', required=True, default=19.5)
    break_minutes = fields.Integer(string='Break (Minutes)', default=30)
    duration_hours = fields.Float(
        string='Paid Hours', compute='_compute_duration_hours', store=True, digits=(16, 2),
        help="Time on duty minus break, in hours. Handles shifts spanning midnight."
    )
    is_night = fields.Boolean(
        string='Night Shift', compute='_compute_is_night', store=True,
        help="Counted for the MAX_CONSEC_NIGHTS rule."
    )
    color = fields.Char(string='Colour', compute='_compute_color', store=True)
    active = fields.Boolean(string='Active', default=True)

    _name_uniq = models.Constraint(
        'UNIQUE(roster_unit_id, name)',
        'A shift type with this name already exists for this unit!'
    )

    @api.depends('time_start', 'time_end', 'break_minutes')
    def _compute_duration_hours(self):
        for shift_type in self:
            start, end = shift_type.time_start, shift_type.time_end
            span = (end - start) if end > start else (24.0 - start + end)
            shift_type.duration_hours = max(0.0, span - (shift_type.break_minutes or 0) / 60.0)

    @api.depends('category')
    def _compute_is_night(self):
        for shift_type in self:
            shift_type.is_night = shift_type.category == 'night'

    @api.depends('category')
    def _compute_color(self):
        for shift_type in self:
            shift_type.color = CATEGORY_COLORS.get(shift_type.category, '#78909c')
