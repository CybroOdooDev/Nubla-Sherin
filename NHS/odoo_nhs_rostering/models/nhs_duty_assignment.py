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

ASSIGNMENT_STATES = [
    ('assigned', 'Assigned'),
    ('published', 'Published'),
    ('worked', 'Worked'),
    ('dna', 'Did Not Attend'),
    ('changed', 'Changed'),
    ('cancelled', 'Cancelled'),
]


class NhsDutyAssignment(models.Model):
    """A person on a duty - the core record the rules engine guards. Every
    create/write runs the full rule evaluation for the member: the
    compliance gate first, then the configured hard/soft rules. A hard
    failure blocks the write outright; a soft failure is allowed and opens
    a logged nhs.rule.violation."""
    _name = 'nhs.duty.assignment'
    _inherit = ['mail.thread']
    _description = 'Duty Assignment'
    _order = 'duty_date, id'



    duty_id = fields.Many2one(
        'nhs.duty', string='Duty', required=True, ondelete='cascade', index=True, help="Duty")
    period_id = fields.Many2one(
        'nhs.roster.period', related='duty_id.period_id', store=True, string='Roster Period',
        help="Roster Period")
    unit_id = fields.Many2one(
        'nhs.roster.unit', related='duty_id.unit_id', store=True, string='Unit', help="Unit")
    eligible_member_ids = fields.Many2many(
        'nhs.workforce.member', compute='_compute_eligible_member_ids',
        help="This duty's unit's team, narrowed to those meeting its Required Band/Skills"
             " - mirrors nhs.duty's own eligible_member_ids so the two Member pickers"
             " (this standalone form, and the one nested under a duty) never disagree.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'duty_id' in vals:
                duty = self.env['nhs.duty'].browse(vals['duty_id'])
                if duty.period_id.state != 'in_progress':
                    from odoo.exceptions import ValidationError
                    raise ValidationError("You can only create assignments when the Roster Period is 'In Progress'.")
        return super().create(vals_list)

    @api.depends('duty_id.eligible_member_ids')
    def _compute_eligible_member_ids(self):
        """ Method for compute eligible member ids """
        for assignment in self:
            assignment.eligible_member_ids = assignment.duty_id.eligible_member_ids
    company_id = fields.Many2one(
        'res.company', related='duty_id.company_id', store=True, help="Detailed information about this field")
    duty_date = fields.Date(related='duty_id.duty_date', store=True, string='Date', help="Date")
    shift_type_id = fields.Many2one(
        'nhs.roster.shift.type', related='duty_id.shift_type_id', store=True,
        string='Shift Type', help="Shift Type")
    member_id = fields.Many2one(
        'nhs.workforce.member', string='Member', required=True, tracking=True, index=True, help="Member")
    state = fields.Selection(
        ASSIGNMENT_STATES, string='Status', required=True, default='assigned', tracking=True, help="Status")
    compliant_at_assignment = fields.Boolean(
        string='Compliant at Assignment', readonly=True,
        help="Snapshot: was the member training/registration compliant at the moment they"
             " were assigned - audit trail, mirrors the Staff Bank pattern.")
    actual_start = fields.Datetime(string='Actual Start', help="Actual Start")
    actual_end = fields.Datetime(string='Actual End', help="Actual End")
    paid_hours = fields.Float(
        string='Paid Hours', compute='_compute_paid_hours', store=True, digits=(16, 2), help="Paid Hours")
    change_note = fields.Char(
        string='Change Reason', help="Reason for a post-publication change (versioned via chatter).")
    display_name = fields.Char(compute='_compute_display_name', help="Detailed information about this field")

    @api.depends('member_id.display_name', 'duty_id.display_name')
    def _compute_display_name(self):
        """ Method for compute display name """
        for assignment in self:
            if assignment.member_id and assignment.duty_id:
                assignment.display_name = '%s on %s' % (
                    assignment.member_id.display_name,
                    assignment.duty_id.display_name)
            else:
                assignment.display_name = 'New Duty Assignment'

    @api.depends('actual_start', 'actual_end', 'shift_type_id.duration_hours')
    def _compute_paid_hours(self):
        """ Method for compute paid hours """
        for assignment in self:
            if assignment.actual_start and assignment.actual_end:
                delta = assignment.actual_end - assignment.actual_start
                assignment.paid_hours = round(delta.total_seconds() / 3600.0, 2)
            else:
                assignment.paid_hours = assignment.shift_type_id.duration_hours

    @api.model_create_multi
    def create(self, vals_list):
        # A hard-rule failure raises from inside _apply_rules() *after* the row
        # already exists in the database. Without a savepoint here, a caller
        # that catches the exception (a bulk wizard, a swap dry run) would
        # leave that half-created row behind - a phantom assignment silently
        # corrupting every rule check that follows in the same transaction.
        # Wrapping the whole call in a savepoint makes "raises => nothing
        # persisted" hold for every caller, not just ones that happen to
        # wrap it themselves.
        """ Method for create """
        with self.env.cr.savepoint():
            assignments = super().create(vals_list)
            assignments._apply_rules(raise_on_hard=True)
        return assignments

    def write(self, vals):
        """ Method for write """
        with self.env.cr.savepoint():
            result = super().write(vals)
            if {'member_id', 'duty_id', 'state', 'actual_start', 'actual_end'} & set(vals):
                self._apply_rules(raise_on_hard=True)
        return result

    def _apply_rules(self, raise_on_hard=True):
        """ Method for apply rules """
        engine = self.env['nhs.roster.rule.engine']
        for assignment in self:
            assignment.compliant_at_assignment = assignment.member_id.is_training_compliant()
            engine.evaluate_and_apply(assignment, raise_on_hard=raise_on_hard)

    def recompute_violations(self):
        """Non-blocking bulk re-check, used by the period's 'Check' action and
        the roster grid's live panel - surfaces both hard and soft open
        violations without raising."""
        self._apply_rules(raise_on_hard=False)

    def action_mark_dna(self):
        """ Method for action mark dna """
        self.write({'state': 'dna'})

    def action_mark_worked(self):
        """ Method for action mark worked """
        self.write({'state': 'worked'})
