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
    """Company-level settings for NHS e-Rostering: the WTR reference period,
    publication lead-time target and default escalation/leave-capacity
    behaviour. Rule limits and severities (including the compliance gate's)
    live on nhs.roster.rule itself - editable reference data, per unit-level
    policy, rather than a single company toggle."""
    _inherit = 'res.company'

    nhs_roster_reference_period_weeks = fields.Integer(
        string='WTR Reference Period (Weeks)',
        default=17,
        help="Reference period, in weeks, over which the 48-hour average working week"
             " is assessed (Working Time Regulations 1998 statutory default: 17 weeks)."
             " Verify the current statutory value before relying on this default."
    )
    nhs_roster_publish_lead_days_target = fields.Integer(
        string='Publication Lead-Time Target (Days)',
        default=42,
        help="Target number of days a roster should be published ahead of its period"
             " start - the widely-cited six-week e-Rostering expectation. Used only to"
             " colour the lead-time KPI; publication is never blocked on it."
    )
    nhs_roster_default_leave_capacity_pct = fields.Float(
        string='Default Leave Capacity (%)',
        default=20.0,
        help="Default maximum percentage of a unit's team who may be on approved leave"
             " at the same time, used when a new roster unit is created."
    )
    nhs_roster_default_escalation_lead_days = fields.Integer(
        string='Default Escalation Lead Time (Days)',
        default=14,
        help="Default number of days before a shift that an unfilled duty is"
             " auto-escalated, used when a new roster unit is created."
    )
    nhs_roster_auto_escalate = fields.Boolean(
        string='Auto-Escalate Unfilled Duties',
        default=True,
        help="When on, the scheduled action pushes unfilled duties within a unit's"
             " escalation lead time to the Staff Bank (when installed) automatically."
    )

    def get_default_hours_basis(self):
        """Full-time weekly hours basis to compute FTE/paid-hours ratios against.
        Reuses the Establishment module's company setting rather than duplicating it."""
        self.ensure_one()
        return self.nhs_full_time_hours_basis or 37.5


class ResConfigSettings(models.TransientModel):
    """Exposes the NHS e-Rostering company settings on the Settings screen."""
    _inherit = 'res.config.settings'

    nhs_roster_reference_period_weeks = fields.Integer(
        related='company_id.nhs_roster_reference_period_weeks', readonly=False,
        help="Detailed information about this field")
    nhs_roster_publish_lead_days_target = fields.Integer(
        related='company_id.nhs_roster_publish_lead_days_target', readonly=False,
        help="Detailed information about this field")
    nhs_roster_default_leave_capacity_pct = fields.Float(
        related='company_id.nhs_roster_default_leave_capacity_pct', readonly=False,
        help="Detailed information about this field")
    nhs_roster_default_escalation_lead_days = fields.Integer(
        related='company_id.nhs_roster_default_escalation_lead_days', readonly=False,
        help="Detailed information about this field")
    nhs_roster_auto_escalate = fields.Boolean(
        related='company_id.nhs_roster_auto_escalate', readonly=False,
        help="Detailed information about this field")
