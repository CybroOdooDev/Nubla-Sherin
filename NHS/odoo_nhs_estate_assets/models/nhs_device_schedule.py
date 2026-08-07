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
from dateutil.relativedelta import relativedelta
from datetime import date

class NHSDeviceSchedule(models.Model):
    _name = 'nhs.device.schedule'
    _description = 'NHS Device Maintenance Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_due_date'
    _rec_name = 'display_name'

    device_id = fields.Many2one(
        'nhs.device',
        string='Device',
        required=True,
        ondelete='cascade',
        help='The device this schedule applies to.'
    )
    schedule_type_id = fields.Many2one(
        'nhs.device.schedule.type',
        string='Schedule Type',
        required=True,
        ondelete='restrict',
        help='Type of scheduled activity (e.g. PPM, Calibration, Electrical Safety).'
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Display name combining device and schedule type.'
    )
    interval_months = fields.Integer(
        string='Interval (Months)',
        required=True,
        default=12,
        help='Recurrence in months between scheduled activities.'
    )
    last_done_date = fields.Date(
        string='Last Done Date',
        help='Last completed date (from the latest matching service event).'
    )
    next_due_date = fields.Date(
        string='Next Due Date',
        compute='_compute_next_due_date',
        store=True,
        help='Last done + interval. Date when the next activity is due.'
    )
    status = fields.Selection(
        selection=[
            ('ok', 'OK'),
            ('due_soon', 'Due Soon'),
            ('overdue', 'Overdue'),
        ],
        string='Status',
        compute='_compute_status',
        store=True,
        help='Current status of the schedule:\n'
             '- OK: Up to date (more than due_soon_window days remaining)\n'
             '- Due Soon: Approaching due date (within due_soon_window)\n'
             '- Overdue: Past due date'
    )
    is_escalated = fields.Boolean(
        string='Overdue Escalated',
        compute='_compute_is_escalated',
        store=True,
        help='True if the schedule is past due by more than the configured overdue escalation threshold (days).'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, the schedule is archived.'
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
    maintenance_request_id = fields.Many2one(
        'maintenance.request',
        string='Maintenance Request',
        help='Latest link to the Odoo maintenance request backing the recurrence.'
    )
    maintenance_request_ids = fields.One2many(
        'maintenance.request',
        'nhs_schedule_id',
        string='Maintenance Requests History',
        help='All maintenance requests generated for this schedule.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='device_id.company_id',
        store=True,
        help='Company owning the schedule (inherited from device).'
    )
    archived_by_device_id = fields.Many2one(
        'nhs.device',
        string='Archived with Device',
        copy=False,
        index=True,
        help='Tracks the device that triggered automated cascade archiving.'
    )

    @api.depends('next_due_date', 'status')
    def _compute_is_escalated(self):
        """
        Determine if overdue status exceeds the configured escalation threshold.
        Reads 'odoo_nhs_estate_assets.overdue_escalation_days' from ir.config_parameter.
        """
        today = date.today()
        try:
            overdue_escalation_days = int(self.env['ir.config_parameter'].sudo().get_param(
                'odoo_nhs_estate_assets.overdue_escalation_days',
                default=7
            ))
        except (ValueError, TypeError):
            overdue_escalation_days = 7
        for record in self:
            if record.status == 'overdue' and record.next_due_date:
                days_overdue = (today - record.next_due_date).days
                record.is_escalated = days_overdue >= overdue_escalation_days
            else:
                record.is_escalated = False

    def unlink(self):
        """
        Archive maintenance schedules instead of permanently deleting them.
        Displays a notification informing the user that nothing was permanently deleted
        and that the record was archived to preserve the safety & maintenance audit trail.
        """
        self.action_archive()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Schedule Archived',
                'message': 'Nothing was permanently deleted. The record was archived to preserve the safety '
                           'and maintenance audit trail.',
                'type': 'warning',
                'sticky': False,
            }
        }

    _schedule_unique = models.Constraint(
        'UNIQUE(device_id, schedule_type_id)',
        'A schedule of this type already exists for this device.',
    )

    @api.depends('device_id', 'schedule_type_id')
    def _compute_display_name(self):
        """Compute display name from device and schedule type."""
        for record in self:
            device_name = record.device_id.display_name or 'Unknown Device'
            schedule_type_name = record.schedule_type_id.name if record.schedule_type_id else 'No Type'
            record.display_name = '%s - %s' % (device_name, schedule_type_name)

    @api.depends('last_done_date', 'interval_months')
    def _compute_next_due_date(self):
        """
        Compute the next due date from the last done date and interval.
        next_due = last_done + interval_months
        If last_done_date is not set, no next_due_date is computed.
        """
        for record in self:
            if record.last_done_date and record.interval_months:
                record.next_due_date = record.last_done_date + relativedelta(months=record.interval_months)
            else:
                record.next_due_date = False

    @api.depends('next_due_date')
    def _compute_status(self):
        """
        Compute the schedule status based on the next due date.
        Status rules:
            - Overdue: next_due_date < today
            - Due Soon: next_due_date <= today + due_soon_window days
            - OK: next_due_date > today + due_soon_window days
        The due_soon_window is read from system configuration.
        Default is 30 days if not configured.
        """
        today = date.today()
        due_soon_window = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_estate_assets.due_soon_window',
            default=30
        ))
        for record in self:
            if not record.next_due_date:
                record.status = 'ok'
                continue
            days_until_due = (record.next_due_date - today).days
            if days_until_due < 0:
                record.status = 'overdue'
            elif days_until_due <= due_soon_window:
                record.status = 'due_soon'
            else:
                record.status = 'ok'

    @api.constrains('interval_months')
    def _check_interval_months(self):
        """Validate that interval is a positive number."""
        for record in self:
            if record.interval_months <= 0:
                raise ValidationError('Interval months must be greater than 0.')

    @api.constrains('last_done_date', 'next_due_date')
    def _check_dates(self):
        """Validate that dates are in a logical order."""
        for record in self:
            if record.last_done_date and record.next_due_date:
                if record.next_due_date <= record.last_done_date:
                    raise ValidationError('Next due date must be after the last done date.')

    def has_open_maintenance_request(self):
        """
        Check if there is an active open maintenance request for this schedule.
        An open request is one that is NOT in a final stage and NOT marked as completed.
        """
        self.ensure_one()
        open_requests = self.maintenance_request_ids.filtered(
            lambda r: not r.is_final_stage and not r.service_record_created
        )
        return bool(open_requests)

    def action_create_maintenance_request(self):
        """
        Create an Odoo maintenance request for this schedule if no open request exists.
        """
        created_requests = self.env['maintenance.request']
        for record in self:
            if record.device_id.status in ['decommissioned', 'disposed', 'out_of_service']:
                continue
            if not record.has_open_maintenance_request():
                type_name = record.schedule_type_id.name if record.schedule_type_id else ''
                equipment = self.env['maintenance.equipment'].search([
                    ('nhs_device_id', '=', record.device_id.id)
                ], limit=1)
                nhs_team = self.env['maintenance.team'].search([
                    ('name', '=', 'NHS Technician Team')
                ], limit=1)
                if not nhs_team:
                    nhs_team = self.env['maintenance.team'].create({
                        'name': 'NHS Technician Team',
                        'company_id': record.company_id.id,
                    })
                request = self.env['maintenance.request'].create({
                    'name': '%s - %s' % (record.device_id.display_name, type_name),
                    'request_date': fields.Date.today(),
                    'schedule_date': record.next_due_date or fields.Date.today(),
                    'maintenance_type': 'preventive',
                    'user_id': record.device_id.responsible_user_id.id or self.env.user.id,
                    'company_id': record.company_id.id,
                    'nhs_device_id': record.device_id.id,
                    'nhs_schedule_id': record.id,
                    'equipment_id': equipment.id if equipment else False,
                    'maintenance_team_id': (
                        equipment.maintenance_team_id.id
                        if equipment and equipment.maintenance_team_id
                        else nhs_team.id
                    ),
                })
                record.maintenance_request_id = request.id
                created_requests |= request

        if len(self) == 1:
            open_req = (self.maintenance_request_ids.filtered(lambda r: not r.is_final_stage)
                        or created_requests)
            return {
                'name': 'Maintenance Request',
                'type': 'ir.actions.act_window',
                'res_model': 'maintenance.request',
                'view_mode': 'form',
                'res_id': open_req[0].id if open_req else False,
            }
        return {
            'name': 'Maintenance Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_mode': 'list,form',
            'domain': [('nhs_schedule_id', 'in', self.ids)],
        }

    def action_view_maintenance_request(self):
        """
        Open the linked maintenance request or create one if none exists.
        """
        self.ensure_one()
        open_requests = self.maintenance_request_ids.filtered(lambda r: not r.is_final_stage)
        if not open_requests and not self.maintenance_request_id:
            return self.action_create_maintenance_request()

        res_id = open_requests[0].id if open_requests else self.maintenance_request_id.id
        return {
            'name': 'Maintenance Request',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_mode': 'form',
            'res_id': res_id,
        }

    @api.model
    def _cron_generate_maintenance_requests(self):
        """
        Cron job to continuously monitor device schedules.
        When a schedule reaches its Next Due Date and there is no existing open
        Maintenance Request for that schedule, automatically create an Odoo Maintenance Request.
        Only one active Maintenance Request per schedule is allowed at any time.
        """
        today = fields.Date.today()
        schedules = self.search([
            ('active', '=', True),
            ('next_due_date', '!=', False),
            ('next_due_date', '<=', today),
            ('device_id.active', '=', True),
            ('device_id.status', 'not in', ['decommissioned', 'disposed', 'out_of_service']),
        ])
        for schedule in schedules:
            if not schedule.has_open_maintenance_request():
                schedule.action_create_maintenance_request()

    @api.onchange('interval_months')
    def _onchange_interval_months(self):
        """
        When interval changes, recompute next_due_date.
        """
        if self.last_done_date and self.interval_months:
            self._compute_next_due_date()
