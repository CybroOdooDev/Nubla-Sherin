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

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

STATES = [
    ('draft', 'Draft'),
    ('in_progress', 'In Progress'),
    ('checked', 'Checked'),
    ('approved', 'Approved'),
    ('published', 'Published'),
    ('finalised', 'Finalised'),
]


class NhsRosterPeriod(models.Model):
    """A roster for one unit over a date range - the core container. Duties
    are generated from the unit's effective demand template, assignment
    happens against those duties (template roll, manual, or swap), and the
    period moves through draft -> in_progress -> checked -> approved ->
    published -> finalised."""
    _name = 'nhs.roster.period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Roster Period'
    _order = 'date_start desc'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    unit_id = fields.Many2one(
        'nhs.roster.unit', string='Unit', required=True, ondelete='restrict',
        tracking=True, index=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='unit_id.company_id', store=True)
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', required=True, tracking=True)
    state = fields.Selection(
        STATES, string='Status', required=True, default='draft', tracking=True)
    duty_ids = fields.One2many('nhs.duty', 'period_id', string='Duties')
    duty_count = fields.Integer(compute='_compute_counts', store=True)
    assignment_ids = fields.One2many(
        'nhs.duty.assignment', 'period_id', string='Assignments')
    violation_ids = fields.One2many('nhs.rule.violation', 'period_id', string='Violations')
    open_violation_count = fields.Integer(compute='_compute_counts', store=True)
    fill_pct = fields.Float(
        string='Fill %', compute='_compute_fill', store=True, digits=(16, 1))
    required_headcount_total = fields.Integer(compute='_compute_fill', store=True)
    assigned_headcount_total = fields.Integer(compute='_compute_fill', store=True)
    gap_count = fields.Integer(
        string='Open Gaps', compute='_compute_fill', store=True,
        help="Total unfilled headcount across every duty in the period.")
    hard_violation_count = fields.Integer(
        string='Hard Violations', compute='_compute_counts', store=True,
        help="Open violations of hard-severity rules. Blocks publication.")
    published_at = fields.Datetime(string='Published At', tracking=True, copy=False)
    publish_lead_days = fields.Integer(
        string='Publish Lead Time (Days)', compute='_compute_publish_lead_days', store=True,
        help="Days between publication and the period's start date - the six-week"
             " e-Rostering KPI.")
    finalised_at = fields.Datetime(string='Finalised At', tracking=True, copy=False)
    notes = fields.Text(string='Notes')

    @api.depends('unit_id.display_name', 'date_start', 'date_end')
    def _compute_name(self):
        for period in self:
            if period.unit_id and period.date_start and period.date_end:
                period.name = '%s — %s to %s' % (
                    period.unit_id.display_name,
                    fields.Date.to_string(period.date_start),
                    fields.Date.to_string(period.date_end))
            else:
                period.name = 'New Roster Period'

    @api.depends('duty_ids', 'violation_ids.state', 'violation_ids.severity')
    def _compute_counts(self):
        for period in self:
            period.duty_count = len(period.duty_ids)
            open_violations = period.violation_ids.filtered(lambda v: v.state == 'open')
            period.open_violation_count = len(open_violations)
            period.hard_violation_count = len(
                open_violations.filtered(lambda v: v.severity == 'hard'))

    @api.depends('duty_ids.required_headcount', 'duty_ids.assigned_count')
    def _compute_fill(self):
        for period in self:
            required = sum(period.duty_ids.mapped('required_headcount'))
            assigned = sum(min(d.assigned_count, d.required_headcount) for d in period.duty_ids)
            period.required_headcount_total = required
            period.assigned_headcount_total = assigned
            period.fill_pct = (assigned / required * 100.0) if required else 100.0
            period.gap_count = sum(
                max(d.required_headcount - d.assigned_count, 0) for d in period.duty_ids)

    @api.depends('published_at', 'date_start')
    def _compute_publish_lead_days(self):
        for period in self:
            if period.published_at and period.date_start:
                published_date = fields.Datetime.to_datetime(period.published_at).date()
                period.publish_lead_days = (period.date_start - published_date).days
            else:
                period.publish_lead_days = 0

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for period in self:
            if period.date_end < period.date_start:
                raise ValidationError('End date must be on or after the start date.')

    def action_generate_duties(self):
        """Generate duty slots for every date in the period from the unit's
        demand template(s) effective on each date. Idempotent: a duty is
        never created twice for the same date/demand line."""
        Duty = self.env['nhs.duty']
        Template = self.env['nhs.demand.template']
        for period in self:
            existing = {(d.duty_date, d.demand_line_id.id) for d in period.duty_ids}
            a_date = period.date_start
            duty_vals = []
            while a_date <= period.date_end:
                template = Template.template_effective_on(period.unit_id.id, a_date)
                if template:
                    for line in template.lines_for_date(a_date):
                        key = (a_date, line.id)
                        if key in existing:
                            continue
                        duty_vals.append({
                            'period_id': period.id,
                            'duty_date': a_date,
                            'shift_type_id': line.shift_type_id.id,
                            'demand_line_id': line.id,
                            'required_band_id': line.band_id.id,
                            'required_skill_ids': [(6, 0, line.required_skill_ids.ids)],
                            'required_headcount': line.required_headcount,
                        })
                a_date += timedelta(days=1)
            if duty_vals:
                Duty.create(duty_vals)
        return True

    def action_start_build(self):
        for period in self:
            if period.state != 'draft':
                continue
            if not period.duty_ids:
                period.action_generate_duties()
            period.state = 'in_progress'

    def action_recompute_check(self):
        """Recompute rule violations for every assignment in the period and
        move the period to 'checked' so the approver sees a fresh position."""
        for period in self:
            if period.state not in ('in_progress', 'checked'):
                raise UserError(_('Only a roster being built can be checked.'))
            period.assignment_ids.recompute_violations()
            period.state = 'checked'

    def action_approve(self):
        for period in self:
            if period.state != 'checked':
                raise UserError(_('Check the roster (recompute rules) before approving it.'))
            period.state = 'approved'

    def action_publish(self):
        """Publish the period: blocked on any open hard violation. Stamps
        every duty and its assignments as published and notifies staff."""
        for period in self:
            if period.state != 'approved':
                raise UserError(_('Only an approved roster can be published.'))
            if period.hard_violation_count:
                raise UserError(_(
                    'Cannot publish: %d open hard rule violation(s) must be resolved or'
                    ' justified first.') % period.hard_violation_count)
            period.assignment_ids.filtered(lambda a: a.state == 'assigned').write(
                {'state': 'published'})
            period.write({'state': 'published', 'published_at': fields.Datetime.now()})
            period._notify_published()

    def _notify_published(self):
        template = self.env.ref(
            'odoo_nhs_rostering.mail_template_roster_published', raise_if_not_found=False)
        if not template:
            return
        for period in self:
            members = period.assignment_ids.mapped('member_id').filtered('user_id')
            for member in members:
                template.send_mail(period.id, force_send=False, email_values={
                    'email_to': member.email or member.user_id.email,
                })

    def action_finalise(self):
        for period in self:
            if period.state != 'published':
                raise UserError(_('Only a published roster can be finalised.'))
            period.assignment_ids.filtered(
                lambda a: a.state == 'published').write({'state': 'worked'})
            period.write({'state': 'finalised', 'finalised_at': fields.Datetime.now()})

    def action_reset_to_draft(self):
        for period in self:
            if period.state in ('published', 'finalised'):
                raise UserError(_('A published or finalised roster cannot be reset.'))
            period.state = 'draft'

    @api.model
    def get_roster_grid_data(self, period_id):
        """Data for the custom roster-grid client action: members (rows) x
        dates (columns), demand/short per day/shift, and open violations -
        everything the grid needs in one call."""
        period = self.browse(period_id)
        if not period.exists():
            return {}
        members = period.unit_id.member_ids.sorted('name')
        dates = []
        a_date = period.date_start
        while a_date <= period.date_end:
            dates.append(fields.Date.to_string(a_date))
            a_date += timedelta(days=1)
        shift_types = period.unit_id.shift_type_ids
        assignments = period.assignment_ids.filtered(lambda a: a.state != 'cancelled')
        assignment_rows = [{
            'id': a.id, 'member_id': a.member_id.id, 'date': fields.Date.to_string(a.duty_date),
            'shift_type_id': a.shift_type_id.id, 'state': a.state,
            'compliant': a.compliant_at_assignment,
        } for a in assignments]
        demand = {}
        for duty in period.duty_ids:
            d_key = fields.Date.to_string(duty.duty_date)
            demand.setdefault(d_key, {})[duty.shift_type_id.id] = {
                'required': duty.required_headcount, 'assigned': duty.assigned_count,
                'short': max(duty.required_headcount - duty.assigned_count, 0),
                'duty_id': duty.id, 'state': duty.state,
            }
        violations = period.violation_ids.filtered(lambda v: v.state == 'open')
        violation_rows = [{
            'id': v.id, 'member_id': v.member_id.id, 'member_name': v.member_id.name,
            'rule_name': v.rule_id.name, 'severity': v.severity, 'message': v.message,
            'duty_date': fields.Date.to_string(v.duty_id.duty_date) if v.duty_id.duty_date else '',
        } for v in violations]
        return {
            'period': {
                'id': period.id, 'name': period.name,
                'date_start': fields.Date.to_string(period.date_start),
                'date_end': fields.Date.to_string(period.date_end), 'state': period.state,
                'fill_pct': round(period.fill_pct, 1),
                'hard_violation_count': period.hard_violation_count,
            },
            'dates': dates,
            'shift_types': [{
                'id': s.id, 'name': s.name, 'category': s.category, 'color': s.color,
                'code': s.code or s.name[:2],
            } for s in shift_types],
            'members': [{
                'id': m.id, 'name': m.name, 'band': m.band_id.name or '',
                'contracted_hours': m.contracted_weekly_hours,
            } for m in members],
            'assignments': assignment_rows,
            'demand': demand,
            'violations': violation_rows,
        }

    @api.model
    def grid_assign(self, period_id, member_id, a_date, shift_type_id):
        """Assign `member_id` to the duty for (date, shift type) in this
        period - finding or creating an ad-hoc duty slot if the demand-driven
        grid doesn't already have one there. Returns {ok: True} or
        {ok: False, error: <message>} rather than raising, so the grid can
        show the rules-engine message inline instead of crashing the RPC."""
        Duty = self.env['nhs.duty']
        a_date = fields.Date.to_date(a_date)
        duty = Duty.search([
            ('period_id', '=', period_id), ('duty_date', '=', a_date),
            ('shift_type_id', '=', shift_type_id),
        ], limit=1)
        if not duty:
            duty = Duty.create({
                'period_id': period_id, 'duty_date': a_date,
                'shift_type_id': shift_type_id, 'required_headcount': 1,
            })
        existing = duty.assignment_ids.filtered(
            lambda a: a.member_id.id == member_id and a.state != 'cancelled')
        if existing:
            return {'ok': True}
        try:
            self.env['nhs.duty.assignment'].create({'duty_id': duty.id, 'member_id': member_id})
            return {'ok': True}
        except ValidationError as exc:
            return {'ok': False, 'error': str(exc)}

    @api.model
    def grid_unassign(self, period_id, member_id, a_date, shift_type_id):
        """Cancel `member_id`'s assignment for (date, shift type) in this period."""
        a_date = fields.Date.to_date(a_date)
        assignments = self.env['nhs.duty.assignment'].search([
            ('period_id', '=', period_id), ('member_id', '=', member_id),
            ('duty_date', '=', a_date), ('shift_type_id', '=', shift_type_id),
            ('state', '!=', 'cancelled'),
        ])
        assignments.write({'state': 'cancelled'})
        return {'ok': True}

    @api.model
    def get_roster_dashboard_data(self):
        """Aggregated metrics for the client-side e-Rostering Dashboard:
        fill rate, gaps/escalation, rules health and publication lead time."""
        periods = self.search([('state', '!=', 'finalised')])
        total_required = sum(periods.mapped('required_headcount_total')) or 0
        total_assigned = sum(periods.mapped('assigned_headcount_total')) or 0
        fill_rate = (total_assigned / total_required * 100.0) if total_required else 100.0
        Escalation = self.env['nhs.roster.escalation']
        open_escalations = Escalation.search([
            ('state', 'not in', ('bank_filled', 'agency_filled', 'manual_cover', 'cancelled')),
        ])
        bank_filled = Escalation.search_count([('state', '=', 'bank_filled')])
        agency_filled = Escalation.search_count([('state', '=', 'agency_filled')])
        agency_cost = sum(Escalation.search([('state', '=', 'agency_filled')]).mapped('agency_cost'))
        Violation = self.env['nhs.rule.violation']
        open_hard = Violation.search([('state', '=', 'open'), ('severity', '=', 'hard')])
        open_soft = Violation.search([('state', '=', 'open'), ('severity', '=', 'soft')])
        lead_times = periods.filtered('published_at').mapped('publish_lead_days')
        avg_lead_time = (sum(lead_times) / len(lead_times)) if lead_times else 0

        return {
            'fill_rate': round(fill_rate, 1),
            'total_gaps': sum(periods.mapped('gap_count')),
            'open_escalation_count': len(open_escalations),
            'bank_filled_count': bank_filled,
            'agency_filled_count': agency_filled,
            'agency_cost': agency_cost,
            'open_hard_violation_count': len(open_hard),
            'open_soft_violation_count': len(open_soft),
            'avg_lead_time': round(avg_lead_time, 1),
            'periods': [{
                'id': p.id, 'name': p.name, 'fill_pct': round(p.fill_pct, 1),
                'gap_count': p.gap_count, 'hard_violation_count': p.hard_violation_count,
                'state': p.state,
            } for p in periods.sorted('date_start', reverse=True)[:10]],
        }

    @api.model
    def _cron_remind_unpublished(self):
        """Scheduled action: nudge followers on periods approaching their
        start date that are still unpublished - the publication lead-time
        KPI made actionable rather than just reported after the fact."""
        today = fields.Date.context_today(self)
        periods = self.search([
            ('state', 'not in', ('published', 'finalised')),
            ('date_start', '>=', today),
        ])
        for period in periods:
            target = period.company_id.nhs_roster_publish_lead_days_target or 42
            days_left = (period.date_start - today).days
            if days_left <= target and days_left in (target, 14, 7, 3, 1):
                period.message_post(
                    body=_('Reminder: this roster starts in %d day(s) and is not yet'
                           ' published (target lead time %d days).') % (days_left, target))

    def action_view_grid(self):
        """Open the custom roster-grid client action for this period."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'nhs_roster_grid',
            'name': self.name,
            'params': {'period_id': self.id},
        }

    def action_export_worked_hours(self):
        """Export the period's worked-hours dataset as a CSV attachment -
        toward external payroll/ESR processing, not a payroll integration
        itself."""
        self.ensure_one()
        import csv
        import io
        import base64
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Member', 'Reference', 'Date', 'Shift Type', 'Start', 'End',
                          'Paid Hours', 'State'])
        for assignment in self.assignment_ids.sorted(lambda a: (a.duty_date, a.member_id.name)):
            writer.writerow([
                assignment.member_id.name, assignment.member_id.reference,
                assignment.duty_date, assignment.shift_type_id.name,
                assignment.actual_start or '', assignment.actual_end or '',
                '%.2f' % assignment.paid_hours, assignment.state,
            ])
        attachment = self.env['ir.attachment'].create({
            'name': 'worked_hours_%s.csv' % (self.id,),
            'type': 'binary',
            'datas': base64.b64encode(buffer.getvalue().encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'text/csv',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
