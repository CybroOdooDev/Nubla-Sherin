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


class NhsEscalateAgencyWizard(models.TransientModel):
    """Record that an unfilled shift has been escalated to agency, and the
    agency's cost — the agency side of the bank-vs-agency displacement metric."""
    _name = 'nhs.escalate.agency.wizard'
    _description = 'Escalate Shift to Agency Wizard'

    shift_id = fields.Many2one('nhs.bank.shift', string='Shift', required=True)
    agency_name = fields.Char(string='Agency')
    agency_cost = fields.Monetary(string='Agency Cost', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='shift_id.currency_id')
    reason = fields.Char(string='Reason')

    def action_confirm(self):
        """Mark the shift to_agency, capture the cost, and withdraw pending offers."""
        self.ensure_one()
        self.shift_id.offer_ids.filtered(lambda o: o.response == 'pending').write({'response': 'withdrawn'})
        self.shift_id.write({
            'state': 'to_agency',
            'agency_name': self.agency_name,
            'agency_cost': self.agency_cost,
            'agency_escalation_reason': self.reason,
            'agency_escalated_by_id': self.env.user.id,
            'agency_escalated_at': fields.Datetime.now(),
        })
        self.shift_id.message_post(body=(
            "Escalated to agency (%(agency)s) at a cost of %(cost)s. Reason: %(reason)s") % {
            'agency': self.agency_name or ('unspecified'),
            'cost': self.agency_cost,
            'reason': self.reason or ('none given'),
        })
        return {'type': 'ir.actions.act_window_close'}
