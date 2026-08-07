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
from odoo import fields, models


class NhsRiskEscalateWizard(models.TransientModel):
    """Wizard to move a risk to a different register, logging the move as a review."""
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
    rationale = fields.Text(string='Rationale', required=True,
                            help='Explain the reason for this escalation or de-escalation. '
                                 'This is recorded in the review log and posted as a chatter message on the risk.')
    notify_user_ids = fields.Many2many('res.users', string='Notify Users',
                                       help='Users who should be notified of this register change. '
                                            'An activity will be created for each selected user.')

    def action_confirm(self):
        """Move the risk to the target register, recording the change as a risk
        review (auto-classified as escalate or de-escalate based on register tier)
        and scheduling an activity for each user selected for notification."""
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

        risk.with_context(nhs_workflow=True).write(
            {'register_id': self.target_register_id.id})
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
