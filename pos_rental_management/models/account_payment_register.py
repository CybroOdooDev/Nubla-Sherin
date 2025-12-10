
from odoo import models


class AccountPaymentRegister(models.TransientModel):
    """
    Model to inherit 'account.payment.register' for supering the Payment Button
    to change functionality.
    """
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        """
        Override the 'action_create_payments' method to set
        'is_partial_payment' to False for the current order associated with
        the active session.
        """
        res = super(AccountPaymentRegister,self).action_create_payments()
        active_session = self.env['pos.session'].search(
            [('state', '=', 'opened'),
             ('user_id', '=', self.env.user.id)], limit=1)
        if active_session:
            current_order = self.env['pos.order'].search(
                [('session_id', '=', active_session.id),
                 ('state', '=', 'invoiced')], limit=1)
            if current_order:
                current_order.write({'is_partial_payment': False})
        return res
