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
from odoo import api,fields, models

class NHSDeviceBulkScheduleWizard(models.TransientModel):
    _name = 'nhs.device.bulk.schedule.wizard'
    _description = 'Bulk Schedule Wizard'

    device_ids = fields.Many2many(
        'nhs.device',
        string='Devices',
        required=True,
        help='Devices to add schedules to.'
    )
    schedule_type_id = fields.Many2one(
        'nhs.device.schedule.type',
        string='Schedule Type',
        required=True,
        help='Type of schedule to create.'
    )
    interval_months = fields.Integer(
        string='Interval (Months)',
        required=True,
        default=12,
        help='Number of months between scheduled activities.'
    )
    last_done_date = fields.Date(
        string='Last Done Date',
        help='Date the activity was last completed. '
             'Used to compute the next due date.'
    )
    delivery = fields.Selection(
        selection=[
            ('in_house', 'In-House (EBME)'),
            ('contractor', 'External Contractor'),
        ],
        string='Delivery Method',
        default='in_house',
        help='Who performs the scheduled activity.'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(NHSDeviceBulkScheduleWizard, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'nhs.device' and self.env.context.get('active_ids'):
            res['device_ids'] = [(6, 0, self.env.context.get('active_ids'))]
        return res

    def action_create_schedules(self):
        """
        Create schedules for all selected devices.
        """
        for device in self.device_ids:
            existing = device.schedule_ids.filtered(
                lambda s: s.schedule_type_id == self.schedule_type_id
            )
            if existing:
                continue
            schedule_vals = {
                'device_id': device.id,
                'schedule_type_id': self.schedule_type_id.id,
                'interval_months': self.interval_months,
                'last_done_date': self.last_done_date,
                'delivery': self.delivery,
            }
            self.env['nhs.device.schedule'].create(schedule_vals)
        return {
            'type': 'ir.actions.act_window_close',
        }
