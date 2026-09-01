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
from odoo import api, fields, models
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
    _rec_name = 'member_id'


    is_manager = fields.Boolean(compute='_compute_is_manager')

    def _compute_is_manager(self):
        is_mgr = self.env.user.has_group('odoo_nhs_rostering.group_nhs_roster_manager')
        for rec in self:
            rec.is_manager = is_mgr

    def _default_member_id(self):
        member = self.env['nhs.workforce.member'].search([('user_id', '=', self.env.uid)], limit=1)
        if member:
            return member.id
        if self.env.user.email:
            member = self.env['nhs.workforce.member'].search([('email', '=ilike', self.env.user.email)], limit=1)
            if member:
                return member.id
        member = self.env['nhs.workforce.member'].search([('name', '=ilike', self.env.user.name)], limit=1)
        return member.id if member else False

    member_id = fields.Many2one(
        'nhs.workforce.member', string='Member', required=True, tracking=True, index=True, help="Member",
        default=_default_member_id)
    company_id = fields.Many2one(
        'res.company', related='member_id.company_id', store=True,
        help="Detailed information about this field")
    leave_type_id = fields.Many2one(
        'nhs.leave.type', string='Leave Type', required=True, tracking=True, help="Leave Type")
    date_from = fields.Date(string='From', required=True, tracking=True, help="From")
    date_to = fields.Date(string='To', required=True, tracking=True, help="To")
    hours = fields.Float(
        string='Hours', compute='_compute_hours', store=True, digits=(16, 2),
        help="Estimated from the member's contracted weekly hours over the weekdays"
             " covered (Mon-Fri) - an approximation, not a shift-by-shift calculation.")
    reason = fields.Text(string='Reason', help="Reason")
    state = fields.Selection(
        LEAVE_STATES, string='Status', required=True, default='draft', tracking=True, help="Status")
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, help="Approved By")
    approved_at = fields.Datetime(string='Approved At', readonly=True, help="Approved At")
    rejection_reason = fields.Char(string='Rejection Reason', help="Rejection Reason")
    capacity_override = fields.Boolean(
        string='Capacity Overridden', readonly=True, copy=False,
        help="Approved despite breaching the unit's leave-capacity limit, by a"
             " Workforce Admin with a logged reason - a deliberate, audited exception"
             " rather than a silent bypass.")
    capacity_override_reason = fields.Char(
        string='Override Reason',
        help="Required before this request can be Force Approved past the unit's"
             " leave-capacity limit.")
    capacity_override_by_id = fields.Many2one(
        'res.users', string='Overridden By', readonly=True, copy=False, help="Overridden By")

    @api.depends('date_from', 'date_to', 'member_id.contracted_weekly_hours')
    def _compute_hours(self):
        """ Method for compute hours """
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
        """ Method for check dates """
        for request in self:
            if request.date_to < request.date_from:
                raise ValidationError('End date must be on or after the start date.')

    def action_submit(self):
        """ Method for action submit """
        self.filtered(lambda r: r.state == 'draft').write({'state': 'submitted'})

    def action_approve(self):
        """ Method for action approve """
        if any(request.state != 'submitted' for request in self):
            raise UserError(('Only a submitted request can be approved.'))
        for request in self:
            breach = request._leave_capacity_breach()
            if breach:
                raise UserError(breach)
        self.write({
            'state': 'approved', 'approved_by': self.env.user.id,
            'approved_at': fields.Datetime.now(),
        })

    def action_force_approve(self):
        """Approve past the unit's leave-capacity limit. Restricted to
        Workforce Admins and only with a logged reason, so a breach is a
        deliberate, auditable management call rather than a silent bypass -
        mirrors the hard/soft gate pattern used for Staff Bank's compliance
        gate elsewhere in the suite."""
        if any(request.state != 'submitted' for request in self):
            raise UserError(('Only a submitted request can be approved.'))
        if not self.env.user.has_group('odoo_nhs_rostering.group_nhs_workforce_admin'):
            raise UserError((
                'Only a Workforce Admin can force-approve past the leave-capacity'
                ' limit.'))
        if any(not request.capacity_override_reason for request in self):
            raise UserError((
                'Enter an Override Reason before force-approving past the'
                ' leave-capacity limit.'))
        for request in self:
            breach = request._leave_capacity_breach()
            request.message_post(body=
                'Leave capacity limit overridden by %(user)s: %(reason)s%(breach)s',
                user=self.env.user.name, reason=request.capacity_override_reason,
                breach=(' (%s)' % breach) if breach else '')
        self.write({
            'state': 'approved', 'approved_by': self.env.user.id,
            'approved_at': fields.Datetime.now(),
            'capacity_override': True,
            'capacity_override_by_id': self.env.user.id,
        })

    def action_reject(self, reason=None):
        """ Method for action reject """
        vals = {'state': 'rejected'}
        if reason:
            vals['rejection_reason'] = reason
        self.write(vals)

    def action_cancel(self):
        """ Method for action cancel """
        self.write({'state': 'cancelled'})

    def _leave_capacity_breach(self):
        """Return the first capacity-breach message for this request across
        its date range, or False if approving it would stay within the
        unit's configured leave_capacity_pct. Used by both action_approve
        (which blocks on it) and action_force_approve (which logs it)."""
        self.ensure_one()
        roster_unit = self.member_id.org_unit_id.roster_unit_ids[:1]
        if not roster_unit or not roster_unit.leave_capacity_pct:
            return False
        team_size = roster_unit.member_count
        if not team_size:
            return False
        a_date = self.date_from
        while a_date <= self.date_to:
            concurrent = self.search_count([
                ('member_id', 'in', roster_unit.member_ids.ids),
                ('state', '=', 'approved'),
                ('date_from', '<=', a_date), ('date_to', '>=', a_date),
                ('id', '!=', self.id),
            ])
            pct = (concurrent + 1) / team_size * 100.0
            if pct > roster_unit.leave_capacity_pct:
                return (
                    'Approving this request would put %.0f%% of %s on leave on %s'
                    ' (limit %.0f%%).') % (
                        pct, roster_unit.display_name, a_date, roster_unit.leave_capacity_pct)
            a_date += timedelta(days=1)
        return False
