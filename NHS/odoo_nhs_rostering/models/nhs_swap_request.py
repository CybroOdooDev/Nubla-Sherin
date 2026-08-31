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
from odoo.exceptions import UserError, ValidationError

SWAP_STATES = [
    ('draft', 'Draft'),
    ('proposed', 'Proposed'),
    ('accepted_by_target', 'Accepted by Colleague'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled'),
]


class _DryRunRollback(Exception):
    """Internal sentinel: always raised at the end of a dry-run savepoint so
    the simulated writes are rolled back regardless of whether they passed."""


class NhsSwapRequest(models.Model):
    """A member proposes swapping their duty with a colleague's. The rules
    engine validates BOTH resulting assignments (via a rolled-back dry run,
    reusing the exact same evaluator every real assignment goes through)
    before a manager can approve and the swap actually executes."""
    _name = 'nhs.swap.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Duty Swap Request'
    _order = 'create_date desc'

    requester_assignment_id = fields.Many2one(
        'nhs.duty.assignment', string='Requester Duty', required=True, tracking=True, help="Requester Duty")
    target_assignment_id = fields.Many2one(
        'nhs.duty.assignment', string='Colleague Duty', required=True, tracking=True, help="Colleague Duty")
    requester_member_id = fields.Many2one(
        'nhs.workforce.member', related='requester_assignment_id.member_id',
        store=True, string='Requester', help="Requester")
    target_member_id = fields.Many2one(
        'nhs.workforce.member', related='target_assignment_id.member_id',
        store=True, string='Colleague', help="Colleague")
    requester_duty_id = fields.Many2one(
        'nhs.duty', related='requester_assignment_id.duty_id', string='Requester Duty (Hidden)')
    unit_id = fields.Many2one(
        'nhs.roster.unit', related='requester_assignment_id.unit_id', store=True,
        help="Detailed information about this field")
    company_id = fields.Many2one(
        'res.company', related='requester_assignment_id.company_id', store=True,
        help="Detailed information about this field")
    state = fields.Selection(
        SWAP_STATES, string='Status', required=True, default='draft', tracking=True, help="Status")
    rule_check_note = fields.Text(string='Rule Check Result', readonly=True, help="Rule Check Result")
    rule_check_passed = fields.Boolean(string='Rule Check Passed', readonly=True, help="Rule Check Passed")
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, help="Approved By")
    approved_at = fields.Datetime(string='Approved At', readonly=True, help="Approved At")
    notes = fields.Text(string='Notes', help="Notes")
    display_name = fields.Char(compute='_compute_display_name', help="Detailed information about this field")

    @api.depends('requester_member_id.display_name', 'target_member_id.display_name')
    def _compute_display_name(self):
        """ Method for compute display name """
        for swap in self:
            if swap.requester_member_id and swap.target_member_id:
                swap.display_name = 'Swap: %s ⇆ %s' % (
                    swap.requester_member_id.display_name,
                    swap.target_member_id.display_name)
            else:
                swap.display_name = 'New Swap Request'

    @api.constrains('requester_assignment_id', 'target_assignment_id')
    def _check_different_members(self):
        """ Method for check different members """
        for swap in self:
            if swap.requester_assignment_id.member_id == swap.target_assignment_id.member_id:
                raise ValidationError('A swap needs two different members.')

    def action_propose(self):
        """ Method for action propose """
        for swap in self:
            if swap.requester_assignment_id.member_id == swap.target_assignment_id.member_id:
                raise ValidationError('A swap needs two different members.')
            if swap.requester_assignment_id.duty_id == swap.target_assignment_id.duty_id:
                raise ValidationError('You cannot swap assignments for the exact same duty!')
            swap._run_rule_check()
        self.filtered(lambda s: s.state == 'draft').write({'state': 'proposed'})

    def action_accept_by_target(self):
        """ Method for action accept by target """
        for swap in self:
            if swap.state != 'proposed':
                raise UserError(('Only a proposed swap can be accepted.'))
            swap._run_rule_check()
            swap.state = 'accepted_by_target'

    def action_reject(self):
        """ Method for action reject """
        self.write({'state': 'rejected'})

    def action_cancel(self):
        """ Method for action cancel """
        self.filtered(lambda s: s.state not in ('approved',)).write({'state': 'cancelled'})

    def _run_rule_check(self):
        """Simulate the swap inside a savepoint that is always rolled back,
        capturing whether every rule would still pass for both parties.
        Reuses nhs.duty.assignment.write() - and therefore the real rule
        engine - so there is exactly one code path for 'would this
        assignment be valid', not a parallel copy."""
        self.ensure_one()
        if not self.requester_assignment_id or not self.target_assignment_id:
            self.rule_check_passed = False
            self.rule_check_note = ''
            return True
            
        requester_duty_id = self.requester_assignment_id.duty_id.id
        target_duty_id = self.target_assignment_id.duty_id.id
        messages = []
        passed = True
        try:
            with self.env.cr.savepoint():
                self.requester_assignment_id.write({'duty_id': target_duty_id})
                self.target_assignment_id.write({'duty_id': requester_duty_id})
                raise _DryRunRollback()
        except _DryRunRollback:
            pass
        except (ValidationError, UserError) as exc:
            passed = False
            messages.append(str(exc))
        self.rule_check_passed = passed
        self.rule_check_note = '\n'.join(messages) if messages else 'All rules pass for both parties.'
        return passed

    def action_approve(self):
        """ Method for action approve """
        for swap in self:
            if swap.state != 'accepted_by_target':
                raise UserError(('The colleague must accept the swap before it can be approved.'))
            if not swap._run_rule_check():
                raise UserError((
                    'The rules engine would not allow this swap:\n%s') % swap.rule_check_note)
            requester_duty_id = swap.requester_assignment_id.duty_id.id
            target_duty_id = swap.target_assignment_id.duty_id.id
            swap.requester_assignment_id.write({
                'duty_id': target_duty_id, 'change_note': 'Swap %s' % swap.id})
            swap.target_assignment_id.write({
                'duty_id': requester_duty_id, 'change_note': 'Swap %s' % swap.id})
            swap.write({
                'state': 'approved', 'approved_by': self.env.user.id,
                'approved_at': fields.Datetime.now(),
            })
