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

class NHSDeviceWarranty(models.Model):
    _name = 'nhs.device.warranty'
    _description = 'NHS Device Warranty / Service Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'
    _rec_name = 'display_name'

    device_id = fields.Many2one(
        'nhs.device',
        string='Device',
        required=True,
        ondelete='cascade',
        help='Covered device. ondelete cascade - when device is deleted, '
             'all warranties/contracts are also deleted.'
    )
    cover_type = fields.Selection(
        selection=[
            ('warranty', 'Warranty'),
            ('service_contract', 'Service Contract'),
        ],
        string='Type',
        required=True,
        default='warranty',
        help='Whether this is a manufacturer warranty or a service contract.'
    )
    provider = fields.Char(
        string='Provider',
        help='Provider/vendor name (manufacturer or service contractor).'
    )
    reference = fields.Char(
        string='Reference',
        help='Contract or warranty reference number.'
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        help='Date coverage starts.'
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        required=True,
        help='Date coverage expires. Expiry reminder is raised ahead of this date.'
    )
    coverage = fields.Text(
        string='Coverage Description',
        help='What is covered by this warranty/contract. '
             'e.g. "Parts and labour", "On-site service", "Calibration included".'
    )
    cost = fields.Monetary(
        string='Cost',
        currency_field='currency_id',
        help='Contract cost (informational).'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='device_id.currency_id',
        help='Currency of the contract cost.'
    )
    is_expiring = fields.Boolean(
        string='Is Expiring',
        compute='_compute_is_expiring',
        store=True,
        help='Within the reminder window of expiry. '
             'True if expiry_date is within the configured reminder window.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='device_id.company_id',
        store=True,
        help='Company owning the record (inherited from device).'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, the warranty/contract is archived.'
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Display name combining device name, asset tag, and warranty type.'
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
        'Cost must be a positive number.',
    )

    @api.depends('device_id', 'cover_type', 'device_id.asset_tag', 'device_id.display_name')
    def _compute_display_name(self):
        """
        Compute display name from device name, asset tag, and warranty type.
        Example: "[NHS-0001] Infusion Pump - Warranty"
        """
        for record in self:
            device_name = record.device_id.display_name or record.device_id.name or 'Unknown Device'
            cover_type_label = dict(self._fields['cover_type'].selection).get(
                record.cover_type, record.cover_type or ''
            )
            record.display_name = '%s - %s' % (device_name, cover_type_label)

    @api.depends('expiry_date')
    def _compute_is_expiring(self):
        """
        Determine if the warranty/contract is expiring soon.
        A record is expiring if expiry_date is within the configured
        expiry_reminder_window days from today.
        Default window is 90 days if not configured.
        """
        today = date.today()
        expiry_reminder_window = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_estate_assets.expiry_reminder_window',
            default=30
        ))
        for record in self:
            if not record.expiry_date:
                record.is_expiring = False
                continue
            days_until_expiry = (record.expiry_date - today).days
            record.is_expiring = 0 <= days_until_expiry <= expiry_reminder_window

    @api.constrains('start_date', 'expiry_date')
    def _check_dates(self):
        """
        Validate that dates are in a logical order.
        """
        for record in self:
            if record.start_date and record.expiry_date:
                if record.expiry_date < record.start_date:
                    raise ValidationError('Expiry date cannot be before start date.')

    @api.constrains('start_date')
    def _check_start_date(self):
        """
        Validate that start date is not in the future.
        """
        for record in self:
            if record.start_date and record.start_date > fields.Date.today():
                raise ValidationError('Start date cannot be in the future.')

    def action_view_device(self):
        """
        Open the device form for this warranty/contract.
        """
        self.ensure_one()
        return {
            'name': 'Device',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device',
            'view_mode': 'form',
            'res_id': self.device_id.id,
        }

    def action_view_services(self):
        """
        Open the service history for the selected device.
        """
        return {
            'name': 'Service History',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.service',
            'view_mode': 'list,form',
            'domain': [('warranty_id', '=', self.id)],
        }

    def get_cover_type_display(self):
        """
        Returns the human-readable label for the cover_type field.
        Example: 'warranty' -> 'Warranty', 'service_contract' -> 'Service Contract'
        """
        self.ensure_one()
        return dict(self._fields['cover_type'].selection).get(
            self.cover_type,
            self.cover_type or ''
        )

    @api.model
    def _cron_check_expiring(self):
        """
        Cron job to check expiring warranties and service contracts.
        Creates Odoo activities for responsible users so expiring items appear in their To-Do list.
        """
        today = date.today()
        todo_activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not todo_activity_type:
            return
        device_model_id = self.env['ir.model']._get_id('nhs.device')
        expiring = self.search([('is_expiring', '=', True)])
        for w in expiring:
            device = w.device_id
            assignee = device._get_responsible_or_manager_user()
            summary = "[Expiring %s] %s - %s" % (
                w.get_cover_type_display(), w.provider or 'Contractor', device.display_name
            )
            note = "%s (reference - %s) for device %s expires on %s." % (
                w.get_cover_type_display(), w.reference or 'N/A', device.asset_tag, w.expiry_date
            )
            existing_activity = self.env['mail.activity'].search([
                ('res_id', '=', device.id),
                ('res_model_id', '=', device_model_id),
                ('summary', '=', summary),
            ], limit=1)
            if not existing_activity:
                self.env['mail.activity'].create({
                    'activity_type_id': todo_activity_type.id,
                    'summary': summary,
                    'note': note,
                    'res_id': device.id,
                    'res_model_id': device_model_id,
                    'user_id': assignee.id,
                    'date_deadline': w.expiry_date or today,
                })

    def unlink(self):
        """
        Archive warranties and contracts instead of permanently deleting them.
        Displays a notification informing the user that nothing was permanently deleted
        and that the record was archived to preserve the safety & maintenance audit trail.
        """
        self.action_archive()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Warranty Archived',
                'message': 'Nothing was permanently deleted. The record was archived to preserve the safety '
                           'and maintenance audit trail.',
                'type': 'warning',
                'sticky': False,
            }
        }

    @api.model
    def get_import_templates(self):
        """Provide standard templates available for importing warranty.
        Returns a list of dicts specifying labels and template asset file paths.
        """
        return [{
            'label': 'Import Template for Warranty',
            'template': '/odoo_nhs_estate_assets/static/import_templates/warranty.xlsx',
        }]
