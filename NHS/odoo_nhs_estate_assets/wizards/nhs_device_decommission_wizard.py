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

class NHSDeviceDecommissionWizard(models.TransientModel):
    _name = 'nhs.device.decommission.wizard'
    _description = 'Decommission Device Wizard'

    device_id = fields.Many2one(
        'nhs.device',
        string='Device',
        required=True,
        help='Device to decommission.'
    )
    decommission_date = fields.Date(
        string='Decommission Date',
        required=True,
        default=fields.Date.today,
        help='Date the device was decommissioned or removed from service.'
    )
    status = fields.Selection(
        selection=[
            ('decommissioned', 'Decommissioned'),
            ('disposed', 'Disposed'),
        ],
        string='Target Status',
        required=True,
        default='decommissioned',
        help='Status to set on the device.'
    )
    disposal_method = fields.Selection(
        selection=[
            ('sold', 'Sold'),
            ('donated', 'Donated'),
            ('scrapped', 'Scrapped'),
            ('returned', 'Returned to Manufacturer'),
        ],
        string='Disposal Method',
        help='Method by which the device was disposed of.'
    )
    disposal_value = fields.Monetary(
        string='Disposal Value',
        currency_field='currency_id',
        help='Value recovered from disposal (if any).'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency of the disposal value.'
    )
    notes = fields.Text(
        string='Notes / Reason',
        help='Reason for decommissioning or additional details.'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(NHSDeviceDecommissionWizard, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'nhs.device' and self.env.context.get('active_id'):
            res['device_id'] = self.env.context.get('active_id')
        return res

    def action_decommission(self):
        """
        Apply decommissioning / disposal to the selected device and archive it,
        retaining full historical maintenance, calibration, alert, and warranty records.
        """
        device = self.device_id
        vals = {
            'status': self.status,
            'decommission_date': self.decommission_date,
            'active': False,
        }
        if self.status == 'disposed':
            if self.disposal_method:
                vals['disposal_method'] = self.disposal_method
            if self.disposal_value:
                vals['disposal_value'] = self.disposal_value
        device.write(vals)
        if self.notes:
            device.message_post(body="Decommissioning Notes: %s" % self.notes)
        return {'type': 'ir.actions.act_window_close'}
