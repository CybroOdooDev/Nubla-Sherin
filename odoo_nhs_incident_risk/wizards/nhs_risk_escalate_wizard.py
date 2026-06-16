from odoo import fields, models
from odoo.exceptions import UserError


class NhsRiskEscalateWizard(models.TransientModel):
    _name = 'nhs.risk.escalate.wizard'
    _description = 'Risk Escalation / De-escalation Wizard'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True)
    current_register_id = fields.Many2one(related='risk_id.register_id',
                                          string='Current Register', readonly=True)
    target_register_id = fields.Many2one(
        'nhs.risk.register', string='Target Register', required=True,
        domain="[('id','!=',current_register_id)]")
    rationale = fields.Text(string='Rationale', required=True)
    notify_user_ids = fields.Many2many('res.users', string='Notify Users')

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

        risk.with_context(nhs_workflow=True).write(
            {'register_id': self.target_register_id.id})
        risk.message_post(
            body=f'Risk moved from <b>{old_register.name}</b> to <b>{self.target_register_id.name}</b>.<br/>'
                 f'Rationale: {self.rationale}')

        if self.notify_user_ids:
            for user in self.notify_user_ids:
                risk.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    note=f'Risk {risk.name} has been moved to your register: {self.rationale}')

        return {'type': 'ir.actions.act_window_close'}
