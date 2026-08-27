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
from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import ValidationError

# Minimal fixed-date UK bank holiday stub (Good Friday/Easter Monday/movable
# bank holidays are NOT included - a full calendar is a natural roadmap
# enhancement; this v1 checkbox handles the common fixed dates only).
FIXED_UK_BANK_HOLIDAYS = {(1, 1), (12, 25), (12, 26)}


class NhsApplyTemplateWizard(models.TransientModel):
    """Rolls a rotation template across a roster period in one action, for
    the selected team members - the pattern is applied as duty assignments,
    creating ad-hoc duty slots where the demand-generated grid doesn't
    already have one for that date/shift type."""
    _name = 'nhs.apply.template.wizard'
    _description = 'Apply Rotation Template Wizard'

    period_id = fields.Many2one('nhs.roster.period', string='Roster Period', required=True)
    rotation_template_id = fields.Many2one(
        'nhs.rotation.template', string='Rotation Template', required=True,
        domain="[('roster_unit_id', '=', unit_id)]")
    unit_id = fields.Many2one(related='period_id.unit_id', string='Unit')
    member_ids = fields.Many2many(
        'nhs.workforce.member', string='Apply To', required=True,
        domain="[('id', 'in', team_member_ids)]")
    team_member_ids = fields.Many2many(
        'nhs.workforce.member', compute='_compute_team_member_ids')
    start_week = fields.Integer(
        string='Pattern Starts at Week', default=1,
        help="Which week of the template's pattern aligns with the period's start date.")
    skip_bank_holidays = fields.Boolean(
        string='Skip Fixed Bank Holidays', default=True,
        help="Skip 1 Jan, 25 Dec and 26 Dec - a minimal fixed-date set, not a full calendar.")

    def _compute_team_member_ids(self):
        for wizard in self:
            wizard.team_member_ids = wizard.period_id.unit_id.member_ids

    @staticmethod
    def _is_bank_holiday(a_date):
        return (a_date.month, a_date.day) in FIXED_UK_BANK_HOLIDAYS

    def action_apply(self):
        self.ensure_one()
        template = self.rotation_template_id
        weeks = template.weeks or 1
        Duty = self.env['nhs.duty']
        Assignment = self.env['nhs.duty.assignment']
        created, skipped = 0, []
        a_date = self.period_id.date_start
        while a_date <= self.period_id.date_end:
            if self.skip_bank_holidays and self._is_bank_holiday(a_date):
                a_date += timedelta(days=1)
                continue
            days_since_start = (a_date - self.period_id.date_start).days
            week_number = ((self.start_week - 1 + days_since_start // 7) % weeks) + 1
            weekday = str(a_date.weekday())
            line = template.line_ids.filtered(
                lambda l: l.week_number == week_number and l.weekday == weekday)[:1]
            if line and line.shift_type_id:
                shift_type = line.shift_type_id
                duty = Duty.search([
                    ('period_id', '=', self.period_id.id), ('duty_date', '=', a_date),
                    ('shift_type_id', '=', shift_type.id),
                ], limit=1)
                for member in self.member_ids:
                    target = duty
                    if target and target.assignment_ids.filtered(
                            lambda a: a.member_id == member and a.state != 'cancelled'):
                        continue
                    if not target or target.assigned_count >= target.required_headcount:
                        target = Duty.create({
                            'period_id': self.period_id.id, 'duty_date': a_date,
                            'shift_type_id': shift_type.id, 'required_headcount': 1,
                        })
                        if not duty:
                            duty = target
                    try:
                        Assignment.create({'duty_id': target.id, 'member_id': member.id})
                        created += 1
                    except ValidationError as exc:
                        skipped.append('%s on %s: %s' % (member.name, a_date, exc))
            a_date += timedelta(days=1)
        message = _('%d duties assigned.') % created
        if skipped:
            message += _(' %d skipped (rule violations) - see below:\n%s') % (
                len(skipped), '\n'.join(skipped[:20]))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Template Applied'),
                'message': message,
                'type': 'warning' if skipped else 'success',
                'sticky': bool(skipped),
            },
        }
