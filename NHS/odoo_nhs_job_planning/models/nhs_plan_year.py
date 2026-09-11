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
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

YEAR_STATES = [
    ('draft', 'Draft'),
    ('open', 'Open'),
    ('closed', 'Closed'),
]

COMPLETE_STATES = ('signed', 'revised')
OPEN_ENDED_STATES = ('proposed', 'in_discussion')
PA_BALANCE_TOLERANCE = 0.5


class NhsPlanYear(models.Model):
    """A job-planning year: the annual cycle every consultant/SAS job plan is
    raised against. One year is normally 'open' at a time per company."""
    _name = 'nhs.plan.year'
    _description = 'NHS Job Planning Year'
    _order = 'date_start desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="Display, e.g. '2026/27', derived from the year's start/end dates."
    )
    date_start = fields.Date(
        string='Start Date',
        required=True,
        help="Plan-year start date."
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        help="Plan-year end date."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning company."
    )
    state = fields.Selection(
        YEAR_STATES,
        string='Status',
        required=True,
        default='draft',
        help="Draft = not yet in use; Open = job plans may be created/rolled over into"
             " it; Closed = the year is finished, orphaned incomplete plans are marked"
             " superseded."
    )
    job_plan_ids = fields.One2many(
        'nhs.job.plan',
        'plan_year_id',
        string='Job Plans',
        help="Job plans raised against this year."
    )
    job_plan_count = fields.Integer(
        string='Job Plan Count',
        compute='_compute_job_plan_count',
        help="Number of job plans raised against this year."
    )
    completeness_pct = fields.Float(
        string='Completeness (%)',
        compute='_compute_completeness',
        store=True,
        digits=(16, 2),
        help="Signed/revised job plans as a percentage of active medical posts -"
             " the board completeness metric."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    _date_range_uniq = models.Constraint(
        'UNIQUE(date_start, company_id)',
        'A plan year already starts on this date for this company!'
    )

    @api.depends('date_start', 'date_end')
    def _compute_name(self):
        """Build the 'YYYY/YY' display name from the start/end dates."""
        for year in self:
            if year.date_start and year.date_end:
                year.name = '%s/%s' % (year.date_start.year, str(year.date_end.year)[-2:])
            else:
                year.name = 'New Plan Year'

    def _compute_job_plan_count(self):
        """Count job plans raised against each year."""
        data = self.env['nhs.job.plan']._read_group(
            [('plan_year_id', 'in', self.ids)], ['plan_year_id'], ['__count'])
        counts = {year.id: count for year, count in data}
        for year in self:
            year.job_plan_count = counts.get(year.id, 0)

    @api.depends('job_plan_ids.state', 'job_plan_ids.post_id')
    def _compute_completeness(self):
        """Signed plans as a % of the company's active medical posts. Checks
        each post's CURRENT job plan only (not "any plan this year that ever
        reached signed/revised") - a post mid-revision has its old plan
        flip to 'revised' the instant a new, unsigned draft is created for
        it, so counting 'revised' here would keep reporting a post complete
        throughout its revision, out of step with Gaps (which correctly
        flags it via current_job_plan_id - see nhs_establishment_post.py)."""
        Post = self.env['nhs.establishment.post']
        for year in self:
            posts = Post.search([
                ('is_medical', '=', True),
                ('status', '=', 'active'),
                ('company_id', '=', year.company_id.id),
            ])
            if not posts:
                year.completeness_pct = 0.0
                continue
            signed_count = len(posts.filtered(
                lambda p: p.current_job_plan_id.id in year.job_plan_ids.ids
                and p.current_job_plan_id.state == 'signed'))
            year.completeness_pct = round(signed_count / len(posts) * 100, 2)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """The end date must fall after the start date, and the year must
        span roughly a full 12 months."""
        MIN_SPAN_DAYS = 300
        for year in self:
            if not (year.date_start and year.date_end):
                continue
            if year.date_end <= year.date_start:
                raise ValidationError('The plan year end date must be after its start date!')
            span = (year.date_end - year.date_start).days
            if span < MIN_SPAN_DAYS:
                raise ValidationError(
                    'The plan year must span approximately 12 months (at least'
                    ' %d days). "%s" to "%s" is only %d days.' % (
                        MIN_SPAN_DAYS, year.date_start, year.date_end, span))

    def action_open(self):
        """Open the year so job plans can be created/rolled over into it."""
        self.write({'state': 'open'})

    def action_close(self):
        """Close the year: block while any plan is still proposed/in discussion
        (an unresolved negotiation should not be allowed to silently expire),
        then relabel any surviving draft/agreed plan as superseded so it is
        excluded from 'current' plan queries while its full history is kept."""
        for year in self:
            unresolved = year.job_plan_ids.filtered(
                lambda p: p.state in OPEN_ENDED_STATES)
            if unresolved:
                raise UserError(
                    "Cannot close %s: %d job plan(s) are still proposed or in"
                    " discussion. Resolve them (agree, sign, or reset to draft)"
                    " before closing the year." % (year.name, len(unresolved)))
            orphaned = year.job_plan_ids.filtered(
                lambda p: p.state not in COMPLETE_STATES + ('superseded',))
            orphaned.write({'state': 'superseded'})
        self.write({'state': 'closed'})

    def action_view_job_plans(self):
        """Open the job plans raised against this plan year."""
        self.ensure_one()
        return {
            'name': 'Job Plans',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.job.plan',
            'view_mode': 'list,form',
            'domain': [('plan_year_id', '=', self.id)],
            'context': {'default_plan_year_id': self.id},
        }

    @api.model
    def get_capacity_dashboard_metrics(self, year_id=None):
        """Aggregate the figures behind the Capacity & Completeness dashboard:
        the selected (or, by default, the current open) plan year's
        completeness/gaps, unsigned and stalled plan counts, per-directorate
        completeness/capacity/on-call breakdowns, upcoming review-due plans,
        PA balance, a cross-year completeness trend and recent plan
        activity. Read-only, called from the dashboard client action."""
        company = self.env.company
        if year_id:
            year = self.browse(year_id).exists().filtered(lambda y: y.company_id == company)
        else:
            year = self.env['nhs.plan.year']
        if not year:
            year = self.search([
                ('company_id', '=', company.id), ('state', '=', 'open'),
            ], limit=1, order='date_start desc')
        if not year:
            year = self.search([('company_id', '=', company.id)], limit=1, order='date_start desc')
        year_options = self.search([('company_id', '=', company.id)], order='date_start desc')

        Post = self.env['nhs.establishment.post']
        posts = Post.search([
            ('is_medical', '=', True), ('status', '=', 'active'), ('company_id', '=', company.id),
        ])
        plans = year.job_plan_ids if year else self.env['nhs.job.plan']
        signed_posts = posts.filtered(
            lambda p: p.current_job_plan_id.id in plans.ids and p.current_job_plan_id.state == 'signed')
        gap_posts = posts - signed_posts
        unsigned = plans.filtered(lambda p: p.state not in COMPLETE_STATES + ('superseded',))
        stalled = plans.filtered(lambda p: p.state in OPEN_ENDED_STATES)
        live_plans = plans.filtered(lambda p: p.state != 'superseded')

        by_unit = {}
        for post in posts:
            unit = post.org_unit_id
            row = by_unit.setdefault(unit.id, {
                'id': unit.id, 'name': unit.display_name or 'Unassigned', 'total': 0, 'signed': 0,
            })
            row['total'] += 1
            if post in signed_posts:
                row['signed'] += 1
        completeness_rows = []
        for row in by_unit.values():
            row['rate'] = round(row['signed'] / row['total'] * 100, 2) if row['total'] else 0.0
            completeness_rows.append(row)
        completeness_rows.sort(key=lambda r: r['rate'])

        capacity_by_unit = {}
        for plan in signed_posts.mapped('current_job_plan_id'):
            unit = plan.org_unit_id
            row = capacity_by_unit.setdefault(unit.id, {
                'id': unit.id, 'name': unit.display_name or 'Unassigned',
                'doctors': 0, 'contracted_pas': 0.0, 'total_pas': 0.0, 'balance': 0.0,
            })
            row['doctors'] += 1
            row['contracted_pas'] += plan.contracted_pas
            row['total_pas'] += plan.total_pas
            row['balance'] += plan.pa_balance
        capacity_rows = sorted(capacity_by_unit.values(), key=lambda r: r['name'])
        today = fields.Date.context_today(self)
        due_soon_horizon = today + relativedelta(days=60)
        reviewable = plans.filtered(lambda p: p.state in COMPLETE_STATES and p.review_due_date)
        review_overdue = reviewable.filtered(lambda p: p.review_due_date < today)
        review_due_soon = reviewable.filtered(
            lambda p: today <= p.review_due_date <= due_soon_horizon)
        oncall_by_unit = {}
        for plan in live_plans:
            unit = plan.org_unit_id
            row = oncall_by_unit.setdefault(unit.id, {
                'id': unit.id, 'name': unit.display_name or 'Unassigned', 'total': 0, 'covered': 0,
            })
            row['total'] += 1
            if plan.oncall_profile_id:
                row['covered'] += 1
        oncall_rows = []
        for row in oncall_by_unit.values():
            row['rate'] = round(row['covered'] / row['total'] * 100, 2) if row['total'] else 0.0
            oncall_rows.append(row)
        oncall_rows.sort(key=lambda r: r['rate'])
        pa_over = live_plans.filtered(lambda p: p.pa_balance > PA_BALANCE_TOLERANCE)
        pa_under = live_plans.filtered(lambda p: p.pa_balance < -PA_BALANCE_TOLERANCE)
        completeness_trend = [
            {'id': y.id, 'name': y.name, 'completeness_pct': y.completeness_pct}
            for y in year_options.sorted('date_start')
        ]
        recent_plans = self.env['nhs.job.plan'].search([
            ('company_id', '=', company.id),
        ], order='write_date desc', limit=8)
        recent_activity = [{
            'id': p.id, 'reference': p.reference, 'doctor_name': p.doctor_name,
            'state': p.state, 'write_date': fields.Datetime.to_string(p.write_date),
        } for p in recent_plans]

        return {
            'year_id': year.id if year else False,
            'year_name': year.name if year else 'No Plan Year',
            'year_options': [{'id': y.id, 'name': y.name, 'state': y.state} for y in year_options],
            'completeness_pct': year.completeness_pct if year else 0.0,
            'post_count': len(posts),
            'signed_count': len(signed_posts),
            'gap_count': len(gap_posts),
            'unsigned_count': len(unsigned),
            'stalled_count': len(stalled),
            'weakest_directorates': completeness_rows[:5],
            'capacity_rows': capacity_rows,
            'review_overdue_count': len(review_overdue),
            'review_due_soon_count': len(review_due_soon),
            'oncall_rows': oncall_rows[:5],
            'pa_over_count': len(pa_over),
            'pa_under_count': len(pa_under),
            'completeness_trend': completeness_trend,
            'recent_activity': recent_activity,
        }

    @api.model
    def _cron_auto_create_next_year(self):
        """Scheduled action: create next year's draft plan year roughly two
        months before the current open year ends, so rollover always has a
        target waiting for it. Idempotent - does nothing once next year
        already exists."""
        today = fields.Date.context_today(self)
        open_years = self.search([('state', '=', 'open')])
        for year in open_years:
            if not year.date_end or (year.date_end - today).days > 60:
                continue
            next_start = year.date_end + relativedelta(days=1)
            target_year = self.search([
                ('date_start', '=', next_start),
                ('company_id', '=', year.company_id.id),
            ], limit=1)
            if not target_year:
                target_year = self.create({
                    'date_start': next_start,
                    'date_end': next_start + relativedelta(years=1, days=-1),
                    'company_id': year.company_id.id,
                    'state': 'draft',
                })
            
            if year.company_id.nhs_jobplan_auto_rollover:
                self.env['nhs.job.plan']._rollover_plans(year, target_year)
