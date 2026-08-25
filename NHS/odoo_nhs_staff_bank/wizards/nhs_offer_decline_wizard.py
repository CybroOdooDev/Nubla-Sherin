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


class NhsOfferDeclineWizard(models.TransientModel):
    """Collects the reason before declining an offer. A separate step (rather
    than declining directly off the button) so a reason can actually be
    required — nhs.shift.offer.action_decline() itself enforces that, so
    this wizard is the only way the backend "Decline" button can supply one."""
    _name = 'nhs.offer.decline.wizard'
    _description = 'Decline Offer Wizard'

    offer_id = fields.Many2one('nhs.shift.offer', string='Offer', required=True)
    reason = fields.Char(string='Decline Reason', required=True)

    def action_confirm(self):
        """Decline the offer with the reason collected here."""
        self.ensure_one()
        self.offer_id.action_decline(reason=self.reason)
        return {'type': 'ir.actions.act_window_close'}
