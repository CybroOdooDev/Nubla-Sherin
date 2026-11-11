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
    _description = 'Bulk Service Creation Wizard'

    device_ids = fields.Many2many(
        'nhs.device',
        string='Devices',
        required=True,
        help='Devices to create service records for.'
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
        help='When performed. Cannot be set in the future.'
    )
    performed_by_id = fields.Many2one(
        'res.users',
        string='Performed By (In-House)',
        default=lambda self: self.env.user,
        help='In-house engineer who performed the service.'
    )
    contractor = fields.Char(
        string='Contractor',
        help='External contractor name (if service was outsourced).'
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
    downtime_hours = fields.Float(
        string='Downtime (Hours)',
        help='Out-of-service time in hours (for repairs).'
    )
    cost = fields.Monetary(
        string='Service Cost',
        currency_field='currency_id',
        help='Service cost.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency of the service cost.'
    )
    certificate_ref = fields.Char(
        string='Certificate Reference',
        help='Calibration/service certificate reference number.'
    )
    parts_used = fields.Text(
        string='Parts Used',
        help='Spare parts, replacement components, or materials consumed.'
    )
    notes = fields.Text(
        string='Notes',
        help='Findings, observations, or additional details about the service.'
    )

    @api.model
    def default_get(self, fields_list):
        """Pre-fill device_ids with active NHS device(s) when wizard is opened."""
        res = super(NHSDeviceServiceWizard, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'nhs.device' and self.env.context.get('active_ids'):
            res['device_ids'] = [(6, 0, self.env.context.get('active_ids'))]
        return res

    def action_create_services(self):
        """
        Create service records for all selected devices.
        """
        Service = self.env['nhs.device.service']
        for device in self.device_ids:
            schedule = device.schedule_ids.filtered(
                lambda s: s.schedule_type_id.code == self.service_type
            )
            schedule_id = schedule[0].id if schedule else False

            vals = {
                'device_id': device.id,
                'schedule_id': schedule_id,
                'service_type': self.service_type,
                'service_date': self.service_date,
                'performed_by_id': self.performed_by_id.id if self.performed_by_id else False,
                'contractor': self.contractor,
                'outcome': self.outcome,
                'downtime_hours': self.downtime_hours,
                'cost': self.cost,
                'certificate_ref': self.certificate_ref,
                'parts_used': self.parts_used,
                'notes': self.notes,
            }
            Service.create(vals)
        return {
            'type': 'ir.actions.act_window_close',
        }
