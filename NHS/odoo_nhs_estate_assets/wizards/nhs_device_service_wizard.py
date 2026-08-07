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

class NHSDeviceServiceWizard(models.TransientModel):
    _name = 'nhs.device.service.wizard'
    _description = 'Log Service Wizard'

    device_id = fields.Many2one(
        'nhs.device',
        string='Device',
        required=True,
        help='Device to log service for.'
    )
    service_type = fields.Selection(
        selection=[
            ('ppm', 'Planned Preventive Maintenance'),
            ('repair', 'Repair'),
            ('calibration', 'Calibration'),
            ('electrical_safety', 'Electrical Safety Test'),
            ('inspection', 'Inspection'),
        ],
        string='Service Type',
        required=True,
        default='ppm',
        help='Type of service performed.'
    )
    service_date = fields.Date(
        string='Service Date',
        required=True,
        default=fields.Date.today,
        help='Date the service was performed.'
    )
    schedule_type_id = fields.Many2one(
        'nhs.device.schedule.type',
        string='Schedule Type',
        help='Schedule type this service fulfils. '
             'Selecting a schedule type will update the corresponding schedule.'
    )
    warranty_id = fields.Many2one(
        'nhs.device.warranty',
        string='Covering Warranty / Contract',
        help='Select covering warranty or service contract if applicable.'
    )
    outcome = fields.Selection(
        selection=[
            ('pass', 'Pass'),
            ('pass_with_note', 'Pass with Note'),
            ('fail', 'Fail'),
            ('removed_from_use', 'Removed from Use'),
        ],
        string='Outcome',
        required=True,
        default='pass',
        help='Result of the service.'
    )
    performed_by_id = fields.Many2one(
        'res.users',
        string='Performed By (In-House)',
        help='In-house engineer who performed the service.'
    )
    contractor = fields.Char(
        string='Contractor',
        help='External contractor name (if outsourced).'
    )
    downtime_hours = fields.Float(
        string='Downtime (Hours)',
        help='Number of hours the device was out of service.'
    )
    cost = fields.Monetary(
        string='Service Cost',
        currency_field='currency_id',
        help='Cost of the service.'
    )
    parts_used = fields.Text(
        string='Parts Used',
        help='Spare parts, replacement components, or materials consumed during service.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency of the service cost.'
    )
    certificate_ref = fields.Char(
        string='Certificate Reference',
        help='Reference number for calibration or service certificate.'
    )
    notes = fields.Text(
        string='Notes',
        help='Findings or additional details about the service.'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(NHSDeviceServiceWizard, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'nhs.device' and self.env.context.get('active_id'):
            res['device_id'] = self.env.context.get('active_id')
        return res

    def action_log_service(self):
        """
        Create service record for the selected device.
        If a schedule_type_id is selected, the first matching schedule
        on the device will be updated.
        """
        device = self.device_id
        schedule = None
        if self.schedule_type_id:
            schedule = device.schedule_ids.filtered(
                lambda s: s.schedule_type_id == self.schedule_type_id
            ).sorted('last_done_date', reverse=True)[:1]
        service_vals = {
            'device_id': device.id,
            'service_type': self.service_type,
            'service_date': self.service_date,
            'outcome': self.outcome,
            'performed_by_id': self.performed_by_id.id if self.performed_by_id else False,
            'contractor': self.contractor,
            'downtime_hours': self.downtime_hours,
            'cost': self.cost,
            'parts_used': self.parts_used,
            'certificate_ref': self.certificate_ref,
            'notes': self.notes,
            'warranty_id': self.warranty_id.id if self.warranty_id and self.warranty_id.device_id == device else False,
        }
        if schedule:
            service_vals['schedule_id'] = schedule.id
        self.env['nhs.device.service'].create(service_vals)
        return {'type': 'ir.actions.act_window_close'}
