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

class NHSDeviceAlertLine(models.Model):
    _name = 'nhs.device.alert.line'
    _description = 'NHS Device Alert - Affected Device Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'alert_id, device_id'
    _rec_name = 'display_name'

    alert_id = fields.Many2one(
        'nhs.device.alert',
        string='Alert',
        required=True,
        ondelete='cascade',
        help='Parent safety alert. ondelete cascade - when alert is deleted, '
             'all affected device action lines are also deleted.'
    )
    device_id = fields.Many2one(
        'nhs.device',
        string='Device',
        required=True,
        help='Affected device that needs to be actioned for this alert.'
    )
    action_required = fields.Char(
        string='Action Required',
        help='What to do to this device. Can be specific action for this device, '
             'or inherited from the parent alert\'s required action.'
    )
    action_status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('quarantined', 'Quarantined'),
            ('actioned', 'Actioned'),
            ('not_affected', 'Not Affected'),
        ],
        string='Action Status',
        required=True,
        default='pending',
        help='Status of the action for this device:\n'
             '- Pending: Awaiting action\n'
             '- Quarantined: Device removed from use pending action\n'
             '- Actioned: Action completed\n'
             '- Not Affected: Device is not actually affected'
    )
    actioned_by_id = fields.Many2one(
        'res.users',
        string='Actioned By',
        help='Who performed the action. Automatically set when status changes '
             'to actioned or not_affected.'
    )
    actioned_date = fields.Date(
        string='Actioned Date',
        help='When the action was completed. Automatically set when status changes '
             'to actioned or not_affected.'
    )
    note = fields.Text(
        string='Note',
        help='Evidence of response. Notes about the action taken, findings, '
             'or additional information for audit trail.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='device_id.company_id',
        store=True,
        help='Company owning the line (inherited from device).'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, the line is archived.'
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Display name combining alert reference and device name.'
    )

    _alert_device_unique = models.Constraint(
        'UNIQUE(alert_id, device_id)',
        'A device can only be listed once per alert.',
    )

    @api.depends('alert_id', 'device_id')
    def _compute_display_name(self):
        """
        Compute display name from alert reference and device name.
        """
        for record in self:
            alert_name = record.alert_id.reference or record.alert_id.name or 'Unknown Alert'
            device_name = record.device_id.display_name or record.device_id.name or 'Unknown Device'
            record.display_name = '%s - %s' % (alert_name, device_name)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create alert lines with automatic actioned_by and actioned_date
        if status is actioned or not_affected.
        """
        for vals in vals_list:
            if vals.get('action_status') in ['actioned', 'not_affected']:
                if 'actioned_by_id' not in vals or not vals['actioned_by_id']:
                    vals['actioned_by_id'] = self.env.user.id
                if 'actioned_date' not in vals or not vals['actioned_date']:
                    vals['actioned_date'] = fields.Date.today()
        records = super(NHSDeviceAlertLine, self).create(vals_list)
        records.mapped('alert_id')._update_state_from_lines()
        return records

    def write(self, vals):
        """
        Override write to auto-set actioned details when status changes.
        """
        if 'action_status' in vals:
            for record in self:
                new_status = vals['action_status']
                if new_status in ['actioned', 'not_affected']:
                    if 'actioned_by_id' not in vals:
                        vals['actioned_by_id'] = self.env.user.id
                    if 'actioned_date' not in vals:
                        vals['actioned_date'] = fields.Date.today()
                elif new_status in ['pending', 'quarantined']:
                    vals['actioned_by_id'] = False
                    vals['actioned_date'] = False
        res = super(NHSDeviceAlertLine, self).write(vals)
        self.mapped('alert_id')._update_state_from_lines()
        return res

    @api.constrains('action_status', 'actioned_date', 'actioned_by_id')
    def _check_actioned_status(self):
        """
        Validate that actioned devices have actioned date and by whom.
        """
        for record in self:
            if record.action_status in ['actioned', 'not_affected']:
                if not record.actioned_date:
                    raise ValidationError(
                        'Actioned date is required when status is Actioned or Not Affected.'
                    )
                if not record.actioned_by_id:
                    raise ValidationError(
                        'Actioned by is required when status is Actioned or Not Affected.'
                    )
            else:
                if record.actioned_date:
                    raise ValidationError(
                        'Actioned date should not be set for status Pending and Quarantined.'
                    )
                if record.actioned_by_id:
                    raise ValidationError(
                        'Actioned by should not be set for status Pending and Quarantined.'
                    )

    def action_mark_pending(self):
        """
        Mark this line as pending.
        """
        for record in self:
            record.action_status = 'pending'
            record.actioned_by_id = False
            record.actioned_date = False

    def action_mark_quarantined(self):
        """
        Mark this line as quarantined (device removed from use).
        """
        for record in self:
            record.action_status = 'quarantined'
            if record.device_id:
                record.device_id.status = 'out_of_service'

    def action_mark_actioned(self):
        """
        Mark this line as actioned.
        """
        for record in self:
            record.action_status = 'actioned'
            record.actioned_by_id = self.env.user
            record.actioned_date = fields.Date.today()

    def action_mark_not_affected(self):
        """
        Mark this line as not affected.
        """
        for record in self:
            record.action_status = 'not_affected'
            record.actioned_by_id = self.env.user
            record.actioned_date = fields.Date.today()

    def action_view_device(self):
        """
        Open the device form for this line.
        """
        self.ensure_one()
        return {
            'name': 'Device',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device',
            'view_mode': 'form',
            'res_id': self.device_id.id,
        }

    def action_view_alert(self):
        """
        Open the alert form for this line.
        """
        self.ensure_one()
        return {
            'name': 'Safety Alert',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.alert',
            'view_mode': 'form',
            'res_id': self.alert_id.id,
        }

    @api.onchange('action_status')
    def _onchange_action_status(self):
        """
        When status changes, auto-set actioned details.
        """
        if self.action_status in ['actioned', 'not_affected']:
            self.actioned_by_id = self.env.user
            self.actioned_date = fields.Date.today()
        elif self.action_status in ['pending', 'quarantined']:
            self.actioned_by_id = False
            self.actioned_date = False

    @api.onchange('device_id')
    def _onchange_device_id(self):
        """
        When device changes, set default action_required from alert.
        """
        if self.device_id and self.alert_id:
            self.action_required = self.alert_id.required_action

    archived_by_device_id = fields.Many2one(
        'nhs.device',
        string='Archived with Device',
        copy=False,
        index=True,
        help='Tracks the device that triggered automated cascade archiving.'
    )

    def unlink(self):
        """
        Archive alert action lines instead of permanently deleting them.
        Displays a notification informing the user that nothing was permanently deleted
        and that the record was archived to preserve the safety & maintenance audit trail.
        """
        self.action_archive()
        self.mapped('alert_id')._update_state_from_lines()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Alert Line Archived',
                'message': 'Nothing was permanently deleted. The record was archived to preserve the safety '
                           'and maintenance audit trail.',
                'type': 'warning',
                'sticky': False,
            }
        }
