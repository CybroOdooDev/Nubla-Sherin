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


class ResUsers(models.Model):
    """Surfaces the res.users <-> nhs.workforce.member link gap on the Users
    form itself. A login can be granted the Staff/Roster Manager/Workforce
    Admin access level without any nhs.workforce.member record pointing its
    user_id back at them - Rostering self-service (My Roster, leave, swaps)
    resolves entirely through that record, so a user in that state has
    access but nothing to use it on. This surfaces the gap at the point it's
    created (granting the group) instead of leaving it to be discovered
    later as an AccessError or a silently-empty portal page."""
    _inherit = 'res.users'

    nhs_workforce_member_id = fields.Many2one(
        'nhs.workforce.member', string='NHS Workforce Member',
        compute='_compute_nhs_workforce_member_id',
        help="The workforce-member record whose Related User points back at this login,"
             " if any. Rostering self-service (My Roster, leave requests, duty swaps)"
             " resolves to this record.")
    nhs_has_roster_access = fields.Boolean(
        string='Has NHS Rostering Access', compute='_compute_nhs_workforce_member_id')

    def _nhs_roster_groups(self):
        """odoo_nhs_training is a hard dependency, but a fresh/partial DB may
        not have these xmlids yet (e.g. mid-install) - fail soft rather than
        breaking every res.users read/onchange."""
        groups = self.env['res.groups']
        for xmlid in (
                'odoo_nhs_rostering.group_nhs_roster_staff',
                'odoo_nhs_rostering.group_nhs_roster_manager',
                'odoo_nhs_rostering.group_nhs_workforce_admin'):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    @api.depends('group_ids')
    def _compute_nhs_workforce_member_id(self):
        roster_groups = self._nhs_roster_groups()
        for user in self:
            user.nhs_has_roster_access = bool(roster_groups) and bool(user.group_ids & roster_groups)
            user.nhs_workforce_member_id = user.id and self.env['nhs.workforce.member'].sudo().search(
                [('user_id', '=', user.id)], limit=1)

    @api.onchange('group_ids')
    def _onchange_group_ids_nhs_workforce_member_warning(self):
        roster_groups = self._nhs_roster_groups()
        if not roster_groups:
            return
        for user in self:
            if not (user.group_ids & roster_groups):
                continue
            linked_id = user._origin.id or user.id
            if linked_id and self.env['nhs.workforce.member'].sudo().search_count(
                    [('user_id', '=', linked_id)]):
                continue
            return {'warning': {
                'title': "No linked NHS workforce member",
                'message': (
                    "%s has NHS e-Rostering access (Staff / Roster Manager / Workforce Admin)"
                    " but no nhs.workforce.member record has its Related User set to this"
                    " login. Until one exists, they cannot use My Roster, leave requests or"
                    " duty swaps.\n\nUse the 'Create Workforce Member' button on this form"
                    " after saving, or NHS e-Rostering > Configuration > Members."
                ) % (user.name or 'This user'),
            }}

    def action_nhs_view_workforce_member(self):
        """Open the workforce-member record linked to this user, if any."""
        self.ensure_one()
        member = self.nhs_workforce_member_id
        return {
            'name': 'Workforce Member',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.workforce.member',
            'view_mode': 'form',
            'res_id': member.id,
            'target': 'current',
        }

    def action_nhs_create_workforce_member(self):
        """Open a prefilled Workforce Member creation form for this user,
        from the point the access gap is actually noticed."""
        self.ensure_one()
        return {
            'name': 'Create Workforce Member',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.workforce.member',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_name': self.name,
                'default_user_id': self.id,
                'default_email': self.email,
            },
        }
