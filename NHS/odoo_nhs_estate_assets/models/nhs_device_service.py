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
from odoo.exceptions import ValidationError
from datetime import date

class NHSDeviceService(models.Model):
    _name = 'nhs.device.service'
    _description = 'NHS Device Service Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'service_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help='Sequenced service event reference number.'
    )
    device_id = fields.Many2one(
        'nhs.device',
        string='Device',
        required=True,
        ondelete='cascade',
        help='The device that was serviced.'
    )
    schedule_id = fields.Many2one(
        'nhs.device.schedule',
        string='Schedule',
        domain="[('device_id', '=', device_id)]",
        help='The schedule this service fulfils (if scheduled).'
    )
    maintenance_request_id = fields.Many2one(
        'maintenance.request',
        string='Maintenance Request',
        ondelete='set null',
        help='The maintenance request backing this service event (if created from a request).'
    )
    warranty_id = fields.Many2one(
        'nhs.device.warranty',
        string='Warranty / Service Contract',
        domain="[('device_id', '=', device_id)]",
        help='The active warranty or service contract covering this service event.'
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
        help='Result of the service:\n'
             '- Pass: Service completed successfully\n'
             '- Pass with Note: Completed with minor observations\n'
             '- Fail: Device failed, requires further attention\n'
             '- Removed from Use: Device condemned/removed'
    )
    downtime_hours = fields.Float(
        string='Downtime (Hours)',
        help='Out-of-service time in hours (for repairs).'
    )
    cost = fields.Monetary(
        string='Service Cost',
        currency_field='currency_id',
        help='Service cost (informational).'
    )
    parts_used = fields.Text(
        string='Parts Used',
        help='Spare parts, replacement components, or materials consumed during service.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='device_id.currency_id',
        help='Currency of the service cost.'
    )
    certificate_ref = fields.Char(
        string='Certificate Reference',
        help='Calibration/service certificate reference number.'
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
        help='Certificates, reports, or other supporting documents.'
    )
    notes = fields.Text(
        string='Notes',
        help='Findings, observations, or additional details about the service.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='device_id.company_id',
        store=True,
        help='Company owning the service record (inherited from device).'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, the service record is archived.'
    )
    archived_by_device_id = fields.Many2one(
        'nhs.device',
        string='Archived with Device',
        copy=False,
        index=True,
        help='Tracks the device that triggered automated cascade archiving.'
    )

    _cost_positive = models.Constraint(
        'CHECK(cost >= 0)',
        'Service cost must be a positive number.',
    )

    _downtime_positive = models.Constraint(
        'CHECK(downtime_hours >= 0)',
        'Downtime hours must be a positive number.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create service records with:
        1. Auto-sequenced references
        2. Automatic schedule progression and device status update
        """
        for vals in vals_list:
            if 'name' not in vals or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('nhs.device.service') or 'New'
        records = super(NHSDeviceService, self).create(vals_list)
        for record in records:
            record._process_outcome()
        return records

    def write(self, vals):
        """
        Override write to process outcome changes.
        """
        res = super(NHSDeviceService, self).write(vals)
        if 'outcome' in vals or 'device_id' in vals:
            for record in self:
                record._process_outcome()
        return res

    def _process_outcome(self):
        """
        Process the service outcome:
            - 'pass'/'pass_with_note': Set schedule last_done_date, calculate next_due_date, update status.
            - 'fail': Set device status to awaiting_repair. Do NOT roll schedule forward.
            - 'removed_from_use': Set device status to out_of_service. Do NOT roll schedule forward. Deactivate future schedule.
            - Sync with linked maintenance request if present.
        """
        for record in self:
            # Sync with maintenance request
            if record.maintenance_request_id:
                record.maintenance_request_id.sudo().write({
                    'nhs_service_id': record.id,
                    'service_record_created': True,
                })
            if record.outcome in ['pass', 'pass_with_note']:
                if record.schedule_id:
                    record.schedule_id.last_done_date = record.service_date
                    record.schedule_id._compute_next_due_date()
                    record.schedule_id._compute_status()
                if record.device_id.status == 'awaiting_repair':
                    record.device_id.status = 'in_service'
            elif record.outcome == 'fail':
                if record.device_id.status not in ['out_of_service', 'decommissioned', 'disposed']:
                    record.device_id.status = 'awaiting_repair'
            elif record.outcome == 'removed_from_use':
                if record.device_id.status not in ['decommissioned', 'disposed']:
                    record.device_id.status = 'out_of_service'
                if record.schedule_id:
                    record.schedule_id.active = False

    @api.constrains('service_date')
    def _check_service_date(self):
        """
        Validate that the service date is not in the future.
        """
        today = date.today()
        for record in self:
            if record.service_date and record.service_date > today:
                raise ValidationError('Service date cannot be in the future.')

    @api.constrains('device_id', 'schedule_id')
    def _check_schedule_device_match(self):
        """
        Validate that the schedule belongs to the device.
        """
        for record in self:
            if record.schedule_id and record.schedule_id.device_id != record.device_id:
                raise ValidationError(
                    'The selected schedule does not belong to this device.'
                )

    @api.constrains('performed_by_id', 'contractor')
    def _check_performer(self):
        """
        Validate that either in-house engineer or contractor is specified.
        """
        for record in self:
            if not record.performed_by_id and not record.contractor:
                raise ValidationError(
                    'Please specify either the in-house engineer or the contractor.'
                )

    def action_view_device(self):
        """
        Open the device form for this service record.
        """
        self.ensure_one()
        return {
            'name': 'Device',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device',
            'view_mode': 'form',
            'res_id': self.device_id.id,
        }

    def action_view_schedule(self):
        """
        Open the schedule form for this service record (if linked).
        """
        self.ensure_one()
        if not self.schedule_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': 'Schedule',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.schedule',
            'view_mode': 'form',
            'res_id': self.schedule_id.id,
        }

    def unlink(self):
        """
        Archive service records instead of permanently deleting them.
        Displays a notification informing the user that nothing was permanently deleted
        and that the record was archived to preserve the safety & maintenance audit trail.
        """
        self.action_archive()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Service Record Archived',
                'message': 'Nothing was permanently deleted. The record was archived to preserve the safety '
                           'and maintenance audit trail.',
                'type': 'warning',
                'sticky': False,
            }
        }

    @api.model
    def get_import_templates(self):
        """Provide standard templates available for importing services.
        Returns a list of dicts specifying labels and template asset file paths.
        """
        return [{
            'label': 'Import Template for Services',
            'template': '/odoo_nhs_estate_assets/static/import_templates/services.xlsx',
        }]

    def action_view_documents(self):
        """Return an action showing all documents and attachments linked to this tenure.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.device.service'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.device.service',
                'default_res_id': self.id,
            }
        }