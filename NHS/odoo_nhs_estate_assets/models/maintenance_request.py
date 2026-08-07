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

class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    nhs_device_id = fields.Many2one(
        'nhs.device',
        string='NHS Device',
        ondelete='set null',
        help='NHS device this maintenance request relates to.'
    )
    nhs_schedule_id = fields.Many2one(
        'nhs.device.schedule',
        string='NHS Device Schedule',
        ondelete='set null',
        domain="[('device_id', '=', nhs_device_id)]",
        help='Recurring NHS device maintenance schedule backing this request.'
    )
    nhs_service_id = fields.Many2one(
        'nhs.device.service',
        string='NHS Service Record',
        ondelete='set null',
        help='Completed NHS service record associated with this maintenance request.'
    )
    service_record_created = fields.Boolean(
        string='Service Record Created',
        default=False,
        copy=False,
        help='Flag indicating whether a service record has been generated for this request.'
    )
    is_final_stage = fields.Boolean(
        string='Is Final Stage',
        compute='_compute_is_final_stage',
        store=True,
        help='True when request is in a final/completed stage (Repaired or Scrap).'
    )

    @api.depends('stage_id', 'stage_id.fold', 'stage_id.name')
    def _compute_is_final_stage(self):
        """
        Compute if request is in a final stage (Repaired or Scrap or folded stage).
        """
        for record in self:
            stage_name = (record.stage_id.name or '').lower() if record.stage_id else ''
            record.is_final_stage = bool(
                record.stage_id and (
                    record.stage_id.fold or
                    'repair' in stage_name or
                    'scrap' in stage_name or
                    'done' in stage_name
                )
            )

    def action_create_service_record(self):
        """
        Open pre-filled NHS Service form view linked to device, schedule, and this request.
        No service record can be created while request is in New or In Progress.
        """
        self.ensure_one()
        if not self.is_final_stage:
            raise UserError('Service record can only be created when the request is in Repaired or Scrap stage.')
        if self.service_record_created and self.nhs_service_id:
            return {
                'name': 'NHS Service Record',
                'type': 'ir.actions.act_window',
                'res_model': 'nhs.device.service',
                'view_mode': 'form',
                'res_id': self.nhs_service_id.id,
            }

        stage_name = (self.stage_id.name or '').lower() if self.stage_id else ''
        is_scrap = 'scrap' in stage_name
        service_type = 'ppm'
        if self.nhs_schedule_id and self.nhs_schedule_id.schedule_type_id:
            code = (self.nhs_schedule_id.schedule_type_id.code or '').lower()
            if code in ['ppm', 'repair', 'calibration', 'electrical_safety', 'inspection']:
                service_type = code
        context = {
            'default_device_id': self.nhs_device_id.id if self.nhs_device_id else False,
            'default_schedule_id': self.nhs_schedule_id.id if self.nhs_schedule_id else False,
            'default_maintenance_request_id': self.id,
            'default_service_type': service_type,
            'default_service_date': fields.Date.today(),
            'default_outcome': 'removed_from_use' if is_scrap else 'pass',
            'default_notes': self.description or self.name,
        }
        return {
            'name': 'Create Service Record',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.service',
            'view_mode': 'form',
            'target': 'current',
            'context': context,
        }
