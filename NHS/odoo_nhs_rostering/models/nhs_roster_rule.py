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
from odoo import fields, models
from odoo.exceptions import ValidationError

RULE_SEVERITIES = [
    ('hard', 'Hard (Blocks)'),
    ('soft', 'Soft (Warns)'),
]

ACTIVE_STATES = ('assigned', 'published', 'worked', 'changed')


class NhsRosterRule(models.Model):
    """A configurable rule the engine checks every assignment against.
    Statutory defaults are shipped as editable data (data/nhs_roster_rule_data.xml) -
    organisations adjust limits/severities to local policy. See each rule's
    description for what its limit_value / limit_value_2 mean."""
    _name = 'nhs.roster.rule'
    _description = 'Roster Rule'
    _order = 'sequence, code'

    code = fields.Char(string='Code', required=True, index=True,
                        help="Stable code the engine dispatches on, e.g. WTR_AVG_48.")
    name = fields.Char(string='Name', required=True, help="Name")
    severity = fields.Selection(
        RULE_SEVERITIES, string='Severity', required=True, default='hard',
        help="Hard: blocks the assignment outright. Soft: allowed, but opens a"
             " logged violation an approver can resolve or justify.")
    sequence = fields.Integer(string='Sequence', default=10, help="Sequence")
    active = fields.Boolean(string='Active', default=True, help="Active")
    company_id = fields.Many2one(
        'res.company', string='Company', help="Leave blank to apply to every company.")
    limit_value = fields.Float(string='Limit', help="Primary numeric limit - meaning depends"
                                " on the rule, see its description.")
    limit_value_2 = fields.Float(string='Secondary Limit', help="Secondary Limit")
    description = fields.Text(string='Description', help="Description")

    _code_company_uniq = models.Constraint(
        'UNIQUE(code, company_id)',
        'A rule with this code already exists for this company!'
    )


class NhsRosterRuleEngine(models.AbstractModel):
    """Service model: evaluates one nhs.duty.assignment against every active
    rule, raising on hard failures (interactive path) and keeping
    nhs.rule.violation records in sync for both severities (recompute path)."""
    _name = 'nhs.roster.rule.engine'
    _description = 'Roster Rules Engine (service)'


    def _active_rules(self, company):
        """ Method for active rules """
        return self.env['nhs.roster.rule'].search([
            ('active', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', company.id),
        ])

    def _assignments_for_member(self, member, date_from, date_to, exclude=None):
        """ Method for assignments for member """
        domain = [
            ('member_id', '=', member.id),
            ('duty_date', '>=', date_from),
            ('duty_date', '<=', date_to),
            ('state', 'not in', ('cancelled', 'dna')),
        ]
        assignments = self.env['nhs.duty.assignment'].search(domain)
        if exclude:
            assignments -= exclude
        return assignments

    def _bank_member(self, member):
        """ Method for bank member """
        if 'nhs.bank.member' not in self.env:
            return False
        return self.env['nhs.bank.member'].sudo().search(
            [('workforce_member_id', '=', member.id)], limit=1)

    def _bank_hours(self, member, date_from, date_to):
        """Best-effort, guarded lookup of Staff Bank hours for `member` in the
        window - 0.0 whenever the Staff Bank module isn't installed, the
        member isn't linked to a bank member, or its booking shape differs
        from what's expected here."""
        bank_member = self._bank_member(member)
        if not bank_member:
            return 0.0
        total = 0.0
        for booking in getattr(bank_member, 'booking_ids', bank_member.browse()):
            if getattr(booking, 'state', '') not in ('booked', 'worked'):
                continue
            start = getattr(booking, 'shift_start', False)
            end = getattr(booking, 'shift_end', False)
            if not start or not end:
                continue
            booking_date = fields.Date.to_date(start)
            if not (date_from <= booking_date <= date_to):
                continue
            total += (end - start).total_seconds() / 3600.0
        return total

    def _bank_overlaps(self, member, start, end):
        """ Method for bank overlaps """
        bank_member = self._bank_member(member)
        if not bank_member:
            return False
        for booking in getattr(bank_member, 'booking_ids', bank_member.browse()):
            if getattr(booking, 'state', '') not in ('booked', 'worked'):
                continue
            bstart = getattr(booking, 'shift_start', False)
            bend = getattr(booking, 'shift_end', False)
            if bstart and bend and bstart < end and start < bend:
                return True
        return False


    def evaluate(self, assignment):
        """Evaluate every active rule for `assignment` (already written to
        the database, reflecting its current member/duty). Returns a list of
        {rule, passed, message} dicts - no side effects."""
        assignment.ensure_one()
        company = assignment.company_id or self.env.company
        rules = self._active_rules(company)
        evaluators = {
            'WTR_AVG_48': self._eval_wtr_avg_48,
            'REST_11H': self._eval_rest_11h,
            'WEEKLY_REST': self._eval_weekly_rest,
            'MAX_CONSEC_DAYS': self._eval_max_consecutive_days,
            'MAX_CONSEC_NIGHTS': self._eval_max_consecutive_nights,
            'CONTRACT_HOURS': self._eval_contract_hours,
            'SKILL_MIX': self._eval_skill_mix,
            'COMPLIANCE_GATE': self._eval_compliance_gate,
            'DOUBLE_BOOK': self._eval_double_book,
            'LEAVE_CONFLICT': self._eval_leave_conflict,
        }
        results = []
        for rule in rules:
            evaluator = evaluators.get(rule.code)
            if not evaluator:
                continue
            passed, message = evaluator(rule, assignment)
            results.append({'rule': rule, 'passed': passed, 'message': message})
        return results

    def evaluate_and_apply(self, assignment, raise_on_hard=True):
        """Evaluate `assignment`, then apply the result: raise on any open
        hard failure when `raise_on_hard` (the interactive create/write
        path); always keep nhs.rule.violation open/resolved in step with
        the outcome, for both severities (the bulk recompute path relies on
        this to surface hard violations too, without blocking)."""
        results = self.evaluate(assignment)
        hard_failures = [r for r in results if not r['passed'] and r['rule'].severity == 'hard']
        if hard_failures and raise_on_hard:
            raise ValidationError('\n'.join(
                '%s: %s' % (r['rule'].name, r['message']) for r in hard_failures))
        Violation = self.env['nhs.rule.violation']
        for r in results:
            existing = Violation.search([
                ('rule_id', '=', r['rule'].id), ('member_id', '=', assignment.member_id.id),
                ('duty_id', '=', assignment.duty_id.id), ('state', '=', 'open'),
            ], limit=1)
            if not r['passed'] and not existing:
                Violation.create({
                    'rule_id': r['rule'].id,
                    'member_id': assignment.member_id.id,
                    'duty_id': assignment.duty_id.id,
                    'period_id': assignment.duty_id.period_id.id,
                    'severity': r['rule'].severity,
                    'message': r['message'],
                    'state': 'open',
                })
            elif r['passed'] and existing:
                existing.write({'state': 'resolved', 'resolved_at': fields.Datetime.now()})
        return results


    def _eval_wtr_avg_48(self, rule, assignment):
        """ Method for eval wtr avg 48 """
        member, duty = assignment.member_id, assignment.duty_id
        weeks = (duty.company_id or self.env.company).nhs_roster_reference_period_weeks or 17
        date_to = duty.duty_date
        date_from = date_to - timedelta(days=weeks * 7 - 1)
        assignments = self._assignments_for_member(member, date_from, date_to)
        hours = sum(assignments.mapped('paid_hours')) + self._bank_hours(member, date_from, date_to)
        avg = hours / weeks if weeks else 0.0
        limit = rule.limit_value or 48.0
        if avg > limit:
            return False, ('Average weekly hours over the last %d weeks would be %.1f'
                            ' (limit %.1f).') % (weeks, avg, limit)
        return True, ''

    def _eval_rest_11h(self, rule, assignment):
        """ Method for eval rest 11h """
        duty = assignment.duty_id
        member = assignment.member_id
        start, end = duty.get_datetime_bounds()
        window_from = duty.duty_date - timedelta(days=2)
        window_to = duty.duty_date + timedelta(days=2)
        others = self._assignments_for_member(member, window_from, window_to, exclude=assignment)
        limit = rule.limit_value or 11.0
        for other in others:
            o_start, o_end = other.duty_id.get_datetime_bounds()
            if o_end <= start:
                gap = (start - o_end).total_seconds() / 3600.0
            elif end <= o_start:
                gap = (o_start - end).total_seconds() / 3600.0
            else:
                return False, 'Overlaps another duty (%s).' % other.duty_id.display_name
            if gap < limit:
                return False, ('Only %.1fh rest before/after %s (minimum %.1fh).') % (
                    gap, other.duty_id.display_name, limit)
        return True, ''

    def _eval_weekly_rest(self, rule, assignment):
        """ Method for eval weekly rest """
        duty = assignment.duty_id
        member = assignment.member_id
        date_from = duty.duty_date - timedelta(days=6)
        date_to = duty.duty_date
        assignments = self._assignments_for_member(member, date_from, date_to)
        bounds = sorted((a.duty_id.get_datetime_bounds() for a in assignments), key=lambda b: b[0])
        limit = rule.limit_value or 24.0
        if len(bounds) < 2:
            # 0 or 1 duty in the trailing 7 days: nothing to compare, so there is
            # necessarily an unbroken rest period around it - trivially passes.
            return True, ''
        max_gap = 0.0
        for i in range(1, len(bounds)):
            gap = (bounds[i][0] - bounds[i - 1][1]).total_seconds() / 3600.0
            max_gap = max(max_gap, gap)
        if max_gap < limit:
            return False, ('No unbroken rest period of at least %.0fh found in the trailing'
                            ' 7 days (longest break %.1fh).') % (limit, max_gap)
        return True, ''

    def _consecutive_run(self, member, center_date, only_nights=False, exclude=None):
        """ Method for consecutive run """
        window_from = center_date - timedelta(days=21)
        window_to = center_date + timedelta(days=21)
        assignments = self._assignments_for_member(member, window_from, window_to, exclude=exclude)
        if only_nights:
            assignments = assignments.filtered(lambda a: a.shift_type_id.is_night)
        dates = set(assignments.mapped('duty_date'))
        dates.add(center_date)
        run = 1
        cursor = center_date - timedelta(days=1)
        while cursor in dates:
            run += 1
            cursor -= timedelta(days=1)
        cursor = center_date + timedelta(days=1)
        while cursor in dates:
            run += 1
            cursor += timedelta(days=1)
        return run

    def _eval_max_consecutive_days(self, rule, assignment):
        """ Method for eval max consecutive days """
        member, duty = assignment.member_id, assignment.duty_id
        limit = member.roster_max_consecutive_days_override or rule.limit_value or 7
        run = self._consecutive_run(member, duty.duty_date)
        if run > limit:
            return False, 'Would be %d consecutive working days (limit %d).' % (run, limit)
        return True, ''

    def _eval_max_consecutive_nights(self, rule, assignment):
        """ Method for eval max consecutive nights """
        member, duty = assignment.member_id, assignment.duty_id
        if not duty.shift_type_id.is_night:
            return True, ''
        limit = member.roster_max_consecutive_nights_override or rule.limit_value or 4
        run = self._consecutive_run(member, duty.duty_date, only_nights=True)
        if run > limit:
            return False, 'Would be %d consecutive nights (limit %d).' % (run, limit)
        return True, ''

    def _eval_contract_hours(self, rule, assignment):
        """ Method for eval contract hours """
        member = assignment.member_id
        period = assignment.duty_id.period_id
        if not member.contracted_weekly_hours or not period.date_start:
            return True, ''
        period_days = (period.date_end - period.date_start).days + 1
        expected = member.contracted_weekly_hours * (period_days / 7.0)
        assignments = self._assignments_for_member(member, period.date_start, period.date_end)
        actual = sum(assignments.mapped('paid_hours'))
        tolerance = rule.limit_value or 0.0
        diff = actual - expected
        if abs(diff) > tolerance:
            position = 'over' if diff > 0 else 'under'
            return False, ('%.1fh %s contracted hours for this period (contracted %.1fh,'
                            ' assigned %.1fh).') % (abs(diff), position, expected, actual)
        return True, ''

    def _eval_skill_mix(self, rule, assignment):
        """ Method for eval skill mix """
        member, duty = assignment.member_id, assignment.duty_id
        missing = duty.required_skill_ids - member.roster_skill_ids
        if missing:
            return False, 'Missing required skill(s): %s.' % ', '.join(missing.mapped('name'))
        if duty.required_band_id and member.band_id and duty.required_band_id != member.band_id:
            return False, 'Band mismatch (needs %s, member is %s).' % (
                duty.required_band_id.name, member.band_id.name)
        return True, ''

    def _eval_compliance_gate(self, rule, assignment):
        """ Method for eval compliance gate """
        member = assignment.member_id
        if not member.is_training_compliant():
            return False, 'Mandatory training or professional registration is not compliant.'
        return True, ''

    def _eval_double_book(self, rule, assignment):
        """ Method for eval double book """
        member, duty = assignment.member_id, assignment.duty_id
        start, end = duty.get_datetime_bounds()
        others = self._assignments_for_member(
            member, duty.duty_date - timedelta(days=1), duty.duty_date + timedelta(days=1),
            exclude=assignment)
        for other in others:
            o_start, o_end = other.duty_id.get_datetime_bounds()
            if o_start < end and start < o_end:
                return False, 'Overlaps another duty (%s).' % other.duty_id.display_name
        if self._bank_overlaps(member, start, end):
            return False, 'Overlaps a Staff Bank booking.'
        return True, ''

    def _eval_leave_conflict(self, rule, assignment):
        """ Method for eval leave conflict """
        member, duty = assignment.member_id, assignment.duty_id
        approved_leave = self.env['nhs.leave.request'].search([
            ('member_id', '=', member.id), ('state', '=', 'approved'),
            ('date_from', '<=', duty.duty_date), ('date_to', '>=', duty.duty_date),
        ], limit=1)
        if approved_leave:
            return False, 'Member is on approved leave (%s) on this date.' % approved_leave.leave_type_id.name
        return True, ''
