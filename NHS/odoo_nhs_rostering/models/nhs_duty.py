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
from odoo.exceptions import ValidationError

DUTY_STATES = [
    ('draft', 'Draft'),
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
        ondelete='cascade', index=True, help="Roster Period")
    unit_id = fields.Many2one(
        'nhs.roster.unit', related='period_id.unit_id', store=True, string='Unit', help="Unit")
    company_id = fields.Many2one(
        'res.company', related='period_id.company_id', store=True, help="Detailed information about this field")
    duty_date = fields.Date(string='Date', required=True, index=True, help="Date")
    shift_type_id = fields.Many2one(
        'nhs.roster.shift.type', string='Shift Type', required=True,
        domain="[('roster_unit_id', '=', unit_id)]", help="Shift Type")
    demand_line_id = fields.Many2one(
        'nhs.demand.line', string='Demand Line', ondelete='set null',
        help="The demand requirement this slot exists to satisfy.")
    staff_group_id = fields.Many2one(
        'nhs.staff.group', string='Role / Staff Group',
        help="Required by the Staff Bank when this duty is pushed there. Copied from"
             " the demand line when generated from one; set it directly for a duty"
             " added manually (e.g. via 'Add a line'), which has no demand line.")
    required_band_id = fields.Many2one('nhs.afc.band', string='Required Band', help="Required Band")
    required_skill_ids = fields.Many2many('nhs.roster.skill', string='Required Skills',
                                          help="Required Skills")
    required_headcount = fields.Integer(string='Required Headcount', default=1, help="Required Headcount")
    assignment_ids = fields.One2many('nhs.duty.assignment', 'duty_id', string='Assignments',
                                     help="Assignments")
    assigned_count = fields.Integer(
        string='Assigned', compute='_compute_assigned_count', store=True, help="Assigned")
    state = fields.Selection(
        DUTY_STATES, string='Status', compute='_compute_state', store=True, help="Status")
    is_cancelled = fields.Boolean(string='Cancelled', help="Cancelled")
    escalation_ids = fields.One2many(
        'nhs.roster.escalation', 'duty_id', string='Escalations',
        help="Every escalation ever raised for this duty.")
    escalation_id = fields.Many2one(
        'nhs.roster.escalation', string='Escalation', compute='_compute_escalation_id',
        store=True, help="Escalation")
    bank_filled_count = fields.Integer(
        related='escalation_id.bank_filled_count', string='Bank Filled',
        help="Confirmed bookings on the linked bank shift, as of the last sync - see"
             " nhs.roster.escalation.bank_filled_count.")
    is_overstaffed = fields.Boolean(
        string='Overstaffed', compute='_compute_is_overstaffed',
        help="True when direct roster assignments and the linked bank shift's confirmed"
             " bookings, added together, exceed this duty's required headcount. The two"
             " are filled independently and never reconciled automatically (Staff Bank is"
             " only a soft link, refreshed by 'Sync from Bank' or its cron) - this flags an"
             " overlap for a human to resolve, e.g. by reducing the bank shift's headcount"
             " or standing down a bank offer.")
    notes = fields.Char(string='Notes', help="e.g. 'supervisory', 'supernumerary'.")
    display_name = fields.Char(compute='_compute_display_name', help="Detailed information about this field")
    eligible_member_ids = fields.Many2many(
        'nhs.workforce.member', compute='_compute_eligible_member_ids',
        help="This duty's unit's team (including secondary members), further narrowed to"
             " those who actually meet this duty's Required Band and Required Skills, if"
             " set - the same match the hard SKILL_MIX rule enforces at save time, just"
             " applied here as the Member domain so a non-matching person never shows in"
             " the picker in the first place.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'period_id' in vals:
                period = self.env['nhs.roster.period'].browse(vals['period_id'])
                if period.state not in ('draft', 'in_progress'):
                    from odoo.exceptions import ValidationError
                    raise ValidationError("You can only create duties when the Roster Period is 'Draft' or 'In Progress'.")
        return super().create(vals_list)

    @api.depends('unit_id', 'required_band_id', 'required_skill_ids')
    def _compute_eligible_member_ids(self):
        """ Method for compute eligible member ids """
        for duty in self:
            members = self.env['nhs.workforce.member'].search([('is_leaver', '=', False)])
            if duty.required_band_id:
                req_band_id = duty.required_band_id._origin.id or duty.required_band_id.id
                members = members.filtered(
                    lambda m: not m.band_id or m.band_id.id == req_band_id)
            if duty.required_skill_ids:
                req_skill_ids = set(duty.required_skill_ids._origin.ids or duty.required_skill_ids.ids)
                members = members.filtered(
                    lambda m: req_skill_ids.issubset(set(m.roster_skill_ids.ids)))
            duty.eligible_member_ids = members

    @api.depends('assignment_ids.state')
    def _compute_assigned_count(self):
        """ Method for compute assigned count """
        for duty in self:
            duty.assigned_count = len(
                duty.assignment_ids.filtered(lambda a: a.state in ACTIVE_ASSIGNMENT_STATES))

    @api.depends('is_cancelled', 'assigned_count', 'required_headcount',
                 'escalation_id.state')
    def _compute_state(self):
        """ Method for compute state """
        for duty in self:
            if not duty.id:
                # Not saved yet (e.g. the "Create Duties" popup before the
                # first save) - nothing has actually been created, so this
                # isn't genuinely "Unfilled" yet.
                duty.state = 'draft'
            elif duty.is_cancelled:
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

    @api.depends('is_cancelled', 'assigned_count', 'required_headcount',
                 'escalation_id.bank_filled_count')
    def _compute_is_overstaffed(self):
        """ Method for compute is overstaffed """
        for duty in self:
            total_cover = duty.assigned_count + duty.escalation_id.bank_filled_count
            duty.is_overstaffed = (
                not duty.is_cancelled and duty.required_headcount
                and total_cover > duty.required_headcount)

    @api.depends('escalation_ids.state')
    def _compute_escalation_id(self):
        """ Method for compute escalation id """
        for duty in self:
            active = duty.escalation_ids.filtered(lambda e: e.state != 'cancelled')
            duty.escalation_id = active[:1]

    @api.depends('duty_date', 'shift_type_id.name', 'unit_id.display_name')
    def _compute_display_name(self):
        """ Method for compute display name """
        for duty in self:
            duty.display_name = '%s — %s — %s' % (
                duty.unit_id.display_name or '', fields.Date.to_string(duty.duty_date) or '',
                duty.shift_type_id.name or '')

    @api.constrains('duty_date', 'period_id')
    def _check_duty_date_within_period(self):
        """ Method for check duty date within period """
        for duty in self:
            period = duty.period_id
            if period.date_start and period.date_end and not (
                    period.date_start <= duty.duty_date <= period.date_end):
                raise ValidationError(
                    'Duty date %s falls outside the roster period (%s to %s).' % (
                        fields.Date.to_string(duty.duty_date),
                        fields.Date.to_string(period.date_start),
                        fields.Date.to_string(period.date_end)))

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
        """ Method for action cancel """
        self.write({'is_cancelled': True})
        self.mapped('assignment_ids').filtered(
            lambda a: a.state not in ('worked', 'dna')).write({'state': 'cancelled'})

    def action_reinstate(self):
        """ Method for action reinstate """
        self.write({'is_cancelled': False})

    def action_escalate_to_bank(self):
        """Open the Escalate Unfilled Duties wizard pre-filled with this
        duty - a shortcut so a gap can be pushed to the bank straight from
        the duty record (e.g. the roster-grid popup), without leaving to
        the Gaps & Escalation list to use the bulk action there."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.escalate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_duty_ids': [(6, 0, [self.id])]},
        }
