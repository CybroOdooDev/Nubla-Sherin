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
    """
    UI wizard for recording a risk review.

    Two-model pattern:
      - nhs.risk.review.wizard  → collects user input (transient, discarded after confirm)
      - nhs.risk.review         → stores the confirmed review entry (permanent)

    A draft nhs.risk.review record is created when the wizard opens (review_id).
    On confirm  → wizard values are written to review_id, risk is updated.
    On cancel   → draft review_id is deleted so no orphan entries appear.
    """
    _name = 'nhs.risk.review.wizard'
    _description = 'Risk Review Wizard'

    # ── Primary links ─────────────────────────────────────────────────
    risk_id = fields.Many2one(
        'nhs.risk', string='Risk', required=True,
        help='The risk register entry being reviewed.')

    # ── Risk context fields (related, read-only display) ──────────────
    risk_title = fields.Char(
        related='risk_id.title', string='Risk Title', readonly=True)
    risk_category_id = fields.Many2one(
        related='risk_id.category_id', string='Category', readonly=True)
    risk_register_id = fields.Many2one(
        related='risk_id.register_id', string='Register', readonly=True)
    risk_owner_id = fields.Many2one(
        related='risk_id.risk_owner_id', string='Risk Owner', readonly=True)
    executive_lead_id = fields.Many2one(
        related='risk_id.executive_lead_id', string='Executive Lead', readonly=True)
    next_review_date = fields.Date(
        related='risk_id.next_review_date', string='Next Review Date', readonly=True)
    outside_appetite = fields.Boolean(
        related='risk_id.outside_appetite', string='Outside Appetite', readonly=True)

    cause = fields.Text(
        related='risk_id.cause', string='Cause (IF)', readonly=True)
    event = fields.Text(
        related='risk_id.event', string='Event (THEN)', readonly=True)
    effect = fields.Text(
        related='risk_id.effect', string='Effect (RESULTING IN)', readonly=True)

    # Scores (read-only display from risk)
    inherent_consequence = fields.Selection(
        related='risk_id.inherent_consequence', string='Inherent Consequence', readonly=True)
    inherent_likelihood = fields.Selection(
        related='risk_id.inherent_likelihood', string='Inherent Likelihood', readonly=True)
    inherent_rating = fields.Integer(
        related='risk_id.inherent_rating', string='Inherent Rating', readonly=True)
    inherent_band = fields.Selection(
        related='risk_id.inherent_band', string='Inherent Band', readonly=True)

    current_consequence = fields.Selection(
        related='risk_id.current_consequence', string='Current Consequence', readonly=True)
    current_likelihood = fields.Selection(
        related='risk_id.current_likelihood', string='Current Likelihood', readonly=True)
    current_rating = fields.Integer(
        related='risk_id.current_rating', string='Current Rating', readonly=True)
    current_band = fields.Selection(
        related='risk_id.current_band', string='Current Band', readonly=True)

    target_consequence = fields.Selection(
        related='risk_id.target_consequence', string='Target Consequence', readonly=True)
    target_likelihood = fields.Selection(
        related='risk_id.target_likelihood', string='Target Likelihood', readonly=True)
    target_rating = fields.Integer(
        related='risk_id.target_rating', string='Target Rating', readonly=True)
    target_band = fields.Selection(
        related='risk_id.target_band', string='Target Band', readonly=True)

    # ── Review input fields (standalone on wizard, written to review_id on confirm) ──
    reviewed_at = fields.Datetime(
        string='Reviewed At', required=True,
        default=fields.Datetime.now)
    reviewer_id = fields.Many2one(
        'res.users', string='Reviewer', required=True,
        default=lambda self: self.env.user)
    prev_current_consequence = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='Previous Consequence', readonly=True,
        help='Consequence score on the risk before this review (auto-filled).')
    prev_current_likelihood = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='Previous Likelihood', readonly=True,
        help='Likelihood score on the risk before this review (auto-filled).')
    new_current_consequence = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='New Consequence')
    new_current_likelihood = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='New Likelihood')
    decision = fields.Selection(
        selection=lambda self: self.env['nhs.risk.review']._fields['decision'].selection,
        string='Decision', required=True, default='no_change')
    commentary = fields.Text(string='Commentary')

    # ── Lifecycle ─────────────────────────────────────────────────────
    def default_get(self, fields_list):
        """Pre-fill the previous consequence/likelihood from the risk in context,
        so the review can display before-and-after scores."""
        res = super().default_get(fields_list)
        risk_id = res.get('risk_id') or self.env.context.get('default_risk_id')
        if risk_id:
            risk = self.env['nhs.risk'].browse(risk_id)
            res['prev_current_consequence'] = risk.current_consequence
            res['prev_current_likelihood'] = risk.current_likelihood
        return res

    def action_confirm(self):
        """Create a single nhs.risk.review record from the wizard inputs, then update the risk."""
        self.ensure_one()
        risk = self.risk_id

        review_vals = {
            'risk_id': risk.id,
            'reviewed_at': self.reviewed_at,
            'reviewer_id': self.reviewer_id.id,
            'commentary': self.commentary,
            'decision': self.decision,
            'prev_current_consequence': self.prev_current_consequence,
            'prev_current_likelihood': self.prev_current_likelihood,
        }
        if self.decision == 'rescore' and self.new_current_consequence:
            review_vals['new_current_consequence'] = self.new_current_consequence
            review_vals['new_current_likelihood'] = self.new_current_likelihood

        self.env['nhs.risk.review'].create(review_vals)

        # Update the risk record
        risk.write({'last_reviewed_at': self.reviewed_at})
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

    def action_cancel(self):
        """Close the wizard without creating a review record."""
        return {'type': 'ir.actions.act_window_close'}
