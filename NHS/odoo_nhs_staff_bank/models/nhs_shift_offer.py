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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class NhsShiftOffer(models.Model):
    """An offer of one open shift to one bank member — broadcast or targeted.
    `eligible` is snapshotted at creation time as an audit record of whether
    the member was eligible+compliant when the offer was made."""
    _name = 'nhs.shift.offer'
    _description = 'Shift Offer'
    _order = 'offered_at desc'

    shift_id = fields.Many2one(
        'nhs.bank.shift',
        string='Shift',
        required=True,
        ondelete='cascade',
        index=True,
        help="The shift offered."
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

    @api.model_create_multi
    def create(self, vals_list):
        """Snapshot eligibility at creation, as the offer-time audit record."""
        gate = self.env['nhs.compliance.gate']
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
                raise UserError(_("This offer has already been responded to."))
            existing = self.env['nhs.shift.booking'].search([
                ('member_id', '=', offer.member_id.id),
                ('state', 'in', ('booked', 'worked')),
                ('shift_start', '<', offer.shift_id.shift_end),
                ('shift_end', '>', offer.shift_id.shift_start),
            ])
            if existing:
                raise UserError(_(
                    "%s already has a booking that overlaps this shift.") % offer.member_id.name)
            if offer.shift_id.filled_count >= offer.shift_id.headcount:
                raise UserError(_("This shift is already fully booked."))
            offer.write({'response': 'accepted', 'responded_at': fields.Datetime.now()})
            self.env['nhs.shift.booking'].create({
                'shift_id': offer.shift_id.id,
                'member_id': offer.member_id.id,
            })
            # Any other still-pending offers for the same shift/member become moot
            # once headcount is reached; leave them for the coordinator to withdraw
            # explicitly if the shift is now full, via the shift's own state.

    def action_decline(self, reason=None):
        for offer in self:
            if offer.response != 'pending':
                raise UserError(_("This offer has already been responded to."))
            offer.write({
                'response': 'declined',
                'responded_at': fields.Datetime.now(),
                'decline_reason': reason or offer.decline_reason,
            })

    def action_withdraw(self):
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
