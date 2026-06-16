from odoo import fields, models


class NhsRiskReviewWizard(models.TransientModel):
    _name = 'nhs.risk.review.wizard'
    _description = 'Risk Review Wizard'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True)
    new_current_consequence = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='New Consequence')
    new_current_likelihood = fields.Selection(
        [(str(i), str(i)) for i in range(1, 6)],
        string='New Likelihood')
    commentary = fields.Text(string='Commentary')
    decision = fields.Selection([
        ('no_change', 'No Change'),
        ('rescore', 'Re-scored'),
        ('escalate', 'Escalate'),
        ('deescalate', 'De-escalate'),
        ('close', 'Close Risk'),
    ], string='Decision', required=True, default='no_change')

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
