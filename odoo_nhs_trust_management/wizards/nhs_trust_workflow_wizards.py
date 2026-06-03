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
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class NhsTrustMergeWizard(models.TransientModel):
    _name = 'nhs.trust.merge.wizard'
    _description = 'NHS Trust Merger Wizard'

    source_trust_id = fields.Many2one('nhs.trust', string='Source Trust', required=True, readonly=True)
    target_trust_id = fields.Many2one(
        'nhs.trust', 
        string='Target Trust (to merge into)', 
        required=True, 
        domain="[('id', '!=', source_trust_id), ('state', '=', 'active')]"
    )
    merge_date = fields.Date(string='Merger Date', required=True, default=fields.Date.context_today)
    reason = fields.Text(string='Justification / Legal Order Reference', required=True)
    transfer_sites = fields.Boolean(string='Transfer All Sites to Target Trust', default=True)
    transfer_board_members = fields.Boolean(string='Transfer Board Members to Target Trust', default=False)

    @api.constrains('reason')
    def _check_reason(self):
        for wiz in self:
            if not wiz.reason or len(wiz.reason.strip()) < 5:
                raise ValidationError('A minimum of 5 characters is required for merger justification!')

    def action_confirm_merge(self):
        self.ensure_one()
        source = self.source_trust_id
        target = self.target_trust_id

        # 1. Create audit log for the merger on source trust
        self.env['nhs.trust.state.log'].create({
            'trust_id': source.id,
            'from_state': source.state,
            'to_state': 'merging',
            'reason': f"Merged into '{target.name}'. {self.reason}",
            'user_id': self.env.user.id,
            'change_date': fields.Datetime.now(),
        })

        # 2. Transfer Sites if selected
        transferred_site_names = []
        if self.transfer_sites and source.site_ids:
            sites_to_transfer = source.site_ids
            for site in sites_to_transfer:
                transferred_site_names.append(site.name)
            sites_to_transfer.write({'trust_id': target.id})

        # 3. Transfer/clear Board Members if selected
        if source.board_member_ids:
            if self.transfer_board_members:
                source.board_member_ids.write({'nhs_trust_id': target.id})
            else:
                source.board_member_ids.write({'nhs_trust_id': False})

        # 4. Set state of source trust to merging
        source.with_context(approved_state_change=True).write({'state': 'merging'})

        # 5. Log details in chatter of both trusts
        source_message = f"This trust has been merged into <b>{target.name}</b> on {self.merge_date}.<br/>"
        if transferred_site_names:
            source_message += f"Sites transferred to target trust: {', '.join(transferred_site_names)}.<br/>"
        source_message += f"Reason: {self.reason}"
        source.message_post(body=source_message)

        target_message = f"NHS Trust merger executed: <b>{source.name}</b> has been merged into this trust.<br/>"
        if transferred_site_names:
            target_message += f"Transferred sites: {', '.join(transferred_site_names)}.<br/>"
        target_message += f"Reason: {self.reason}"
        target.message_post(body=target_message)

        return {'type': 'ir.actions.act_window_close'}


class NhsTrustDissolveWizard(models.TransientModel):
    _name = 'nhs.trust.dissolve.wizard'
    _description = 'NHS Trust Dissolution Wizard'

    trust_id = fields.Many2one('nhs.trust', string='Trust Reference', required=True, readonly=True)
    dissolve_date = fields.Date(string='Dissolution Date', required=True, default=fields.Date.context_today)
    reason = fields.Text(string='Justification / Legal Order Reference', required=True)
    archive_sites = fields.Boolean(string='Archive All Associated Sites', default=True)

    @api.constrains('reason')
    def _check_reason(self):
        for wiz in self:
            if not wiz.reason or len(wiz.reason.strip()) < 5:
                raise ValidationError('A minimum of 5 characters is required for dissolution justification!')

    def action_confirm_dissolve(self):
        self.ensure_one()
        trust = self.trust_id

        # 1. Create audit log for the dissolution
        self.env['nhs.trust.state.log'].create({
            'trust_id': trust.id,
            'from_state': trust.state,
            'to_state': 'dissolved',
            'reason': f"Dissolved. {self.reason}",
            'user_id': self.env.user.id,
            'change_date': fields.Datetime.now(),
        })

        # 2. Archive Sites if selected
        if self.archive_sites and trust.site_ids:
            trust.site_ids.write({'active': False})

        # 3. Archive Board Members (or set nhs_trust_id = False)
        if trust.board_member_ids:
            trust.board_member_ids.write({'nhs_trust_id': False})

        # 4. Set state of trust to dissolved
        trust.with_context(approved_state_change=True).write({'state': 'dissolved', 'active': False})

        # 5. Log details in chatter
        message = f"This trust has been dissolved on {self.dissolve_date}.<br/>"
        if self.archive_sites:
            message += "All associated sites have been archived.<br/>"
        message += f"Reason: {self.reason}"
        trust.message_post(body=message)

        return {'type': 'ir.actions.act_window_close'}
