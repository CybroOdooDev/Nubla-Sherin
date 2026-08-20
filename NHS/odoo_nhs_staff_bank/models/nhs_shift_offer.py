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
from odoo.exceptions import UserError, ValidationError


class NhsShiftOffer(models.Model):
    """An offer of one open shift to one bank member — broadcast or targeted.
    `eligible` is snapshotted at creation time as an audit record of whether
    the member was eligible+compliant when the offer was made."""
    _name = 'nhs.shift.offer'
    _description = 'Shift Offer'
    _order = 'offered_at desc'
    _rec_name = 'member_id'



    shift_id = fields.Many2one(
        'nhs.bank.shift',
        string='Shift',
        required=True,
        ondelete='cascade',
        index=True,
        domain="[('state', 'in', ('open', 'partially_filled'))]",
        help="The shift offered. Only open/partially-filled shifts can be offered —"
             " a draft shift hasn't been opened to the bank yet, and a filled one"
             " no longer needs offers."
    )
    member_id = fields.Many2one(
        'nhs.bank.member',
        string='Member',
        required=True,
        index=True,
        help="Member offered."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='shift_id.company_id',
        store=True,
    )
    company_booking_mode = fields.Selection(
        related='company_id.nhs_bank_booking_mode',
        string='Company Booking Mode',
    )
    offered_at = fields.Datetime(
        string='Offered At',
        default=fields.Datetime.now,
        help="When offered."
    )
    expiry_datetime = fields.Datetime(
        string='Expires At',
        help="When this offer auto-expires if not responded to."
    )
    response = fields.Selection([
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
    ], string='Response', required=True, default='pending',
        help="Member's response to the offer."
    )
    responded_at = fields.Datetime(
        string='Responded At',
    )
    eligible = fields.Boolean(
        string='Eligible at Offer',
        help="Whether the member was eligible+compliant at offer time (audit snapshot,"
             " never recomputed)."
    )
    eligibility_reasons = fields.Char(
        string='Ineligibility Reasons',
        help="Reasons the member was ineligible at offer time, if any."
    )
    decline_reason = fields.Char(
        string='Decline Reason',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    eligible_member_ids = fields.Many2many(
        'nhs.bank.member',
        compute='_compute_eligible_member_ids',
        help="Technical field for UI domain filtering."
    )

    @api.depends('shift_id')
    def _compute_eligible_member_ids(self):
        for offer in self:
            if offer.shift_id:
                outcomes = offer.shift_id.get_eligible_members()
                offer.eligible_member_ids = [o['member'].id for o in outcomes if o['eligible']]
            else:
                offer.eligible_member_ids = False

    @api.onchange('member_id')
    def _onchange_member_id(self):
        """Restrict the Shift field to shifts this member is actually
        eligible for (role/band + skills + area + available + compliant),
        mirroring the eligibility check the offer wizard already applies
        in the other direction."""
        if self.member_id:
            eligible_shifts = self.member_id.get_eligible_shifts()
            if self.shift_id and self.shift_id not in eligible_shifts:
                self.shift_id = False
            return {'domain': {'shift_id': [('id', 'in', eligible_shifts.ids)]}}
        return {'domain': {'shift_id': []}}

    @api.onchange('shift_id')
    def _onchange_shift_id(self):
        """Restrict the Member field to members who are actually eligible
        for this shift."""
        if self.shift_id:
            eligible_outcomes = self.shift_id.get_eligible_members()
            eligible_member_ids = [outcome['member'].id for outcome in eligible_outcomes if outcome['eligible']]
            if self.member_id and self.member_id.id not in eligible_member_ids:
                self.member_id = False
            return {'domain': {'member_id': [('id', 'in', eligible_member_ids)]}}
        return {'domain': {'member_id': []}}

    @api.model_create_multi
    def create(self, vals_list):
        """Snapshot eligibility at creation, as the offer-time audit record.
        Also guards that an offer can only be made against a shift that's
        actually open for offers — the domain on shift_id is only a UI hint
        and can be bypassed (direct write, import, API), so it's enforced
        here too."""
        gate = self.env['nhs.compliance.gate']
        shift_ids = {vals['shift_id'] for vals in vals_list if vals.get('shift_id')}
        shifts = self.env['nhs.bank.shift'].browse(shift_ids)
        for shift in shifts:
            if shift.state not in ('open', 'partially_filled'):
                raise ValidationError(
                    "An offer can only be made for an open or partially-filled shift. "
                    "'%s' is currently '%s'." % (shift.display_name, shift.state)
                )
        for vals in vals_list:
            if 'eligible' not in vals and vals.get('shift_id') and vals.get('member_id'):
                shift = self.env['nhs.bank.shift'].browse(vals['shift_id'])
                member = self.env['nhs.bank.member'].browse(vals['member_id'])
                outcome = gate.eligibility(shift, member)
                vals['eligible'] = outcome['eligible']
                vals['eligibility_reasons'] = '; '.join(outcome['reasons'])
        return super().create(vals_list)

    def action_accept(self):
        """Member accepts: confirm/book the shift, preventing double-booking."""
        for offer in self:
            if offer.response != 'pending':
                raise UserError(("This offer has already been responded to."))
            existing = self.env['nhs.shift.booking'].search([
                ('member_id', '=', offer.member_id.id),
                ('state', 'in', ('booked', 'worked')),
                ('shift_start', '<', offer.shift_id.shift_end),
                ('shift_end', '>', offer.shift_id.shift_start),
            ])
            if existing:
                raise UserError((
                    "%s already has a booking that overlaps this shift.") % offer.member_id.name)
            if offer.shift_id.filled_count >= offer.shift_id.headcount:
                raise UserError(("This shift is already fully booked."))
            offer.write({'response': 'accepted', 'responded_at': fields.Datetime.now()})
            
            if offer.company_id.nhs_bank_booking_mode != 'manager_allocated':
                self.env['nhs.shift.booking'].create({
                    'shift_id': offer.shift_id.id,
                    'member_id': offer.member_id.id,
                })
            # Any other still-pending offers for the same shift/member become moot
            # once headcount is reached; leave them for the coordinator to withdraw
            # explicitly if the shift is now full, via the shift's own state.

    def action_allocate_booking(self):
        """Manager allocates an accepted offer to a booking (Manager-Allocated mode)."""
        if not self.env.user.has_group('odoo_nhs_staff_bank.group_nhs_bank_manager'):
            raise UserError("Only Bank Managers can manually allocate shifts.")
        for offer in self:
            if offer.response != 'accepted':
                raise UserError(("Can only allocate offers that have been accepted by the member."))
            existing = self.env['nhs.shift.booking'].search([
                ('member_id', '=', offer.member_id.id),
                ('state', 'in', ('booked', 'worked')),
                ('shift_start', '<', offer.shift_id.shift_end),
                ('shift_end', '>', offer.shift_id.shift_start),
            ])
            if existing:
                raise UserError((
                    "%s already has a booking that overlaps this shift.") % offer.member_id.name)
            if offer.shift_id.filled_count >= offer.shift_id.headcount:
                raise UserError(("This shift is already fully booked."))
            
            self.env['nhs.shift.booking'].create({
                'shift_id': offer.shift_id.id,
                'member_id': offer.member_id.id,
            })

    def action_decline(self, reason=None):
        """Member declines the offer, recording an optional reason."""
        for offer in self:
            if offer.response != 'pending':
                raise UserError(("This offer has already been responded to."))
            offer.write({
                'response': 'declined',
                'responded_at': fields.Datetime.now(),
                'decline_reason': reason or offer.decline_reason,
            })

    def action_withdraw(self):
        """Withdraw all still-pending offers in the set."""
        self.filtered(lambda o: o.response == 'pending').write({'response': 'withdrawn'})

    @api.model
    def _cron_expire_offers(self):
        """Scheduled action: pending offers past their expiry are auto-expired."""
        expired = self.search([
            ('response', '=', 'pending'),
            ('expiry_datetime', '!=', False),
            ('expiry_datetime', '<', fields.Datetime.now()),
        ])
        expired.write({'response': 'expired', 'responded_at': fields.Datetime.now()})
