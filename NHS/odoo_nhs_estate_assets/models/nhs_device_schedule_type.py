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
from odoo import fields, models

class NHSDeviceScheduleType(models.Model):
    _name = 'nhs.device.schedule.type'
    _description = 'NHS Device Schedule Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='Schedule Type Name',
        required=True,
        help='Name of the maintenance schedule type, e.g. Planned Preventive Maintenance, Calibration.'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique identifier code for the schedule type.'
    )
    description = fields.Text(
        string='Description',
        help='Full description of what activities this schedule type covers.'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order in which schedule types are displayed.'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, the schedule type is archived.'
    )

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'Schedule type code must be unique.',
    )
