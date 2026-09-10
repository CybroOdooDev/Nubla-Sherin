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


class NhsWorkforceMember(models.Model):
    """Extend Workforce Member (from odoo_nhs_training) with the directorate-
    manager set Job Planning's own record rules need."""
    _inherit = 'nhs.workforce.member'

    unit_manager_ids = fields.Many2many(
        'res.users',
        compute='_compute_unit_manager_ids',
        store=True,
        help="Every manager/lead in this member's org-unit ancestor chain -"
             " lets a Job Planning Clinical Manager's record rule match this"
             " member (and, via member_id, their rostered duties) the same"
             " way nhs.job.plan.manager_ids already scopes job plans."
    )

    @api.depends('org_unit_id.parent_path')
    def _compute_unit_manager_ids(self):
        OrgUnit = self.env['nhs.org.unit']
        for member in self:
            if not member.org_unit_id or not member.org_unit_id.parent_path:
                member.unit_manager_ids = [(5, 0, 0)]
                continue
            ancestor_ids = [int(part) for part in member.org_unit_id.parent_path.split('/') if part]
            managers = OrgUnit.browse(ancestor_ids).mapped('manager_id')
            member.unit_manager_ids = [(6, 0, managers.ids)]
