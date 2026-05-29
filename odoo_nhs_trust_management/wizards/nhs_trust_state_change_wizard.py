# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class NhsTrustStateChangeWizard(models.TransientModel):
    _name = 'nhs.trust.state.change.wizard'
    _description = 'NHS Trust Workflow State Change Confirmation'

    trust_id = fields.Many2one('nhs.trust', string='NHS Trust Reference', required=True)
    current_state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('active', 'Active'),
        ('special_measures', 'Special Measures'),
        ('merging', 'Merging'),
        ('dissolved', 'Dissolved'),
    ], string='Current State', related='trust_id.state', readonly=True)
    new_state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('active', 'Active'),
        ('special_measures', 'Special Measures'),
        ('merging', 'Merging'),
        ('dissolved', 'Dissolved'),
    ], string='Target State', required=True)
    reason = fields.Text(string='Justification Reason / Auditable Narrative', required=True)

    @api.constrains('reason')
    def _check_reason(self):
        for wiz in self:
            if not wiz.reason or len(wiz.reason.strip()) < 5:
                raise ValidationError('A minimum of 5 characters is required for state change justification!')

    def action_confirm(self):
        self.ensure_one()
        if self.new_state == self.current_state:
            raise ValidationError('The new state must be different from the current state!')
        
        # 1. Add immutable audit trail entry
        self.env['nhs.trust.state.log'].create({
            'trust_id': self.trust_id.id,
            'from_state': self.current_state,
            'to_state': self.new_state,
            'reason': self.reason,
            'user_id': self.env.user.id,
            'change_date': fields.Datetime.now(),
        })

        # 2. Update the trust model state bypassing direct block via context
        self.trust_id.with_context(approved_state_change=True).write({
            'state': self.new_state
        })

        return {'type': 'ir.actions.act_window_close'}
