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

URGENCIES = [
    ('planned', 'Planned'),
    ('urgent', 'Urgent'),
    ('last_minute', 'Last Minute'),
]


class NhsEscalateWizard(models.TransientModel):
    """One-click escalation: push the selected unfilled duties to the Staff
    Bank as open shifts (when installed), or track them as needing manual
    cover otherwise."""
    _name = 'nhs.escalate.wizard'
    _description = 'Escalate Unfilled Duties Wizard'

    duty_ids = fields.Many2many(
        'nhs.duty', string='Duties', required=True,
        domain="[('state', 'in', ('unfilled', 'partially_filled'))]", help="Duties")
    urgency = fields.Selection(URGENCIES, string='Urgency', default='urgent', required=True, help="Urgency")
    push_to_bank = fields.Boolean(
        string='Push to Staff Bank', default=True,
        help="Untick to just record these as needing manual cover, without pushing to the bank.")
    bank_installed = fields.Boolean(compute='_compute_bank_installed', help="Detailed information about this field")

    def _compute_bank_installed(self):
        """ Method for compute bank installed """
        installed = 'nhs.bank.shift' in self.env
        for wizard in self:
            wizard.bank_installed = installed

    @api.model
    def default_get(self, fields_list):
        """ Method for default get """
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'nhs.duty' and self.env.context.get('active_ids'):
            duties = self.env['nhs.duty'].browse(self.env.context['active_ids']).filtered(
                lambda d: d.state in ('unfilled', 'partially_filled'))
            res['duty_ids'] = [(6, 0, duties.ids)]
        return res

    def action_escalate(self):
        """ Method for action escalate """
        self.ensure_one()
        Escalation = self.env['nhs.roster.escalation']
        count = 0
        for duty in self.duty_ids:
            if duty.escalation_id and duty.escalation_id.state not in ('cancelled',):
                continue
            gap = duty.required_headcount - duty.assigned_count
            if gap <= 0:
                continue
            escalation = Escalation.create({
                'duty_id': duty.id, 'headcount': gap, 'urgency': self.urgency,
            })
            if self.push_to_bank and self.bank_installed:
                escalation.action_push_to_bank()
            else:
                escalation.action_mark_manual_cover() if not self.bank_installed else None
            count += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': ('Escalated'),
                'message': ('%d duty(ies) escalated.') % count,
                'type': 'success',
            },
        }
