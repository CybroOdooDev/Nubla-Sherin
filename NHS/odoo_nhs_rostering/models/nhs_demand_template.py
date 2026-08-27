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

WEEKDAYS = [
    ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'),
    ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
]


class NhsDemandTemplate(models.Model):
    """The unit's DEMAND: for each weekday and shift type, the required
    headcount by role/band/skill. Effective-dated so establishment changes
    (or a new demand pattern) can flow through without losing history -
    only one demand template is effective for a unit on a given date."""
    _name = 'nhs.demand.template'
    _description = 'Demand Template'
    _order = 'roster_unit_id, effective_from desc'

    roster_unit_id = fields.Many2one(
        'nhs.roster.unit', string='Unit', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Name', required=True, help="e.g. 'Standard Demand 2026'.")
    effective_from = fields.Date(string='Effective From', required=True,
                                  default=fields.Date.context_today)
    effective_to = fields.Date(string='Effective To', help="Leave blank for still in effect.")
    line_ids = fields.One2many('nhs.demand.line', 'template_id', string='Demand Lines')
    line_count = fields.Integer(compute='_compute_line_count')
    active = fields.Boolean(string='Active', default=True)

    def _compute_line_count(self):
        for template in self:
            template.line_count = len(template.line_ids)

    @api.constrains('effective_from', 'effective_to')
    def _check_dates(self):
        for template in self:
            if template.effective_to and template.effective_to < template.effective_from:
                raise ValidationError('Effective To must be on or after Effective From.')

    def lines_for_date(self, a_date):
        """Effective demand lines for a specific calendar date: date-specific
        override lines for that exact date take precedence over the standing
        weekly-pattern line for that weekday."""
        self.ensure_one()
        weekday = str(a_date.weekday())
        overrides = self.line_ids.filtered(lambda l: l.date_override == a_date)
        if overrides:
            return overrides
        return self.line_ids.filtered(lambda l: not l.date_override and l.weekday == weekday)

    @api.model
    def template_effective_on(self, roster_unit_id, a_date):
        """The single demand template effective for `roster_unit_id` on `a_date`."""
        return self.search([
            ('roster_unit_id', '=', roster_unit_id),
            ('effective_from', '<=', a_date),
            '|', ('effective_to', '=', False), ('effective_to', '>=', a_date),
        ], order='effective_from desc', limit=1)


class NhsDemandLine(models.Model):
    """One demand requirement: on this weekday (or this specific date, as a
    date-specific override), this shift type needs this many staff of this
    role/band, optionally with a specific skill (e.g. IV-competent)."""
    _name = 'nhs.demand.line'
    _description = 'Demand Line'
    _order = 'template_id, weekday, shift_type_id'

    template_id = fields.Many2one(
        'nhs.demand.template', string='Demand Template', required=True,
        ondelete='cascade', index=True)
    roster_unit_id = fields.Many2one(
        related='template_id.roster_unit_id', store=True, string='Unit')
    weekday = fields.Selection(
        WEEKDAYS, string='Weekday',
        help="Standing weekly requirement for this day of the week. Leave blank and set"
             " a specific date instead for a one-off override (escalation beds, winter"
             " uplift, a closure day)."
    )
    date_override = fields.Date(
        string='Specific Date (Override)',
        help="If set, this line applies only on this exact date, taking precedence over"
             " the standing weekday line for that day."
    )
    shift_type_id = fields.Many2one(
        'nhs.roster.shift.type', string='Shift Type', required=True,
        domain="[('roster_unit_id', '=', roster_unit_id)]")
    band_id = fields.Many2one('nhs.afc.band', string='Band')
    staff_group_id = fields.Many2one('nhs.staff.group', string='Role / Staff Group')
    required_headcount = fields.Integer(string='Required Headcount', required=True, default=1)
    required_skill_ids = fields.Many2many('nhs.roster.skill', string='Required Skills')
    notes = fields.Char(string='Notes')

    @api.constrains('weekday', 'date_override')
    def _check_weekday_or_date(self):
        for line in self:
            if not line.weekday and not line.date_override:
                raise ValidationError('Set either a weekday or a specific-date override.')

    @api.constrains('required_headcount')
    def _check_headcount(self):
        for line in self:
            if line.required_headcount < 1:
                raise ValidationError('Required headcount must be at least 1.')
