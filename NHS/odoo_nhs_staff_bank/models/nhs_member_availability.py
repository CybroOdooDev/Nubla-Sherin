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


class NhsMemberAvailability(models.Model):
    """When a bank member is available (or explicitly unavailable/blackout)
    to work, so offers only go to people who can actually work."""
    _name = 'nhs.member.availability'
    _description = 'Bank Member Availability'
    _order = 'date_from desc'
    _rec_name = 'member_id'

    member_id = fields.Many2one(
        'nhs.bank.member',
        string='Member',
        required=True,
        ondelete='cascade',
        index=True,
        help="The member this availability record belongs to."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='member_id.company_id',
        store=True,
        help="Company of the member, mirrored for filtering."
    )
    date_from = fields.Datetime(
        string='From',
        required=True,
        help="Start of the available (or unavailable) window."
    )
    date_to = fields.Datetime(
        string='To',
        required=True,
        help="End of the available (or unavailable) window."
    )
    availability_type = fields.Selection([
        ('available', 'Available'),
        ('unavailable', 'Unavailable (Blackout)'),
    ], string='Type', required=True, default='available',
        help="Whether this window declares the member available, or explicitly"
             " unavailable (a blackout, e.g. annual leave)."
    )
    recurring = fields.Boolean(
        string='Recurring',
        help="Recurring weekly pattern (e.g. every Saturday) rather than a single window."
    )
    weekday = fields.Selection(
        WEEKDAYS,
        string='Weekday',
        help="Day of the week this recurs on, when Recurring is set."
    )
    recurrence_end_date = fields.Date(
        string='Recurs Until',
        help="Last date the recurring pattern applies, when Recurring is set."
    )
    note = fields.Char(
        string='Note',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Only an active bank member can have availability declared —
        a member still in Draft (or Suspended/Inactive) isn't confirmed
        yet, so availability windows for them wouldn't mean anything.
        This also gates the portal self-service form, which creates
        these records via sudo()."""
        member_ids = {vals['member_id'] for vals in vals_list if vals.get('member_id')}
        members = self.env['nhs.bank.member'].browse(member_ids)
        state_labels = dict(members._fields['state'].selection)
        for member in members:
            if member.state != 'active':
                raise ValidationError(
                    "Availability can only be added for an active bank member. "
                    "'%s' is currently '%s'." % (member.name, state_labels.get(member.state, member.state))
                )
        return super().create(vals_list)

    @api.constrains('date_from', 'date_to', 'recurrence_end_date', 'recurring')
    def _check_dates(self):
        """Reject a window whose end is not after its start, or whose start
        is already in the past — an availability/blackout window only makes
        sense for a future (or currently-open) period."""
        now = fields.Datetime.now()
        for record in self:
            if record.date_to <= record.date_from:
                raise ValidationError("'To' must be after 'From'.")
            if record.date_from < now:
                raise ValidationError("'From' cannot be in the past.")
            if record.recurring and record.recurrence_end_date:
                if record.recurrence_end_date < record.date_from.date():
                    raise ValidationError("'Recurs Until' date cannot be before the 'From' date.")

    @api.constrains('member_id', 'date_from', 'date_to', 'active', 'recurring')
    def _check_no_overlap(self):
        """A member can't have two windows overlapping in time for the same
        period — it'd be ambiguous whether they're available or not. Scoped
        to non-recurring windows only: a recurring record's date_from/date_to
        is just its first occurrence, not its actual span, so comparing that
        raw range against other windows would misfire."""
        for record in self:
            if not record.active or record.recurring:
                continue
            overlapping = self.search([
                ('id', '!=', record.id),
                ('member_id', '=', record.member_id.id),
                ('active', '=', True),
                ('recurring', '=', False),
                ('date_from', '<', record.date_to),
                ('date_to', '>', record.date_from),
            ], limit=1)
            if overlapping:
                raise ValidationError(
                    "%s already has an availability window (%s, %s → %s) "
                    "that overlaps this one." % (
                        record.member_id.name,
                        dict(overlapping._fields['availability_type'].selection).get(
                            overlapping.availability_type, overlapping.availability_type),
                        overlapping.date_from, overlapping.date_to,
                    )
                )
