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

class NHSDeviceCategory(models.Model):
    _name = 'nhs.device.category'
    _description = 'NHS Device Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _parent_store = True
    _rec_name = 'complete_name'

    name = fields.Char(
        string='Category Name',
        required=True,
        help='Category name, e.g. "Infusion Pump", "Patient Monitor", "Imaging".'
    )
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True,
        help='Full hierarchical name including parent categories.'
    )
    parent_id = fields.Many2one(
        'nhs.device.category',
        string='Parent Category',
        ondelete='restrict',
        help='Parent category for hierarchical grouping. '
             'Leave empty for top-level categories.'
    )
    child_ids = fields.One2many(
        'nhs.device.category',
        'parent_id',
        string='Child Categories',
        help='Sub-categories under this category.'
    )
    parent_path = fields.Char(
        string='Parent Path',
        index=True,
        help='Materialized path for efficient hierarchical queries.'
    )
    default_life_years = fields.Integer(
        string='Default Life (Years)',
        default=7,
        help='Default expected economic/service life in years for devices in this category. '
             'Used to compute the replacement year.'
    )
    default_schedule_ids = fields.One2many(
        'nhs.device.category.schedule',
        'category_id',
        string='Default Schedules',
        help='Default maintenance schedules that will be automatically copied to every new device '
             'created in this category. e.g. PPM every 12 months, Calibration every 12 months.'
    )
    is_clinical = fields.Boolean(
        string='Clinical Category',
        default=True,
        help='Clinical device category (informational). Used for filtering and reporting.'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Archive flag. If unchecked, the category is archived and hidden from most views.'
    )

    _name_unique = models.Constraint(
        'UNIQUE(name)',
        'Category name must be unique.',
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """Compute the complete hierarchical name for the category."""
        for record in self:
            if record.parent_id:
                record.complete_name = '%s / %s' % (record.parent_id.complete_name, record.name)
            else:
                record.complete_name = record.name

    def _get_active_default_schedules(self):
        """Get all active default schedules for this category."""
        return self.default_schedule_ids.filtered('active')

    def _copy_default_schedules_to_device(self, device):
        """
        Copy all active default schedules from this category to a device.
        This is called when a new device is created.
        """
        for default_schedule in self._get_active_default_schedules():
            if not default_schedule.schedule_type_id:
                continue
            existing = device.schedule_ids.filtered(
                lambda s: s.schedule_type_id == default_schedule.schedule_type_id
            )
            if existing:
                continue
            schedule_vals = {
                'schedule_type_id': default_schedule.schedule_type_id.id,
                'interval_months': default_schedule.interval_months,
                'delivery': default_schedule.delivery,
                'last_done_date': False,
            }
            if device.id and isinstance(device.id, int):
                schedule_vals['device_id'] = device.id
                device.env['nhs.device.schedule'].create(schedule_vals)
            else:
                device.schedule_ids = [(0, 0, schedule_vals)]

    def _add_missing_schedules_to_device(self, device):
        """
        Add any missing default schedules from this category to a device.
        This does NOT remove existing schedules.
        Called when category is changed on an existing device or during onchange.
        """
        existing_types = device.schedule_ids.mapped('schedule_type_id')
        default_schedules = self._get_active_default_schedules()
        added_count = 0
        new_schedules = []
        for default_schedule in default_schedules:
            if default_schedule.schedule_type_id and default_schedule.schedule_type_id not in existing_types:
                schedule_vals = {
                    'schedule_type_id': default_schedule.schedule_type_id.id,
                    'interval_months': default_schedule.interval_months,
                    'delivery': default_schedule.delivery,
                    'last_done_date': default_schedule.last_done_date,
                }
                if device.id and isinstance(device.id, int):
                    schedule_vals['device_id'] = device.id
                    device.env['nhs.device.schedule'].create(schedule_vals)
                else:
                    new_schedules.append((0, 0, schedule_vals))
                added_count += 1
        if new_schedules:
            device.schedule_ids = new_schedules
        return added_count

    @api.constrains('default_life_years')
    def _check_default_life_years(self):
        """Validate that default life years is a positive number."""
        for record in self:
            if record.default_life_years and record.default_life_years <= 0:
                raise ValidationError('Default life years must be a positive number.')

    def action_view_devices(self):
        """List the devices having the current category"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Devices',
            'res_model': 'nhs.device',
            'view_mode': 'list,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id}
        }

class NHSDeviceCategorySchedule(models.Model):
    _name = 'nhs.device.category.schedule'
    _description = 'NHS Category Default Schedule'
    _order = 'category_id, schedule_type_id'

    category_id = fields.Many2one(
        'nhs.device.category',
        string='Category',
        required=True,
        ondelete='cascade',
        help='The category this default schedule belongs to.'
    )
    schedule_type_id = fields.Many2one(
        'nhs.device.schedule.type',
        string='Schedule Type',
        required=True,
        ondelete='restrict',
        help='Type of maintenance schedule.'
    )
    interval_months = fields.Integer(
        string='Interval (Months)',
        required=True,
        default=12,
        help='Number of months between scheduled activities.'
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
    last_done_date = fields.Date(
        string='Last Done Date',
        help='Default last done date. If set, next due date is computed from this date.'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, this schedule configuration is archived.'
    )

    _category_schedule_unique = models.Constraint(
        'UNIQUE(category_id, schedule_type_id)',
        'A category can only have one default configuration per schedule type.',
    )

    @api.constrains('interval_months')
    def _check_interval_months(self):
        """Validate that interval is a positive number."""
        for record in self:
            if record.interval_months <= 0:
                raise ValidationError('Interval months must be greater than 0.')

    @api.constrains('last_done_date')
    def _check_last_done_date(self):
        """Validate that last done date is not in the future."""
        for record in self:
            if record.last_done_date and record.last_done_date > fields.Date.today():
                raise ValidationError('Last done date cannot be in the future.')
