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


class NhsRiskEscalateWizard(models.TransientModel):
    _name = 'nhs.risk.escalate.wizard'
    _description = 'Risk Escalation / De-escalation Wizard'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True,
                              help='The risk being escalated or de-escalated to a different register.')
    current_register_id = fields.Many2one(related='risk_id.register_id',
                                          string='Current Register', readonly=True,
                                          help='The register this risk currently sits on.')
    target_register_id = fields.Many2one(
        'nhs.risk.register', string='Target Register', required=True,
        domain="[('id','!=',current_register_id)]",
        help='The register the risk should be moved to. Moving to a higher tier (e.g. Corporate, BAF) '
             'constitutes an escalation; moving to a lower tier is a de-escalation.')
    target_tier = fields.Selection(related='target_register_id.tier', string='Target Tier', readonly=True)
    executive_lead_id = fields.Many2one(
        'res.users', string='Executive Lead',
        help='Required when moving to a Corporate or BAF register. '
             'The executive accountable for this risk at board level.')
    rationale = fields.Text(string='Rationale', required=True,
                            help='Explain the reason for this escalation or de-escalation. '
                                 'This is recorded in the review log and posted as a chatter message on the risk.')
    notify_user_ids = fields.Many2many('res.users', string='Notify Users',
                                       help='Users who should be notified of this register change. '
                                            'An activity will be created for each selected user.')

    @api.onchange('target_register_id')
    def _onchange_target_register_id(self):
        if self.target_register_id and self.target_register_id.tier in ('corporate', 'baf'):
            if not self.executive_lead_id and self.risk_id.executive_lead_id:
                self.executive_lead_id = self.risk_id.executive_lead_id

    def action_confirm(self):
        self.ensure_one()
        risk = self.risk_id
        old_register = risk.register_id

        decision = 'escalate'
        if self.target_register_id.tier in ('local', 'directorate') and \
           old_register.tier in ('corporate', 'baf'):
            decision = 'deescalate'

        self.env['nhs.risk.review'].create({
            'risk_id': risk.id,
            'reviewed_at': fields.Datetime.now(),
            'reviewer_id': self.env.user.id,
            'commentary': self.rationale,
            'decision': decision,
        })

        vals = {'register_id': self.target_register_id.id}
        if self.executive_lead_id:
            vals['executive_lead_id'] = self.executive_lead_id.id
        risk.with_context(nhs_workflow=True).write(vals)
        risk.message_post(
            body='Risk moved from %s to %s. Rationale: %s' % (
                old_register.name, self.target_register_id.name, self.rationale
            )
        )

        if self.notify_user_ids:
            for user in self.notify_user_ids:
                risk.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    note=f'Risk {risk.name} has been moved to your register: {self.rationale}')

        return {'type': 'ir.actions.act_window_close'}
