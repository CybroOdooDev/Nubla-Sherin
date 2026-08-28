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


class NhsLeaveEntitlement(models.Model):
    """A person's leave balance for one leave type in one leave year -
    decremented as requests are approved."""
    _name = 'nhs.leave.entitlement'
    _description = 'Leave Entitlement'
    _order = 'leave_year desc, member_id'
    _rec_name =  'member_id'

    member_id = fields.Many2one(
        'nhs.workforce.member', string='Member', required=True, ondelete='cascade', index=True)
    leave_type_id = fields.Many2one('nhs.leave.type', string='Leave Type', required=True)
    leave_year = fields.Char(
        string='Leave Year', required=True, default=lambda self: str(fields.Date.context_today(self).year),
        help="e.g. '2026'.")
    company_id = fields.Many2one(
        'res.company', related='member_id.company_id', store=True)
    entitlement_hours = fields.Float(string='Entitlement (Hours)', required=True, default=0.0)
    taken_hours = fields.Float(
        string='Taken (Hours)', compute='_compute_taken_hours', store=True)
    remaining_hours = fields.Float(
        string='Remaining (Hours)', compute='_compute_taken_hours', store=True)

    _member_type_year_uniq = models.Constraint(
        'UNIQUE(member_id, leave_type_id, leave_year)',
        'This member already has an entitlement for that leave type and year!'
    )

    @api.depends('member_id.leave_request_ids.state', 'member_id.leave_request_ids.hours',
                 'member_id.leave_request_ids.leave_type_id', 'member_id.leave_request_ids.date_from',
                 'entitlement_hours', 'leave_type_id', 'leave_year')
    def _compute_taken_hours(self):
        for entitlement in self:
            requests = entitlement.member_id.leave_request_ids.filtered(
                lambda r: r.leave_type_id == entitlement.leave_type_id
                and r.state == 'approved'
                and r.date_from and str(r.date_from.year) == entitlement.leave_year)
            entitlement.taken_hours = sum(requests.mapped('hours'))
            entitlement.remaining_hours = entitlement.entitlement_hours - entitlement.taken_hours
