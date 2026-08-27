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
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

LEAVE_STATES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled'),
]


class NhsLeaveRequest(models.Model):
    """Annual/study/other leave: requested by self-service, approved against
    the unit's leave-capacity rule, decrementing the member's entitlement
    (via the entitlement's own compute) and blocking assignment for the
    dates covered (the LEAVE_CONFLICT rule)."""
    _name = 'nhs.leave.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Leave Request'
    _order = 'date_from desc'

    member_id = fields.Many2one(
        'nhs.workforce.member', string='Member', required=True, tracking=True, index=True)
    company_id = fields.Many2one(
        'res.company', related='member_id.company_id', store=True)
    leave_type_id = fields.Many2one(
        'nhs.leave.type', string='Leave Type', required=True, tracking=True)
    date_from = fields.Date(string='From', required=True, tracking=True)
    date_to = fields.Date(string='To', required=True, tracking=True)
    hours = fields.Float(
        string='Hours', compute='_compute_hours', store=True, digits=(16, 2),
        help="Estimated from the member's contracted weekly hours over the weekdays"
             " covered (Mon-Fri) - an approximation, not a shift-by-shift calculation.")
    reason = fields.Text(string='Reason')
    state = fields.Selection(
        LEAVE_STATES, string='Status', required=True, default='draft', tracking=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_at = fields.Datetime(string='Approved At', readonly=True)
    rejection_reason = fields.Char(string='Rejection Reason')

    @api.depends('date_from', 'date_to', 'member_id.contracted_weekly_hours')
    def _compute_hours(self):
        for request in self:
            if not (request.date_from and request.date_to):
                request.hours = 0.0
                continue
            daily_hours = (request.member_id.contracted_weekly_hours or 37.5) / 5.0
            weekdays = 0
            a_date = request.date_from
            while a_date <= request.date_to:
                if a_date.weekday() < 5:
                    weekdays += 1
                a_date += timedelta(days=1)
            request.hours = round(weekdays * daily_hours, 2)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for request in self:
            if request.date_to < request.date_from:
                raise ValidationError('End date must be on or after the start date.')

    def action_submit(self):
        self.filtered(lambda r: r.state == 'draft').write({'state': 'submitted'})

    def action_approve(self):
        for request in self:
            if request.state != 'submitted':
                raise UserError(_('Only a submitted request can be approved.'))
            request._check_leave_capacity()
            request.write({
                'state': 'approved', 'approved_by': self.env.user.id,
                'approved_at': fields.Datetime.now(),
            })

    def action_reject(self, reason=None):
        for request in self:
            request.write({
                'state': 'rejected', 'rejection_reason': reason or request.rejection_reason,
            })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _check_leave_capacity(self):
        """Block approval if it would push the unit's simultaneous-absence
        percentage, on any day in the request's range, above the unit's
        configured leave_capacity_pct."""
        for request in self:
            roster_unit = request.member_id.org_unit_id.roster_unit_ids[:1]
            if not roster_unit or not roster_unit.leave_capacity_pct:
                continue
            team_size = roster_unit.member_count
            if not team_size:
                continue
            a_date = request.date_from
            while a_date <= request.date_to:
                concurrent = self.search_count([
                    ('member_id', 'in', roster_unit.member_ids.ids),
                    ('state', '=', 'approved'),
                    ('date_from', '<=', a_date), ('date_to', '>=', a_date),
                    ('id', '!=', request.id),
                ])
                pct = (concurrent + 1) / team_size * 100.0
                if pct > roster_unit.leave_capacity_pct:
                    raise UserError(_(
                        'Approving this request would put %.0f%% of %s on leave on %s'
                        ' (limit %.0f%%).') % (
                            pct, roster_unit.display_name, a_date, roster_unit.leave_capacity_pct))
                a_date += timedelta(days=1)
