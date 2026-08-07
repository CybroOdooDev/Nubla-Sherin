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
from xml.etree import ElementTree as ET
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    _ROLE_TRUST_FIELD = {
        'chair': 'chair_id',
        'ceo': 'chief_executive_id',
        'medical_director': 'medical_director_id',
        'nursing_director': 'director_of_nursing_id',
        'finance_director': 'finance_director_id',
    }

    is_nhs_board_member = fields.Boolean(
        string='NHS Board Member',
        default=False, 
        index=True,
        help="Master flag. Setting to True reveals the NHS Board Member notebook page on the partner form. Used in domain filters across all NHS views."
    )
    nhs_trust_id = fields.Many2one(
        'nhs.trust', 
        string='NHS Trust', 
        index=True,
        help="Trust this person sits on the board of. Required if is_nhs_board_member=True (enforced by view)."
    )
    nhs_board_role = fields.Selection(
        selection='_selection_nhs_board_role',
        string='Board Role',
        index=True,
        help="chair / ceo / medical_director / nursing_director / finance_director / exec / "
             "non_exec / other. NED = Non-Executive Director (independent oversight role). "
             "The available labels are configurable under Settings > Users & Companies > "
             "NHS > Board Roles."
    )

    @api.model
    def _selection_nhs_board_role(self):
        roles = self.env['nhs.board.role'].sudo().search([])
        return [(role.code, role.name) for role in roles]
    is_voting_member = fields.Boolean(
        string='Voting Member', 
        default=True,
        help="True for full voting board members. Default: True. Set False for advisors, observers, associate directors."
    )
    term_start_date = fields.Date(
        string='Term Start Date',
        help="Start of current appointment term."
    )
    term_end_date = fields.Date(
        string='Term End Date',
        help="End of current appointment term. Used to compute is_term_active."
    )
    appointment_authority = fields.Char(
        string='Appointment Authority', 
        help="Body that appointed this member (e.g. 'NHS Improvement', 'Council of Governors', 'Secretary of State')."
    )
    is_term_active = fields.Boolean(
        string='Term Active',
        compute='_compute_is_term_active',
        store=True,
        index=True,
        help="True if today's date is within [term_start_date, term_end_date]."
    )
    can_edit_board_member = fields.Boolean(
        string='Can Edit Board Member',
        compute='_compute_can_edit_board_member',
        help="True if the current user is an NHS Trust Manager or Administrator."
    )

    def _compute_can_edit_board_member(self):
        """Compute whether the current user is an NHS Trust Manager/Administrator, gating board-member edit rights."""
        is_manager = self.env.user.has_group(
            'odoo_nhs_trust_management.group_nhs_trust_manager'
        )
        for rec in self:
            rec.can_edit_board_member = is_manager

    def _sync_trust_governance(self):
        """Set the matching statutory field on the linked trust when a role is assigned."""
        for partner in self:
            trust = partner.nhs_trust_id
            if not trust or not partner.is_nhs_board_member:
                continue
            trust_field = self._ROLE_TRUST_FIELD.get(partner.nhs_board_role)
            if trust_field:
                trust.sudo().write({trust_field: partner.id})

    def get_view(self, view_id=None, view_type='form', **options):
        """Extend get_view() to strip create/delete rights from the board member list view for non-managers."""
        result = super().get_view(view_id, view_type, **options)
        if view_type == 'list':
            board_view = self.env.ref(
                'odoo_nhs_trust_management.view_nhs_board_member_list',
                raise_if_not_found=False,
            )
            if (board_view and view_id == board_view.id and
                    not self.env.user.has_group(
                        'odoo_nhs_trust_management.group_nhs_trust_manager')):
                node = ET.fromstring(result['arch'])
                node.set('create', '0')
                node.set('delete', '0')
                result['arch'] = ET.tostring(node, encoding='unicode')
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Extend create() to block non-managers from creating board member records and sync trust governance fields.

        Raises UserError if a non-manager attempts to create a partner with
        is_nhs_board_member=True.
        """
        if not self.env.user.has_group('odoo_nhs_trust_management.group_nhs_trust_manager'):
            for vals in vals_list:
                if vals.get('is_nhs_board_member'):
                    raise UserError(
                        'Only NHS Trust Managers and Administrators can create board member records.'
                    )
        records = super().create(vals_list)
        records.filtered('is_nhs_board_member')._sync_trust_governance()
        return records

    def write(self, vals):
        """Extend write() to gate board-member field changes to managers and keep trust governance fields in sync.

        Raises UserError if a non-manager modifies any board-member-related
        field. When trust/role fields change, clears the stale statutory
        field (e.g. chair_id) on the previously linked trust before syncing
        the new one, since a trust field must always point at the current
        role holder only.
        """
        board_fields = {
            'is_nhs_board_member', 'nhs_trust_id', 'nhs_board_role',
            'is_voting_member', 'term_start_date', 'term_end_date',
            'appointment_authority',
        }
        if board_fields & set(vals):
            nhs_records = self.filtered('is_nhs_board_member')
            becoming_member = vals.get('is_nhs_board_member')
            if (nhs_records or becoming_member) and not self.env.user.has_group(
                'odoo_nhs_trust_management.group_nhs_trust_manager'
            ):
                raise UserError(
                    'Only NHS Trust Managers and Administrators can modify board member records.'
                )

        # Capture old governance state before write so we can clear stale trust fields
        governance_triggers = {'is_nhs_board_member', 'nhs_trust_id', 'nhs_board_role'}
        needs_sync = bool(governance_triggers & set(vals))
        old_states = {}
        if needs_sync:
            for partner in self:
                if partner.is_nhs_board_member or vals.get('is_nhs_board_member'):
                    old_states[partner.id] = {
                        'trust': partner.nhs_trust_id,
                        'role': partner.nhs_board_role,
                    }

        result = super().write(vals)

        if needs_sync and old_states:
            for partner in self:
                old = old_states.get(partner.id)
                if not old:
                    continue
                old_trust = old['trust']
                old_role = old['role']
                # Clear the old trust field if this partner was occupying it and the
                # role or trust has changed
                if old_trust and old_role:
                    old_field = self._ROLE_TRUST_FIELD.get(old_role)
                    if old_field and old_trust[old_field] == partner:
                        if old_trust != partner.nhs_trust_id or old_role != partner.nhs_board_role:
                            old_trust.sudo().write({old_field: False})
                # Set new statutory field on the (possibly new) trust
                if partner.is_nhs_board_member:
                    partner._sync_trust_governance()

        return result

    def unlink(self):
        """Extend unlink() to block non-managers from deleting board member records."""
        if not self.env.user.has_group('odoo_nhs_trust_management.group_nhs_trust_manager'):
            if self.filtered('is_nhs_board_member'):
                raise UserError(
                    'Only NHS Trust Managers and Administrators can delete board member records.'
                )
        return super().unlink()

    def action_open_nhs_trust(self):
        """Open the linked NHS Trust form in the current window."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'NHS Trust',
            'res_model': 'nhs.trust',
            'res_id': self.nhs_trust_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.constrains('nhs_trust_id', 'is_nhs_board_member')
    def _check_trust_state_for_board_member(self):
        """Prevent assigning a board member to a Trust that is dissolved or suspended."""
        for partner in self:
            if partner.is_nhs_board_member and partner.nhs_trust_id:
                if partner.nhs_trust_id.state in ('dissolved', 'suspended'):
                    raise ValidationError(
                        'Cannot assign a board member to "%s" because the trust is %s.'
                        % (partner.nhs_trust_id.name, partner.nhs_trust_id.state.capitalize())
                    )

    @api.depends('term_start_date', 'term_end_date', 'is_nhs_board_member')
    def _compute_is_term_active(self):
        """Compute whether today falls within [term_start_date, term_end_date] for board members.

        Non board members are always False. An open-ended start or end date
        is treated as active from/until that bound; with neither bound set,
        an active board member defaults to True.
        """
        today = fields.Date.context_today(self)
        for partner in self:
            if not partner.is_nhs_board_member:
                partner.is_term_active = False
                continue
            start = partner.term_start_date
            end = partner.term_end_date
            if start and end:
                partner.is_term_active = start <= today <= end
            elif start:
                partner.is_term_active = start <= today
            elif end:
                partner.is_term_active = today <= end
            else:
                partner.is_term_active = True
