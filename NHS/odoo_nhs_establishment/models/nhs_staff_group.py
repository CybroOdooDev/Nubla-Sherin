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


class NhsStaffGroup(models.Model):
    """Standard NHS staff-group classification used to categorise posts for
    workforce reporting and national workforce data returns."""
    _name = 'nhs.staff.group'
    _description = 'NHS Staff Group'
    _order = 'sequence, name'

    name = fields.Char(
        string='Staff Group',
        required=True,
        translate=True,
        help="Standard NHS staff-group classification (e.g. 'Nursing & Midwifery',"
             " 'Medical & Dental', 'Allied Health Professionals (AHPs)'). Used throughout"
             " workforce reporting and in the national workforce data returns."
    )
    code = fields.Char(
        string='Code',
        help="Short code for the staff group, used in exports and national returns."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display order."
    )
    is_clinical = fields.Boolean(
        string='Clinical',
        default=True,
        help="Clinical vs non-clinical classification, used for reporting splits."
    )
    post_count = fields.Integer(
        string='Post Count',
        compute='_compute_post_count',
        help="Number of funded posts currently using this staff group."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag. Archived staff groups are hidden but retained for history."
    )

    _name_uniq = models.Constraint(
        'UNIQUE(name)',
        'A staff group with this name already exists!'
    )

    def _compute_post_count(self):
        """Count active posts using each staff group."""
        post_data = self.env['nhs.establishment.post']._read_group(
            [('staff_group_id', 'in', self.ids)],
            ['staff_group_id'], ['__count'],
        )
        counts = {group.id: count for group, count in post_data}
        for staff_group in self:
            staff_group.post_count = counts.get(staff_group.id, 0)
