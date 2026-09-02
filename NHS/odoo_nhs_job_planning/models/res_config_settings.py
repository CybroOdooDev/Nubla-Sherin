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
    """ Company-level Job Planning configuration """
    _inherit = 'res.company'

    nhs_jobplan_pas_per_wte = fields.Float(
        string='PAs per WTE', default=10.0,
        help="Programmed Activities representing 1.0 Whole Time Equivalent - the "
             "divisor used to derive a job plan's FTE from its contracted PAs.")
    nhs_jobplan_pa_length_hours = fields.Float(
        string='PA Length (Hours)', default=4.0,
        help="Nominal hours represented by one Programmed Activity (statutory default "
             "is a 4-hour session).")
    nhs_jobplan_evening_start_hour = fields.Float(
        string='Evening Premium-Time Start Hour', default=18.5,
        help="A weekday timetable line starting at or after this hour (24h, e.g. 18.5 "
             "= 18:30) is flagged as premium time. Weekend lines are always premium time.")
    nhs_jobplan_review_lead_days = fields.Integer(
        string='Annual Review Lead Days', default=60,
        help="Days before a plan year's end date that a job plan's review is due and "
             "reminders begin.")
    nhs_jobplan_stale_discussion_days = fields.Integer(
        string='Stale Discussion Threshold (Days)', default=21,
        help="Days a plan may remain 'Proposed' or 'In Discussion' before it is "
             "flagged as stalled in reminders.")
    nhs_jobplan_auto_rollover = fields.Boolean(
        string='Automatic Annual Rollover', default=False,
        help="When enabled, next year's draft job plans are cloned automatically by "
             "the scheduled action rather than only via the manual rollover wizard.")


class ResConfigSettings(models.TransientModel):
    """ Job Planning settings screen """
    _inherit = 'res.config.settings'

    nhs_jobplan_pas_per_wte = fields.Float(
        related='company_id.nhs_jobplan_pas_per_wte', readonly=False,
        help="Programmed Activities representing 1.0 Whole Time Equivalent.")
    nhs_jobplan_pa_length_hours = fields.Float(
        related='company_id.nhs_jobplan_pa_length_hours', readonly=False,
        help="Nominal hours represented by one Programmed Activity.")
    nhs_jobplan_evening_start_hour = fields.Float(
        related='company_id.nhs_jobplan_evening_start_hour', readonly=False,
        help="Hour after which a weekday session is flagged as premium time.")
    nhs_jobplan_review_lead_days = fields.Integer(
        related='company_id.nhs_jobplan_review_lead_days', readonly=False,
        help="Days before plan-year end that annual review is due.")
    nhs_jobplan_stale_discussion_days = fields.Integer(
        related='company_id.nhs_jobplan_stale_discussion_days', readonly=False,
        help="Days a plan may sit in discussion before being flagged stalled.")
    nhs_jobplan_auto_rollover = fields.Boolean(
        related='company_id.nhs_jobplan_auto_rollover', readonly=False,
        help="Automatically clone next year's draft job plans.")
