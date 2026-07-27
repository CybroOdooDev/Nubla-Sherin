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
    partner_id = fields.Many2one('res.partner', string='Member', required=True,
                                 help='The person — board member, director or external/co-opted '
                                      'member. Reuses the standard Contact record (the same one used '
                                      'by NHS Trust Management for board membership).')
    user_id = fields.Many2one('res.users', string='User',
                              help='System user link, used to grant portal/system access to this member '
                                   'for their own packs, actions and declarations.')
    name = fields.Char(string='Member Name', related='partner_id.name', store=True,
                       help='The member name, taken from the contact record.')
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

    _DIRECTORY_SYNC_ROLES = {'chair', 'vice_chair', 'member'}

    @api.onchange('partner_id')
    def _onchange_partner_ned(self):
        """Default is_ned from the selected partner's NHS board role."""
        if self.partner_id.nhs_board_role:
            role = self.env['nhs.board.role'].search(
                [('code', '=', self.partner_id.nhs_board_role)], limit=1)
            if role:
                self.is_ned = role.is_ned

    @api.onchange('partner_id')
    def _onchange_partner_user(self):
        """Default the linked user from the selected partner's user account."""
        self.user_id = self.partner_id.user_ids[:1]

    @api.onchange('role')
    def _onchange_role_voting(self):
        """Mark attendee/in-attendance roles as non-voting by default."""
        if self.role in ('attendee', 'in_attendance'):
            self.voting = False

    def _sync_board_member_directory(self):
        """Add Chair/Vice-Chair/Member roles to the linked Trust's Board Member directory
        (res.partner.is_nhs_board_member), so they don't need to be created twice."""
        for member in self:
            trust = member.committee_id.trust_id
            if not trust or not member.partner_id or member.role not in self._DIRECTORY_SYNC_ROLES:
                continue
            partner = member.partner_id
            vals = {}
            if not partner.is_nhs_board_member:
                vals['is_nhs_board_member'] = True
            if not partner.nhs_trust_id:
                vals['nhs_trust_id'] = trust.id
            if not partner.nhs_board_role:
                # 'non_exec'/'other' only: never 'chair'/'ceo'/etc., which would hijack the
                # Trust's own statutory field via res.partner._sync_trust_governance().
                vals['nhs_board_role'] = 'non_exec' if member.is_ned else 'other'
            if vals:
                partner.sudo().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Create memberships and sync the partner's board member directory."""
        records = super().create(vals_list)
        records._sync_board_member_directory()
        return records

    def write(self, vals):
        """Update memberships and re-sync the board member directory when partner/role changes."""
        result = super().write(vals)
        if {'partner_id', 'role'} & set(vals):
            self._sync_board_member_directory()
        return result
