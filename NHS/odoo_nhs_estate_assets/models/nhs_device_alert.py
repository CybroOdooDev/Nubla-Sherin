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
from datetime import date, timedelta

class NHSDeviceAlert(models.Model):
    _name = 'nhs.device.alert'
    _description = 'A device safety alert (MHRA / CAS / manufacturer FSN)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issued_date desc, id desc'

    name = fields.Char(
        string='Alert Title',
        required=True,
        help='Alert title or description of the safety alert.'
    )
    reference = fields.Char(
        string='Reference',
        required=True,
        help='Alert reference number (MHRA/CAS/FSN number).'
    )
    source = fields.Selection(
        selection=[
            ('mhra', 'MHRA'),
            ('cas', 'CAS'),
            ('manufacturer_fsn', 'Manufacturer FSN'),
            ('other', 'Other'),
        ],
        string='Source',
        required=True,
        default='mhra',
        help='Source of the safety alert.'
    )
    issued_date = fields.Date(
        string='Issued Date',
        required=True,
        default=fields.Date.today,
        help='Date the alert was issued.'
    )
    action_deadline = fields.Date(
        string='Action Deadline',
        help='Deadline for required action.'
    )
    affected_make = fields.Char(
        string='Affected Manufacturer',
        help='Device manufacturer affected by this alert. '
             'Used for automatic matching to find affected devices.'
    )
    affected_model = fields.Char(
        string='Affected Model',
        help='Device model affected by this alert. '
             'Used for automatic matching to find affected devices.'
    )
    affected_category_id = fields.Many2one(
        'nhs.device.category',
        string='Affected Category',
        help='Device category affected by this alert. '
             'Used for automatic matching to find affected devices.'
    )
    description = fields.Text(
        string='Description',
        help='What the alert says. Full description of the alert and the issue it addresses.'
    )
    required_action = fields.Text(
        string='Required Action',
        help='Action the organisation must take to address the alert.'
    )
    state = fields.Selection(
        selection=[
            ('open', 'Open'),
            ('in_progress', 'In Progress'),
            ('closed', 'Closed'),
        ],
        string='State',
        required=True,
        default='open',
        help='Current state of the alert:\n'
             '- Open: Alert received, not yet actioned\n'
             '- In Progress: Affected devices being actioned\n'
             '- Closed: All affected devices have been actioned'
    )
    line_ids = fields.One2many(
        'nhs.device.alert.line',
        'alert_id',
        string='Affected Devices',
        help='Affected-device action lines.'
    )
    affected_count = fields.Integer(
        string='Affected Count',
        compute='_compute_counts',
        store=True,
        help='Progress: total number of devices affected by this alert.'
    )
    actioned_count = fields.Integer(
        string='Actioned Count',
        compute='_compute_counts',
        store=True,
        help='Progress: number of affected devices that have been actioned.'
    )
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_is_overdue',
        store=True,
        help='Past deadline with unactioned devices. '
             'True if the alert is past the action deadline with pending devices.'
    )
    is_expiring = fields.Boolean(
        string='Is Expiring Soon',
        compute='_compute_is_expiring',
        store=True,
        help='Deadline approaching (within 7 days) with pending devices.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Company owning the alert.'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, the alert is archived.'
    )

    _reference_unique = models.Constraint(
        'UNIQUE(reference)',
        'Alert reference must be unique.',
    )

    def _update_state_from_lines(self):
        """
        Automatically update the alert state based on the status of
        its affected device lines.
        Rules:
        - Closed: All lines are Actioned or Not Affected.
        - In Progress: At least one line is Pending or Quarantined.
        """
        for alert in self:
            if not alert.line_ids:
                continue
            pending_lines = alert.line_ids.filtered(
                lambda l: l.action_status in ('pending', 'quarantined')
            )
            if pending_lines:
                alert.state = 'in_progress'
            else:
                alert.state = 'closed'

    @api.depends('line_ids', 'line_ids.action_status')
    def _compute_counts(self):
        """
        Compute the total affected and actioned counts.
        """
        for record in self:
            record.affected_count = len(record.line_ids)
            record.actioned_count = len(
                record.line_ids.filtered(
                    lambda l: l.action_status in ['actioned', 'not_affected']
                )
            )

    @api.depends('action_deadline', 'line_ids.action_status')
    def _compute_is_overdue(self):
        """
        Determine if the alert is overdue.
        An alert is overdue if:
            - There is an action deadline
            - The deadline has passed
            - There are still pending or quarantined devices
        """
        today = date.today()
        for record in self:
            if not record.action_deadline or record.action_deadline > today:
                record.is_overdue = False
                continue
            pending_devices = record.line_ids.filtered(
                lambda l: l.action_status in ['pending', 'quarantined']
            )
            record.is_overdue = bool(pending_devices)

    @api.depends('action_deadline', 'line_ids.action_status', 'state')
    def _compute_is_expiring(self):
        """
        Determine if the safety alert action deadline is approaching (within next 7 days)
        and still has pending or quarantined devices.
        """
        today = date.today()
        upcoming = today + timedelta(days=7)
        for record in self:
            if record.state not in ['open', 'in_progress'] or not record.action_deadline:
                record.is_expiring = False
                continue
            pending_devices = record.line_ids.filtered(
                lambda l: l.action_status in ['pending', 'quarantined']
            )
            record.is_expiring = bool(pending_devices) and (today <= record.action_deadline <= upcoming)

    @api.constrains('issued_date', 'action_deadline')
    def _check_dates(self):
        """
        Validate that dates are in a logical order.
        """
        for record in self:
            if record.issued_date and record.action_deadline:
                if record.action_deadline < record.issued_date:
                    raise ValidationError('Action deadline cannot be before the issued date.')

    @api.constrains('state', 'line_ids')
    def _check_closed_state(self):
        """
        Validate that closed alerts have all devices actioned.
        """
        for record in self:
            if record.state == 'closed':
                pending = record.line_ids.filtered(
                    lambda l: l.action_status in ['pending', 'quarantined']
                )
                if pending:
                    raise ValidationError(
                        'Cannot close the alert. %s device(s) are still pending action.'
                        % len(pending)
                    )

    def action_match_devices(self):
        """
        Open the alert match wizard to automatically find affected devices
        by make, model, or category.
        """
        self.ensure_one()
        return {
            'name': 'Match Affected Devices',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.alert.match.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_alert_id': self.id,
                'default_affected_make': self.affected_make,
                'default_affected_model': self.affected_model,
                'default_affected_category_id': self.affected_category_id.id,
            }
        }

    def action_close_alert(self):
        """
        Close the alert if all affected devices have been actioned.
        """
        for record in self:
            if record.affected_count == 0:
                raise ValidationError(
                    'Cannot close the alert. No devices are affected.'
                )
            if record.affected_count == record.actioned_count:
                record.state = 'closed'
                record.message_post(body='Alert closed successfully.')
            else:
                pending_count = record.affected_count - record.actioned_count
                raise ValidationError(
                    'Cannot close the alert. %s device(s) are still pending action.'
                    % pending_count
                )

    def action_reopen_alert(self):
        """
        Reopen a closed alert.
        """
        for record in self:
            record.state = 'in_progress'
            record.message_post(body='Alert reopened.')

    def action_view_affected_devices(self):
        """
        Open the list of affected devices.
        """
        self.ensure_one()
        return {
            'name': ('Affected Devices - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.alert.line',
            'view_mode': 'list,form',
            'domain': [('alert_id', '=', self.id)],
            'context': {'default_alert_id': self.id},
        }

    def action_generate_report(self):
        """
        Generate the alert response report.
        """
        self.ensure_one()
        return self.env.ref('odoo_nhs_estate_assets.action_report_nhs_alert_response').report_action(self)


    def _create_pending_device_activities(self):
        """
        For open / in-progress safety alerts with pending or quarantined devices,
        create activities for the responsible person (or manager fallback)
        to complete required safety alert actions before deadline.
        Supports both initial action activities and expiring reminders.
        """
        today = date.today()
        warning_activity_type = self.env.ref('mail.mail_activity_data_warning', raise_if_not_found=False) or \
                                self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not warning_activity_type:
            return
        device_model_id = self.env['ir.model']._get_id('nhs.device')
        for alert in self.filtered(lambda a: a.state in ['open', 'in_progress']):
            pending_lines = alert.line_ids.filtered(lambda l:
                                                    l.action_status in ['pending', 'quarantined'])
            days_remaining = (alert.action_deadline - today).days if (alert.action_deadline and
                                                                      alert.action_deadline >= today) else None
            is_expiring_soon = days_remaining is not None and days_remaining <= 7
            for line in pending_lines:
                device = line.device_id
                if not device:
                    continue
                assignee = device._get_responsible_or_manager_user()
                status_display = dict(line._fields['action_status'].selection or []).get(line.action_status,
                                                                                         line.action_status)
                if is_expiring_soon:
                    summary = "[SAFETY ALERT EXPIRING REMINDER] %s - %s" % (alert.reference or alert.name,
                                                                            device.display_name)
                    note = (
                        "URGENT ALERT EXPIRING REMINDER: Safety Alert '%s' (%s) deadline is %s (%s day(s) remaining).\n"
                        "Device: %s (Asset Tag: %s)\n"
                        "Current Status: %s\n"
                        "Required Action: %s"
                    ) % (
                        alert.name, alert.reference or 'N/A', alert.action_deadline, days_remaining,
                        device.display_name, device.asset_tag, status_display,
                        line.action_required or alert.required_action or 'N/A'
                    )
                else:
                    summary = "[SAFETY ALERT ACTION REQUIRED] %s - %s" % (alert.reference or alert.name,
                                                                          device.display_name)
                    note = (
                        "Safety Alert '%s' (%s) requires action for device %s (Asset Tag: %s).\n"
                        "Current Status: %s\n"
                        "Required Action: %s\n"
                        "Action Deadline: %s"
                    ) % (
                        alert.name, alert.reference or 'N/A', device.display_name, device.asset_tag,
                        status_display, line.action_required or alert.required_action or 'N/A',
                        alert.action_deadline or 'N/A'
                    )
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', device.id),
                    ('res_model_id', '=', device_model_id),
                    ('summary', '=', summary),
                ], limit=1)
                if not existing_activity:
                    self.env['mail.activity'].create({
                        'activity_type_id': warning_activity_type.id,
                        'summary': summary,
                        'note': note,
                        'res_id': device.id,
                        'res_model_id': device_model_id,
                        'user_id': assignee.id,
                        'date_deadline': alert.action_deadline or today,
                    })

    @api.model
    def _cron_check_overdue(self):
        """
        Cron job to check overdue and expiring safety alerts and pending device actions.
        Creates activities for responsible users for pending/quarantined devices,
        and high-priority activities for overdue and expiring safety alerts.
        """
        today = date.today()
        active_alerts = self.search([('state', 'in', ['open', 'in_progress'])])
        active_alerts._create_pending_device_activities()
        warning_activity_type = self.env.ref('mail.mail_activity_data_warning', raise_if_not_found=False) or \
                                self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not warning_activity_type:
            return
        alert_model_id = self.env['ir.model']._get_id('nhs.device.alert')
        expiring_alerts = active_alerts.filtered(lambda a: a.is_expiring)
        for alert in expiring_alerts:
            days_remaining = (alert.action_deadline - today).days
            pending_count = len(alert.line_ids.filtered(lambda l:
                                                        l.action_status in ['pending', 'quarantined']))
            summary = "[SAFETY ALERT EXPIRING REMINDER] Safety Alert %s (%s)" % (alert.reference or alert.name,
                                                                                 alert.name)
            note = ("Safety alert %s (%s) action deadline is approaching on %s (%s day(s) remaining) with %s "
                    "unactioned device(s).") % (alert.reference or 'N/A', alert.name, alert.action_deadline,
                                                days_remaining, pending_count
            )
            existing_activity = self.env['mail.activity'].search([
                ('res_id', '=', alert.id),
                ('res_model_id', '=', alert_model_id),
                ('summary', '=', summary),
            ], limit=1)
            if not existing_activity:
                self.env['mail.activity'].create({
                    'activity_type_id': warning_activity_type.id,
                    'summary': summary,
                    'note': note,
                    'res_id': alert.id,
                    'res_model_id': alert_model_id,
                    'user_id': self.env.user.id,
                    'date_deadline': alert.action_deadline,
                })
        overdue_alerts = active_alerts.filtered(lambda a: a.is_overdue)
        for alert in overdue_alerts:
            summary = "[OVERDUE SAFETY ALERT] %s (%s)" % (alert.reference or alert.name, alert.name)
            note = "Safety alert %s (%s) is past action deadline %s with %s unactioned devices." % (
                alert.reference or 'N/A', alert.name, alert.action_deadline, alert.affected_count - alert.actioned_count
            )
            existing_activity = self.env['mail.activity'].search([
                ('res_id', '=', alert.id),
                ('res_model_id', '=', alert_model_id),
                ('summary', '=', summary),
            ], limit=1)
            if not existing_activity:
                self.env['mail.activity'].create({
                    'activity_type_id': warning_activity_type.id,
                    'summary': summary,
                    'note': note,
                    'res_id': alert.id,
                    'res_model_id': alert_model_id,
                    'user_id': self.env.user.id,
                    'date_deadline': alert.action_deadline or today,
                })

    def unlink(self):
        """
        Archive safety alerts instead of permanently deleting them.
        Displays a notification informing the user that nothing was permanently deleted
        and that the record was archived to preserve the safety & maintenance audit trail.
        """
        for alert in self:
            alert.line_ids.action_archive()
        self.action_archive()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Safety Alert Archived',
                'message': 'Nothing was permanently deleted. The record was archived to preserve the safety '
                           'and maintenance audit trail.',
                'type': 'warning',
                'sticky': True,
            }
        }
