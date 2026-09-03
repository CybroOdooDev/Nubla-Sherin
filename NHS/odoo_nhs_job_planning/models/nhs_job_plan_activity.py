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
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
]
WEEKEND_DAYS = ('5', '6')
WEEK_PATTERNS = [
    ('every', 'Every Week'),
    ('a', 'Week A'),
    ('b', 'Week B'),
]
CLASSIFICATIONS = [
    ('dcc', 'Direct Clinical Care'),
    ('spa', 'Supporting Professional Activities'),
    ('additional', 'Additional Responsibility'),
    ('external', 'External Duty'),
]


class NhsJobPlanActivity(models.Model):
    """One line of a job plan's weekly timetable: a Programmed Activity on a
    given day, classified DCC/SPA/Additional/External."""
    _name = 'nhs.job.plan.activity'
    _description = 'Job Plan Timetable Activity'
    _order = 'weekday, sequence, time_start'
    _rec_name = 'activity'

    plan_id = fields.Many2one(
        'nhs.job.plan',
        string='Job Plan',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning job plan."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='plan_id.company_id',
        store=True,
        help="Owning company, from the plan."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Row order within the weekday."
    )
    weekday = fields.Selection(
        WEEKDAYS,
        string='Day',
        required=True,
        default='0',
        help="Day of the week this activity falls on."
    )
    week_pattern = fields.Selection(
        WEEK_PATTERNS,
        string='Week Pattern',
        required=True,
        default='every',
        help="Every week, or an alternating week-A/week-B pattern."
    )
    time_start = fields.Float(
        string='Start Time',
        help="Session start time (24h)."
    )
    time_end = fields.Float(
        string='End Time',
        help="Session end time (24h)."
    )
    is_premium_time = fields.Boolean(
        string='Premium Time',
        compute='_compute_is_premium_time',
        store=True,
        help="Weekend, or evening/early session per the company's configured"
             " threshold hour."
    )
    activity = fields.Char(
        string='Activity',
        required=True,
        help="e.g. 'Outpatient clinic', 'Theatre list', 'Ward round', 'CPD'."
    )
    session_category_id = fields.Many2one(
        'nhs.job.plan.session.category',
        string='Session Category',
        help="Optional normalised category; defaults the classification."
    )
    classification = fields.Selection(
        CLASSIFICATIONS,
        string='Classification',
        required=True,
        default='dcc',
        help="DCC / SPA / Additional Responsibility / External Duty."
    )
    location = fields.Char(
        string='Location',
        help="Site/clinic."
    )
    pa_value = fields.Float(
        string='PA Value',
        required=True,
        default=1.0,
        digits=(16, 2),
        help="PAs for the line (4-hour nominal session; fractional allowed)."
    )
    is_annualised = fields.Boolean(
        string='Annualised',
        help="Tick for a line whose nominal PA value is scaled by a frequency"
             " factor rather than occurring literally every week."
    )
    frequency_factor = fields.Float(
        string='Frequency Factor',
        default=1.0,
        digits=(16, 2),
        help="Applied to pa_value when Annualised is ticked, e.g. 0.5 for a"
             " fortnightly session."
    )
    effective_pa_value = fields.Float(
        string='Effective PA Value',
        compute='_compute_effective_pa_value',
        store=True,
        digits=(16, 2),
        help="pa_value scaled by the annualised frequency factor and, for"
             " week-A/week-B lines, by 0.5. This is the figure summed into"
             " the job plan's DCC/SPA/Additional/External totals."
    )
    notes = fields.Text(
        string='Notes',
        help="Free-text notes on this activity line."
    )

    @api.depends('weekday', 'time_start', 'time_end', 'plan_id.company_id.nhs_jobplan_evening_start_hour')
    def _compute_is_premium_time(self):
        """Weekend lines are always premium time; weekday lines are premium
        time if they start at/after the configured evening threshold."""
        for line in self:
            evening_hour = line.plan_id.company_id.nhs_jobplan_evening_start_hour or 18.5
            line.is_premium_time = line.weekday in WEEKEND_DAYS or (
                bool(line.time_start) and line.time_start >= evening_hour)

    @api.depends('pa_value', 'frequency_factor', 'is_annualised', 'week_pattern')
    def _compute_effective_pa_value(self):
        """The PA value actually counted into the plan's totals."""
        for line in self:
            value = line.pa_value or 0.0
            if line.is_annualised:
                value *= (line.frequency_factor or 1.0)
            if line.week_pattern in ('a', 'b'):
                value *= 0.5
            line.effective_pa_value = value

    @api.onchange('session_category_id')
    def _onchange_session_category_id(self):
        """Default the classification from the picked session category."""
        if self.session_category_id:
            if self.session_category_id.default_classification:
                self.classification = self.session_category_id.default_classification

    @api.constrains('time_start', 'time_end')
    def _check_times(self):
        """The end time must fall after the start time when both are set."""
        for line in self:
            if line.time_start and line.time_end and line.time_end <= line.time_start:
                raise ValidationError('End time must be after start time on a timetable line!')
