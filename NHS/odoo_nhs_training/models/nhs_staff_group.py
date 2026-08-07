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
##############################################################################
from odoo import fields, models


class NhsStaffGroup(models.Model):
    _inherit = 'nhs.staff.group'

    requirement_ids = fields.One2many(
        'nhs.training.requirement',
        'staff_group_id',
        string='Training Requirements',
        help="Training subjects required by this staff group."
    )
    requirement_count = fields.Integer(
        string='Requirement Count',
        compute='_compute_requirement_count',
        help="Number of training requirements defined on this staff group."
    )

    def _compute_requirement_count(self):
        """Count the training requirements defined on this staff group."""
        for record in self:
            record.requirement_count = len(record.requirement_ids)

    def action_view_training_requirements(self):
        """Open the training requirements defined on this staff group."""
        self.ensure_one()
        return {
            'name': 'Training Requirements',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.training.requirement',
            'view_mode': 'list,form',
            'domain': [('staff_group_id', '=', self.id)],
            'context': {
                'default_staff_group_id': self.id,
                'hide_staff_group_id': True,
            },
        }
