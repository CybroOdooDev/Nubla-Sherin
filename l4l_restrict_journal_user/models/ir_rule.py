# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.osv import expression

class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _compute_domain(self, model_name, mode="read"):
        base = super()._compute_domain(model_name, mode=mode)
        
        target_models = [
            'account.journal', 
            'account.move', 
            'account.move.line', 
            'account.payment', 
            'account.bank.statement.line'
        ]
        if model_name not in target_models:
            return base

        if self.env.su or self._context.get('bypass_domain_access'):
            return base
        if self._context.get('active_model') == 'res.users' or self._context.get('params', {}).get('model') == 'res.users':
            return base

        current_user_sudo = self.env.user.sudo()
        
        if not current_user_sudo.has_group('l4l_restrict_journal_user.access_restrict_user_for_journal'):
            return base

        journal_ids = current_user_sudo.allowed_journal_ids.ids


        if not journal_ids:
            return base

        if model_name == 'account.journal':
            return expression.AND([base, [('id', 'in', journal_ids)]])

        return expression.AND([base, [('journal_id', 'in', journal_ids + [False])]])