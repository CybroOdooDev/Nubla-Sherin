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
#    You should have received a copy of the GNU LESSER PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class NhsCommitteeMember(models.Model):
    _name = 'nhs.committee.member'
    _description = 'Committee Membership'
    _order = 'committee_id, role, id'

    committee_id = fields.Many2one('nhs.committee', string='Committee', required=True,
                                   ondelete='cascade', help='The committee.')
    director_id = fields.Many2one('nhs.director', string='Director', required=True,
                                  ondelete='cascade', help='The person (director/officer).')
    partner_id = fields.Many2one('res.partner', string='Contact', related='director_id.partner_id',
                                 store=True, help='Contact/user link for external members or portal access, '
                                                   "taken from the director's own contact link.")
    user_id = fields.Many2one('res.users', string='User', related='director_id.user_id', store=True,
                              help='System user link, used to grant portal/system access to this member '
                                   'for their own packs, actions and declarations.')
    name = fields.Char(string='Member Name', related='director_id.name', store=True,
                       help='The member name, taken from the director record.')
    role = fields.Selection([
        ('chair', 'Chair'),
        ('vice_chair', 'Vice-Chair'),
        ('member', 'Member'),
        ('attendee', 'Attendee'),
        ('in_attendance', 'In Attendance'),
        ('secretary', 'Secretary'),
    ], string='Role', required=True, default='member',
       help='The role this person holds on this committee.')
    is_ned = fields.Boolean(string='Non-Executive Director', default=False,
                            help='Non-executive director — counts toward the NED quorum where the committee '
                                 "requires a minimum number of NEDs present.")
    term_start = fields.Date(string='Term Start', help='Membership term start date.')
    term_end = fields.Date(string='Term End', help='Membership term end date.')
    voting = fields.Boolean(string='Voting Member', default=True,
                            help='Whether this member votes and counts toward quoracy. '
                                 'Attendees / in-attendance members are typically non-voting.')
    company_id = fields.Many2one(related='committee_id.company_id', string='Company', store=True,
                                 help='Owning company, taken from the related committee.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    @api.onchange('director_id')
    def _onchange_director_ned(self):
        """Default is_ned from the selected director's executive status."""
        if self.director_id:
            self.is_ned = not self.director_id.is_executive

    @api.onchange('director_id')
    def _onchange_director_user(self):
        """Default the linked user from the selected director's own user account."""
        self.user_id = self.director_id.user_id

    @api.onchange('role')
    def _onchange_role_voting(self):
        """Mark attendee/in-attendance roles as non-voting by default."""
        if self.role in ('attendee', 'in_attendance'):
            self.voting = False
