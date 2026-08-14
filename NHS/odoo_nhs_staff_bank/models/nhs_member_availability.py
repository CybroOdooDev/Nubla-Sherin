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

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Reject a window whose end is not after its start."""
        for record in self:
            if record.date_to <= record.date_from:
                raise ValidationError("'To' must be after 'From'.")
