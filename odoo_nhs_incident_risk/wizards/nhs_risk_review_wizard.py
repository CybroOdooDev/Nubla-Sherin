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


class NhsRiskReviewWizard(models.TransientModel):
    _name = 'nhs.risk.review.wizard'
    _description = 'Risk Review Wizard'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True,
                              help='The risk register entry being reviewed.')
    new_current_consequence = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='New Consequence',
        help='Updated consequence score (1–5) after reviewing current controls. '
             'Leave blank if the score is unchanged. 1 = negligible, 5 = catastrophic.')
    new_current_likelihood = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='New Likelihood',
        help='Updated likelihood score (1–5) after reviewing current controls. '
             'Leave blank if the score is unchanged. 1 = rare, 5 = almost certain.')
    commentary = fields.Text(string='Commentary',
                             help='Narrative explaining the outcome of this review, any score changes, '
                                  'and the reasoning behind the decision.')
    decision = fields.Selection([
        ('no_change', 'No Change'),
        ('rescore', 'Re-scored'),
        ('escalate', 'Escalate'),
        ('deescalate', 'De-escalate'),
        ('close', 'Close Risk'),
    ], string='Decision', required=True, default='no_change',
       help='The outcome of this review: No Change if the risk is unchanged; '
            'Re-scored if the consequence or likelihood has changed; '
            'Escalate or De-escalate to move the risk to a different register; '
            'Close Risk to mark it as resolved.')

    def action_confirm(self):
        self.ensure_one()
        risk = self.risk_id
        review_vals = {
            'risk_id': risk.id,
            'reviewed_at': fields.Datetime.now(),
            'reviewer_id': self.env.user.id,
            'commentary': self.commentary,
            'decision': self.decision,
        }
        if self.new_current_consequence:
            review_vals['prev_current_consequence'] = risk.current_consequence
            review_vals['prev_current_likelihood'] = risk.current_likelihood
            review_vals['new_current_consequence'] = self.new_current_consequence
            review_vals['new_current_likelihood'] = self.new_current_likelihood
        self.env['nhs.risk.review'].create(review_vals)

        risk.write({'last_reviewed_at': fields.Datetime.now()})
        if self.decision == 'rescore' and self.new_current_consequence:
            risk.write({
                'current_consequence': self.new_current_consequence,
                'current_likelihood': self.new_current_likelihood,
            })
        elif self.decision == 'close':
            if not risk.closure_reason:
                risk.write({'closure_reason': self.commentary})
            risk.action_close()

        return {'type': 'ir.actions.act_window_close'}
