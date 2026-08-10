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


class ResCompany(models.Model):
    _inherit = 'res.company'

    nhs_full_time_hours_basis = fields.Float(
        string='Full-Time Hours Basis',
        default=37.5,
        digits=(16, 2),
        help="Weekly hours that count as 1.0 FTE (NHS standard is 37.5)."
             " Drives the FTE math used across the establishment register."
    )
    nhs_on_cost_factor = fields.Float(
        string='On-Cost Factor',
        default=1.0,
        digits=(16, 3),
        help="Multiplier applied to indicative salary to approximate total employment"
             " cost (employer NI, pension, etc). 1.0 = no on-costs added; e.g. 1.2 adds 20%."
    )
    nhs_change_control_required = fields.Boolean(
        string='Require Establishment Change Control',
        default=True,
        help="When enabled, changes to a post's funded FTE, band or team must be raised"
             " as an Establishment Change Request rather than edited directly."
    )
    nhs_change_control_single_stage = fields.Boolean(
        string='Single-Stage Approval',
        default=False,
        help="When enabled, workforce approval alone is sufficient to apply a change"
             " (finance approval is skipped) — suited to smaller providers."
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nhs_full_time_hours_basis = fields.Float(
        related='company_id.nhs_full_time_hours_basis', readonly=False)
    nhs_on_cost_factor = fields.Float(
        related='company_id.nhs_on_cost_factor', readonly=False)
    nhs_change_control_required = fields.Boolean(
        related='company_id.nhs_change_control_required', readonly=False)
    nhs_change_control_single_stage = fields.Boolean(
        related='company_id.nhs_change_control_single_stage', readonly=False)
