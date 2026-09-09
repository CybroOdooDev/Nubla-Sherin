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
from odoo import models

class NhsOrgUnit(models.Model):
    """Extend Org Unit to trigger job plan recomputes when management changes."""
    _inherit = 'nhs.org.unit'

    def write(self, vals):
        res = super().write(vals)
        if 'manager_id' in vals or 'parent_id' in vals:
            plans = self.env['nhs.job.plan'].search([('org_unit_id', 'child_of', self.ids)])
            if plans:
                plans._compute_manager_ids()
        return res
