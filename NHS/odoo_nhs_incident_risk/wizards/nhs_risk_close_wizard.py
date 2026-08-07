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


class NhsRiskCloseWizard(models.TransientModel):
    """Wizard to record a closure reason and close a risk register entry."""
    _name = 'nhs.risk.close.wizard'
    _description = 'Close Risk Wizard'

    risk_id = fields.Many2one('nhs.risk', string='Risk', required=True,
                              help='The risk being closed.')
    closure_reason = fields.Text(
        string='Closure Reason', required=True,
        help='Explain why this risk is being closed. This is saved on the risk record '
             'and posted as a chatter message.')

    def action_confirm(self):
        """Save the closure reason on the risk, close it, and post a chatter message."""
        self.ensure_one()
        risk = self.risk_id
        risk.write({'closure_reason': self.closure_reason})
        risk.action_close()
        risk.message_post(body='Risk closed. Reason: %s' % self.closure_reason)
        return {'type': 'ir.actions.act_window_close'}
