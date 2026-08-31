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

SHIFT_TYPES = [
    ('Early', 'Early'),
    ('Late', 'Late'),
    ('Long Day', 'Long Day'),
    ('Night', 'Night'),
    ('Twilight', 'Twilight'),
    ('On-Call', 'On-Call'),
    ('Other', 'Other'),
]

# Bootstrap-ish colour per shift type, used by the roster grid to colour-code cells.
SHIFT_COLORS = {
    'Early': '#f4b400', 'Late': '#ff7043', 'Long Day': '#ab47bc',
    'Night': '#3949ab', 'Twilight': '#00897b', 'On-Call': '#6d4c41',
    'Other': '#78909c',
}


class NhsRosterShiftType(models.Model):
    """A kind of working day for one rostered unit: early / late / long day /
    night / twilight / on-call, with its times, break rule and paid hours.
    One fixed-vocabulary field only (name) - an earlier revision split this
    into a free-text name plus a separate Category driving the logic below,
    but every unit just re-picked the same value in both, so it was pure
    double-entry with no actual benefit; collapsed back to one field."""
    _name = 'nhs.roster.shift.type'
    _description = 'Shift Type'
    _order = 'roster_unit_id, sequence, name'

    roster_unit_id = fields.Many2one(
        'nhs.roster.unit', string='Unit', required=True, ondelete='cascade', index=True, help="Unit")
    name = fields.Selection(
        SHIFT_TYPES, string='Shift Type', required=True, default='Other',
        help="Drives colour-coding on the roster grid, the MAX_CONSEC_NIGHTS rule and"
             " the Staff Bank push mapping. One row per value per unit (a unit can't"
             " have two different 'Night' shift types) - use Code for a short label if"
             " you need to tell variants apart on the grid/exports."
    )
    code = fields.Char(string='Code', help="Short code, used on the roster grid/exports.")
    sequence = fields.Integer(string='Sequence', default=10, help="Sequence")
    time_start = fields.Float(string='Start Time', required=True, default=7.5, help="Start Time")
    time_end = fields.Float(string='End Time', required=True, default=19.5, help="End Time")
    break_minutes = fields.Integer(string='Break (Minutes)', default=30, help="Break (Minutes)")
    duration_hours = fields.Float(
        string='Paid Hours', compute='_compute_duration_hours', store=True, digits=(16, 2),
        help="Time on duty minus break, in hours. Handles shifts spanning midnight."
    )
    is_night = fields.Boolean(
        string='Night Shift', compute='_compute_is_night', store=True,
        help="Counted for the MAX_CONSEC_NIGHTS rule."
    )
    color = fields.Char(string='Colour', compute='_compute_color', store=True, help="Colour")
    active = fields.Boolean(string='Active', default=True, help="Active")

    _name_uniq = models.Constraint(
        'UNIQUE(roster_unit_id, name)',
        'A shift type with this name already exists for this unit!'
    )

    @api.depends('time_start', 'time_end', 'break_minutes')
    def _compute_duration_hours(self):
        """ Method for compute duration hours """
        for shift_type in self:
            start, end = shift_type.time_start, shift_type.time_end
            span = (end - start) if end > start else (24.0 - start + end)
            shift_type.duration_hours = max(0.0, span - (shift_type.break_minutes or 0) / 60.0)

    @api.depends('name')
    def _compute_is_night(self):
        """ Method for compute is night """
        for shift_type in self:
            shift_type.is_night = shift_type.name == 'Night'

    @api.depends('name')
    def _compute_color(self):
        """ Method for compute color """
        for shift_type in self:
            shift_type.color = SHIFT_COLORS.get(shift_type.name, '#78909c')
