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
from odoo.exceptions import UserError

VIOLATION_STATES = [
    ('open', 'Open'),
    ('resolved', 'Resolved'),
    ('justified', 'Justified'),
]


class NhsRuleViolation(models.Model):
    """A persisted rule breach: what broke, for whom, on which duty. Hard
    violations only ever appear via the non-blocking bulk recompute path
    (interactive assignment is blocked outright, so none should normally
    persist) - soft ones are the everyday case, approved-with-justification
    by a manager and logged."""
    _name = 'nhs.rule.violation'
    _inherit = ['mail.thread']
    _description = 'Rule Violation'
    _order = 'create_date desc'

    rule_id = fields.Many2one('nhs.roster.rule', string='Rule', required=True, index=True)
    member_id = fields.Many2one(
        'nhs.workforce.member', string='Member', required=True, index=True)
    duty_id = fields.Many2one('nhs.duty', string='Duty', required=True, ondelete='cascade')
    period_id = fields.Many2one(
        'nhs.roster.period', string='Roster Period', required=True, index=True)
    company_id = fields.Many2one(
        'res.company', related='period_id.company_id', store=True)
    severity = fields.Selection(
        [('hard', 'Hard'), ('soft', 'Soft')], string='Severity', required=True)
    message = fields.Text(string='Detail')
    state = fields.Selection(
        VIOLATION_STATES, string='Status', required=True, default='open', tracking=True)
    justification = fields.Text(string='Justification')
    justified_by = fields.Many2one('res.users', string='Justified By', readonly=True)
    justified_at = fields.Datetime(string='Justified At', readonly=True)
    resolved_at = fields.Datetime(string='Resolved At', readonly=True)

    def action_justify(self, justification):
        for violation in self:
            if violation.severity == 'hard':
                raise UserError(
                    'A hard rule violation cannot be justified away - fix the'
                    ' assignment so the rule actually passes.')
            violation.write({
                'state': 'justified',
                'justification': justification,
                'justified_by': self.env.user.id,
                'justified_at': fields.Datetime.now(),
            })

    def action_justify_from_field(self):
        """Justify using whatever is currently typed into the justification
        field - the simple path for the 'Justify' button on the form."""
        for violation in self:
            if not violation.justification:
                raise UserError('Enter a justification first.')
            violation.action_justify(violation.justification)

    def action_resolve(self):
        self.write({'state': 'resolved', 'resolved_at': fields.Datetime.now()})

    def action_reopen(self):
        self.write({'state': 'open', 'resolved_at': False, 'justified_at': False,
                    'justified_by': False, 'justification': False})
