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


class NhsRosterUnit(models.Model):
    """A rostered unit: an Establishment org unit switched on for e-Rostering,
    carrying the unit-level configuration (leave capacity, escalation policy,
    managers) and the team it rosters - everyone whose post sits in this org
    unit, plus anyone rosterable here as a secondary unit."""
    _name = 'nhs.roster.unit'
    _inherit = ['mail.thread']
    _description = 'Rostered Unit'
    _order = 'org_unit_id'
    _rec_name = 'display_name'

    org_unit_id = fields.Many2one(
        'nhs.org.unit', string='Org Unit', required=True, ondelete='restrict',
        index=True, help="The Establishment org unit (ward/department) this rosters."
    )
    display_name = fields.Char(
        string='Name', compute='_compute_display_name', store=True, help="Name")
    company_id = fields.Many2one(
        'res.company', string='Company', related='org_unit_id.company_id',
        store=True, readonly=True, help="Company")
    roster_manager_ids = fields.Many2many(
        'res.users', 'nhs_roster_unit_manager_rel', 'roster_unit_id', 'user_id',
        string='Roster Managers',
        help="Users who can build/approve/publish rosters for this unit. Record"
             " rules scope Roster Manager access to the units listed here."
    )
    leave_capacity_pct = fields.Float(
        string='Leave Capacity (%)',
        default=lambda self: self.env.company.nhs_roster_default_leave_capacity_pct,
        help="Maximum percentage of this unit's team who may be on approved leave"
             " at the same time. Checked when a leave request is approved."
    )
    escalation_lead_days = fields.Integer(
        string='Escalation Lead Time (Days)',
        default=lambda self: self.env.company.nhs_roster_default_escalation_lead_days,
        help="Unfilled duties within this many days of their shift are auto-escalated"
             " (when auto-escalation is on)."
    )
    escalation_auto_push = fields.Boolean(
        string='Auto-Escalate to Bank',
        default=lambda self: self.env.company.nhs_roster_auto_escalate,
        help="Automatically push unfilled duties to the Staff Bank (when installed) as"
             " they enter the escalation lead-time window. Defaults from the company's"
             " Auto-Escalate Unfilled Duties setting; the cron still checks both this"
             " and the company setting before escalating."
    )
    shift_type_ids = fields.One2many(
        'nhs.roster.shift.type', 'roster_unit_id', string='Shift Types', help="Shift Types")
    shift_type_count = fields.Integer(compute='_compute_counts', help="Detailed information about this field")
    rotation_template_ids = fields.One2many(
        'nhs.rotation.template', 'roster_unit_id', string='Rotation Templates', help="Rotation Templates")
    demand_template_ids = fields.One2many(
        'nhs.demand.template', 'roster_unit_id', string='Demand Templates', help="Demand Templates")
    period_ids = fields.One2many(
        'nhs.roster.period', 'unit_id', string='Roster Periods', help="Roster Periods")
    period_count = fields.Integer(compute='_compute_counts', help="Detailed information about this field")
    member_ids = fields.Many2many(
        'nhs.workforce.member', compute='_compute_member_ids', string='Team', help="Team")
    member_count = fields.Integer(compute='_compute_member_ids', help="Detailed information about this field")
    active = fields.Boolean(string='Active', default=True, help="Active")

    _org_unit_uniq = models.Constraint(
        'UNIQUE(org_unit_id)',
        'This org unit already has a rostered unit configured!'
    )

    @api.depends('org_unit_id.complete_name')
    def _compute_display_name(self):
        """ Method for compute display name """
        for unit in self:
            unit.display_name = unit.org_unit_id.complete_name or 'New Rostered Unit'

    def _compute_counts(self):
        """ Method for compute counts """
        for unit in self:
            unit.shift_type_count = len(unit.shift_type_ids)
            unit.period_count = len(unit.period_ids)

    def _compute_member_ids(self):
        """ Method for compute member ids """
        Member = self.env['nhs.workforce.member']
        for unit in self:
            members = Member.search([
                ('org_unit_id', '=', unit.org_unit_id.id), ('is_leaver', '=', False),
            ])
            members |= Member.search([
                ('secondary_roster_unit_ids', 'in', unit.id), ('is_leaver', '=', False),
            ])
            unit.member_ids = members
            unit.member_count = len(members)

    def action_view_team(self):
        """ Method for action view team """
        self.ensure_one()
        return {
            'name': 'Team',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.workforce.member',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.member_ids.ids)],
        }

    def action_view_periods(self):
        """ Method for action view periods """
        self.ensure_one()
        return {
            'name': 'Roster Periods',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.roster.period',
            'view_mode': 'list,form',
            'domain': [('unit_id', '=', self.id)],
            'context': {'default_unit_id': self.id},
        }
