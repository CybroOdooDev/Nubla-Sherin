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
from odoo import api, fields, models
from odoo.exceptions import UserError


class NhsBulkCommunicateWizard(models.TransientModel):
    """Send the same templated communication to a batch of applicants at
    once — typically used to notify unsuccessful applicants after
    shortlisting or interview."""
    _name = 'nhs.bulk.communicate.wizard'
    _description = 'Bulk-communicate outcome to applicants'

    application_ids = fields.Many2many('nhs.application', string='Applications', required=True)
    template_id = fields.Many2one(
        'mail.template', string='Template', required=True,
        domain="[('model', '=', 'nhs.application')]")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids and self.env.context.get('active_model') == 'nhs.application':
            res['application_ids'] = [(6, 0, active_ids)]
        return res

    def action_send(self):
        self.ensure_one()
        if not self.application_ids:
            raise UserError(('Select at least one application.'))
        for application in self.application_ids:
            if application.candidate_id.email:
                self.template_id.send_mail(
                    application.id, 
                    force_send=True,
                    email_values={'email_to': application.candidate_id.email}
                )
                application.acknowledged = True
        return {'type': 'ir.actions.act_window_close'}
