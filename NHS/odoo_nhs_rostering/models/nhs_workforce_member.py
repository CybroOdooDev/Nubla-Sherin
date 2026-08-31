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


class NhsWorkforceMember(models.Model):
    """Extends the Training workforce member with the rostering data the
    rules engine and grid need: contracted hours/band (surfaced from the
    post for quick access), personal working constraints, held skills,
    secondary units for multi-unit staff, and reverse links to duties/
    leave."""
    _inherit = 'nhs.workforce.member'

    contracted_weekly_hours = fields.Float(
        related='post_id.contracted_hours', store=True, string='Contracted Weekly Hours',
        help="Weekly contracted hours, from the post - the baseline the CONTRACT_HOURS"
             " rule tracks assigned hours against."
    )
    band_id = fields.Many2one(
        'nhs.afc.band', related='post_id.band_id', store=True, string='Band',
        help="Agenda for Change band, from the post - used for demand/skill-mix matching."
    )
    roster_skill_ids = fields.Many2many(
        'nhs.roster.skill', string='Skills',
        help="Competencies this member holds, matched against demand-line skill"
             " requirements (e.g. IV-competent) by the SKILL_MIX rule."
    )
    roster_fixed_weekday_ids = fields.Many2many(
        'nhs.roster.weekday', string='Fixed Working Days',
        help="If set, this member only works these days of the week - a fixed"
             " working-day agreement the roster grid and rules engine respect."
    )
    roster_no_nights = fields.Boolean(
        string='No Nights',
        help="Personal constraint: this member cannot be assigned night duties."
    )
    roster_max_consecutive_days_override = fields.Integer(
        string='Max Consecutive Days (Override)',
        help="Overrides the MAX_CONSEC_DAYS rule limit for this member specifically."
             " 0 = use the rule's standard limit."
    )
    roster_max_consecutive_nights_override = fields.Integer(
        string='Max Consecutive Nights (Override)',
        help="Overrides the MAX_CONSEC_NIGHTS rule limit for this member specifically."
             " 0 = use the rule's standard limit."
    )
    roster_part_time_note = fields.Char(
        string='Part-Time / Flexible Pattern',
        help="Free-text note on a part-time or flexible-working pattern the roster"
             " manager should respect when building duties (e.g. '0.6 WTE, Mon/Tue/Thu')."
    )
    secondary_roster_unit_ids = fields.Many2many(
        'nhs.roster.unit', 'nhs_roster_unit_member_rel', 'member_id', 'roster_unit_id',
        string='Also Rosterable In',
        help="Additional rostered units (beyond their home unit, from their post) this"
             " member can be assigned duties in - for multi-unit staff. The rules engine"
             " checks across all of a member's duties regardless of unit, so no"
             " double-booking is possible between units either."
    )
    duty_assignment_ids = fields.One2many(
        'nhs.duty.assignment', 'member_id', string='Duty Assignments',
        help="Duty Assignments")
    duty_assignment_count = fields.Integer(
        string='Duty Count', compute='_compute_duty_assignment_count', help="Duty Count")
    leave_request_ids = fields.One2many(
        'nhs.leave.request', 'member_id', string='Leave Requests',
        help="Leave Requests")
    leave_entitlement_ids = fields.One2many(
        'nhs.leave.entitlement', 'member_id', string='Leave Entitlements',
        help="Leave Entitlements")

    def _compute_duty_assignment_count(self):
        """ Method for compute duty assignment count """
        for member in self:
            member.duty_assignment_count = len(member.duty_assignment_ids)

    def action_view_duty_assignments(self):
        """ Method for action view duty assignments """
        self.ensure_one()
        return {
            'name': 'Duty Assignments',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.duty.assignment',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }
