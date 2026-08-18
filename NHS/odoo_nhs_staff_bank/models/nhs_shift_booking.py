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
from odoo.exceptions import UserError


class NhsShiftBooking(models.Model):
    """A confirmed booking of a bank member onto a shift, and its worked
    outcome. Compliance is re-checked at booking time (it may have lapsed
    since the offer) and `compliant_at_booking` is snapshotted as the audit
    evidence that the worker was compliant when booked, regardless of the
    gate policy. No hard delete — bookings are archived to preserve the pay
    and compliance audit trail."""
    _name = 'nhs.shift.booking'
    _inherit = ['mail.thread']
    _description = "A confirmed booking, and its worked outcome"
    _order = 'shift_start desc'

    name = fields.Char(
        string='Booking Reference',
        copy=False,
        readonly=True,
        default='New',
        help="Booking reference, sequenced."
    )
    shift_id = fields.Many2one(
        'nhs.bank.shift',
        string='Shift',
        required=True,
        index=True,
        help="The shift booked."
    )
    member_id = fields.Many2one(
        'nhs.bank.member',
        string='Member',
        required=True,
        index=True,
        tracking=True,
        help="Booked member."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='shift_id.company_id',
        store=True,
    )
    shift_start = fields.Datetime(
        string='Start',
        help="Booked start time (defaults from the shift; may be adjusted)."
    )
    shift_end = fields.Datetime(
        string='End',
        help="Booked end time (defaults from the shift; may be adjusted)."
    )
    state = fields.Selection([
        ('booked', 'Booked'),
        ('worked', 'Worked'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ], string='Status', required=True, default='booked', tracking=True,
        help="booked -> worked (attended), or no_show / cancelled."
    )
    compliant_at_booking = fields.Boolean(
        string='Compliant at Booking',
        readonly=True,
        help="Snapshot: the member was compliant when this booking was confirmed"
             " (audit evidence, never recomputed)."
    )
    actual_start = fields.Datetime(
        string='Actual Start',
        help="Actual worked start time."
    )
    actual_end = fields.Datetime(
        string='Actual End',
        help="Actual worked end time."
    )
    rate_id = fields.Many2one(
        'nhs.bank.rate',
        string='Rate Applied',
        help="Rate card line applied to compute the payable amount."
    )
    rate_override = fields.Monetary(
        string='Rate Override',
        currency_field='currency_id',
        help="Exceptional flat payable-amount override, with a reason."
    )
    rate_override_reason = fields.Char(
        string='Override Reason',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
    )
    payable_amount = fields.Monetary(
        string='Payable Amount',
        compute='_compute_payable_amount',
        store=True,
        currency_field='currency_id',
        help="hours x rate (+ enhancements), or the override when set."
    )
    authorised_by_id = fields.Many2one(
        'res.users',
        string='Authorised By',
        help="Manager who authorised the worked shift for pay."
    )
    authorised_at = fields.Datetime(
        string='Authorised At',
    )
    fill_source = fields.Selection([
        ('bank', 'Bank'),
    ], string='Fill Source', default='bank',
        help="This booking's contribution to the bank-vs-agency dataset (agency"
             " fills are captured directly on the shift, not as a booking)."
    )
    cancel_reason = fields.Char(
        string='Cancel Reason',
    )
    working_time_breach = fields.Boolean(
        string='Working-Time Breach Warning',
        compute='_compute_working_time_breach',
        store=True,
        help="This booking would push the member over their safe/legal weekly"
             " hours limit (substantive + bank)."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag — bookings are never hard-deleted, to preserve the pay"
             " and compliance audit trail."
    )

    @api.onchange('shift_id')
    def _onchange_shift_id(self):
        """Default the booked start/end times from the shift when it is set."""
        for booking in self:
            if booking.shift_id:
                booking.shift_start = booking.shift_id.shift_start
                booking.shift_end = booking.shift_id.shift_end

    @api.depends('shift_start', 'shift_end', 'actual_start', 'actual_end',
                 'rate_id', 'rate_override')
    def _compute_payable_amount(self):
        """Compute hours x rate (+ enhancements) as the payable amount, or use
        the flat override when one is set."""
        for booking in self:
            if booking.rate_override:
                booking.payable_amount = booking.rate_override
                continue
            start = booking.actual_start or booking.shift_start
            end = booking.actual_end or booking.shift_end
            if not (start and end) or not booking.rate_id:
                booking.payable_amount = 0.0
                continue
            hours = (end - start).total_seconds() / 3600.0
            booking.payable_amount = booking.rate_id.compute_payable(hours)

    @api.depends('member_id', 'shift_start', 'shift_end')
    def _compute_working_time_breach(self):
        """Flag when this booking's hours, added to the member's other booked/
        substantive hours in the rolling 7 days up to the shift, would breach
        the safe/legal weekly limit."""
        for booking in self:
            if not (booking.member_id and booking.shift_start and booking.shift_end):
                booking.working_time_breach = False
                continue
            hours = (booking.shift_end - booking.shift_start).total_seconds() / 3600.0
            window_start = booking.shift_end - timedelta(days=7)
            booking.working_time_breach = booking.member_id.check_working_time_breach(
                hours, window_start, booking.shift_end)

    @api.model_create_multi
    def create(self, vals_list):
        """Assign a sequence reference, default times from the shift, enforce
        the compliance gate (hard/soft per company policy) and snapshot
        compliant_at_booking as the audit trail."""
        gate = self.env['nhs.compliance.gate']
        hard_gate = self.env.company.nhs_bank_gate_policy == 'hard'
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('nhs.shift.booking') or 'New'
            shift = self.env['nhs.bank.shift'].browse(vals.get('shift_id'))
            member = self.env['nhs.bank.member'].browse(vals.get('member_id'))
            if shift and not vals.get('shift_start'):
                vals['shift_start'] = shift.shift_start
            if shift and not vals.get('shift_end'):
                vals['shift_end'] = shift.shift_end
            if member:
                compliant, _reason = gate.is_member_compliant_with_reason(member)
                vals['compliant_at_booking'] = compliant
                if not compliant and hard_gate:
                    raise UserError((
                        "%(member)s cannot be booked: %(reason)s") % {
                        'member': member.name, 'reason': _reason})
        return super().create(vals_list)

    def unlink(self):
        """Block hard deletion of bookings; cancel instead to preserve the audit trail."""
        raise UserError((
            "Bookings cannot be deleted, to preserve the pay and compliance audit"
            " trail. Cancel the booking instead."))

    def action_confirm_worked(self):
        """Confirm the shift as worked (attended), defaulting actual times to
        the booked times when not otherwise entered."""
        for booking in self:
            booking.write({
                'state': 'worked',
                'actual_start': booking.actual_start or booking.shift_start,
                'actual_end': booking.actual_end or booking.shift_end,
            })

    def action_no_show(self):
        """Mark the booking as a no-show."""
        self.write({'state': 'no_show'})

    def action_authorise(self):
        """Record who authorised the worked shift for pay, and when."""
        for booking in self:
            booking.write({
                'authorised_by_id': self.env.user.id,
                'authorised_at': fields.Datetime.now(),
            })

    def action_cancel(self, reason=None):
        """Cancel the booking and reopen the shift for a fresh offer."""
        for booking in self:
            booking.write({'state': 'cancelled', 'cancel_reason': reason or booking.cancel_reason})
            booking.shift_id._compute_filled_count()
