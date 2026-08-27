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
from datetime import datetime, timedelta

from odoo import api, fields, models

DUTY_STATES = [
    ('unfilled', 'Unfilled'),
    ('partially_filled', 'Partially Filled'),
    ('filled', 'Filled'),
    ('escalated', 'Escalated'),
    ('covered_bank', 'Covered (Bank)'),
    ('covered_agency', 'Covered (Agency)'),
    ('cancelled', 'Cancelled'),
]

ACTIVE_ASSIGNMENT_STATES = ('assigned', 'published', 'worked', 'changed')


class NhsDuty(models.Model):
    """A duty slot: on this date, this shift, this many staff of this
    role/band/skill are required - the demand line's requirement made
    concrete for one specific day. Assignment records fill it, up to
    required_headcount."""
    _name = 'nhs.duty'
    _description = 'Duty Slot'
    _order = 'duty_date, shift_type_id'

    period_id = fields.Many2one(
        'nhs.roster.period', string='Roster Period', required=True,
        ondelete='cascade', index=True)
    unit_id = fields.Many2one(
        'nhs.roster.unit', related='period_id.unit_id', store=True, string='Unit')
    company_id = fields.Many2one(
        'res.company', related='period_id.company_id', store=True)
    duty_date = fields.Date(string='Date', required=True, index=True)
    shift_type_id = fields.Many2one(
        'nhs.roster.shift.type', string='Shift Type', required=True,
        domain="[('roster_unit_id', '=', unit_id)]")
    demand_line_id = fields.Many2one(
        'nhs.demand.line', string='Demand Line', ondelete='set null',
        help="The demand requirement this slot exists to satisfy.")
    required_band_id = fields.Many2one('nhs.afc.band', string='Required Band')
    required_skill_ids = fields.Many2many('nhs.roster.skill', string='Required Skills')
    required_headcount = fields.Integer(string='Required Headcount', default=1)
    assignment_ids = fields.One2many('nhs.duty.assignment', 'duty_id', string='Assignments')
    assigned_count = fields.Integer(
        string='Assigned', compute='_compute_assigned_count', store=True)
    state = fields.Selection(
        DUTY_STATES, string='Status', compute='_compute_state', store=True)
    is_cancelled = fields.Boolean(string='Cancelled')
    escalation_id = fields.Many2one(
        'nhs.roster.escalation', string='Escalation', compute='_compute_escalation_id',
        store=True)
    notes = fields.Char(string='Notes', help="e.g. 'supervisory', 'supernumerary'.")
    display_name = fields.Char(compute='_compute_display_name')

    @api.depends('assignment_ids.state')
    def _compute_assigned_count(self):
        for duty in self:
            duty.assigned_count = len(
                duty.assignment_ids.filtered(lambda a: a.state in ACTIVE_ASSIGNMENT_STATES))

    @api.depends('is_cancelled', 'assigned_count', 'required_headcount',
                 'escalation_id.state')
    def _compute_state(self):
        for duty in self:
            if duty.is_cancelled:
                duty.state = 'cancelled'
            elif duty.escalation_id.state == 'bank_filled':
                duty.state = 'covered_bank'
            elif duty.escalation_id.state == 'agency_filled':
                duty.state = 'covered_agency'
            elif duty.escalation_id.state in ('pushed_to_bank', 'offered', 'to_agency'):
                duty.state = 'escalated'
            elif duty.required_headcount and duty.assigned_count >= duty.required_headcount:
                duty.state = 'filled'
            elif duty.assigned_count > 0:
                duty.state = 'partially_filled'
            else:
                duty.state = 'unfilled'

    def _compute_escalation_id(self):
        Escalation = self.env['nhs.roster.escalation']
        for duty in self:
            duty.escalation_id = Escalation.search([
                ('duty_id', '=', duty.id), ('state', '!=', 'cancelled'),
            ], order='id desc', limit=1)

    @api.depends('duty_date', 'shift_type_id.name', 'unit_id.display_name')
    def _compute_display_name(self):
        for duty in self:
            duty.display_name = '%s — %s — %s' % (
                duty.unit_id.display_name or '', fields.Date.to_string(duty.duty_date) or '',
                duty.shift_type_id.name or '')

    def get_datetime_bounds(self):
        """(start, end) naive datetimes for this duty, combining duty_date with
        the shift type's start/end times - handling shifts that span midnight."""
        self.ensure_one()
        shift_type = self.shift_type_id
        base = datetime.combine(self.duty_date, datetime.min.time())
        start = base + timedelta(hours=shift_type.time_start or 0.0)
        end = base + timedelta(hours=shift_type.time_end or 0.0)
        if shift_type.time_end <= shift_type.time_start:
            end += timedelta(days=1)
        return start, end

    def action_cancel(self):
        self.write({'is_cancelled': True})
        self.mapped('assignment_ids').filtered(
            lambda a: a.state not in ('worked', 'dna')).write({'state': 'cancelled'})

    def action_reinstate(self):
        self.write({'is_cancelled': False})
