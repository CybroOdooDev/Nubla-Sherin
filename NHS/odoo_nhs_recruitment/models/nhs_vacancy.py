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
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare

VACANCY_STATES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('workforce_approved', 'Workforce Approved'),
    ('finance_approved', 'Finance Approved'),
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('filled', 'Filled'),
    ('closed', 'Closed'),
    ('withdrawn', 'Withdrawn'),
]


class NhsVacancy(models.Model):
    """A recruitment vacancy against a funded establishment post: a vacancy IS
    an unfilled funded post, and approving it goes through the same
    workforce/finance discipline as the Establishment Register's change
    control, preventing over-establishment and uncontrolled pay-cost growth."""
    _name = 'nhs.vacancy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A recruitment vacancy against a funded establishment post'
    _order = 'create_date desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="Display, e.g. 'Band 5 Staff Nurse — Ward 7 (VAC/2026/0012)'."
    )
    reference = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help="Vacancy reference, sequenced."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    post_id = fields.Many2one(
        'nhs.establishment.post',
        string='Funded Post',
        required=True,
        ondelete='restrict',
        tracking=True,
        domain="[('company_id', '=', company_id), ('status', '=', 'active')]",
        help="The funded post being recruited to. Pulls band/staff group/FTE/unit."
             " Only active (non-frozen) posts are offered."
    )
    org_unit_id = fields.Many2one(
        related='post_id.org_unit_id', string='Team / Department', store=True, readonly=True)
    band_id = fields.Many2one(
        related='post_id.band_id', string='Agenda for Change Band', store=True, readonly=True)
    staff_group_id = fields.Many2one(
        related='post_id.staff_group_id', string='Staff Group', store=True, readonly=True)
    hiring_manager_id = fields.Many2one(
        'res.users',
        string='Hiring Manager',
        default=lambda self: self.env.user,
        tracking=True,
        help="Day-to-day owner of this vacancy; scopes what Recruitment Viewers can see."
    )
    fte = fields.Float(
        string='FTE',
        required=True,
        default=1.0,
        digits=(16, 2),
        help="FTE being recruited (must not exceed the post's vacant FTE)."
    )
    post_fte_display = fields.Char(
        string='Post FTE (Funded / Vacant)',
        compute='_compute_post_fte_display',
        help="Live funded/vacant FTE from the establishment post, shown next to the post"
             " link per the build spec — not a stored field; always reflects the post's"
             " current state, e.g. after an approved Change Request."
    )
    contract_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('fixed_term', 'Fixed Term'),
        ('secondment', 'Secondment'),
    ], string='Contract Type', default='permanent', required=True)
    reason = fields.Selection([
        ('replacement', 'Replacement'),
        ('growth', 'Growth'),
        ('fixed_term_cover', 'Fixed-Term Cover'),
    ], string='Recruitment Reason', default='replacement', required=True)
    person_spec_id = fields.Many2one('nhs.person.spec', string='Person Specification', required=True)
    check_profile_id = fields.Many2one(
        'nhs.check.profile',
        string='Check Profile',
        help="Which pre-employment checks apply to a successful candidate;"
             " defaulted from the post's staff group."
    )
    state = fields.Selection(VACANCY_STATES, string='Status', required=True, default='draft', tracking=True)
    withdrawn_reason = fields.Text(string='Withdrawal Reason')
    advert_text = fields.Html(string='Advert Text')
    advertising_channel_ids = fields.Many2many(
        'nhs.recruitment.channel', string='Advertising Channels')
    open_date = fields.Date(string='Opening Date')
    close_date = fields.Date(string='Closing Date', tracking=True)
    internal_only = fields.Boolean(string='Internal Only')
    anonymised_shortlisting = fields.Boolean(
        string='Anonymised Shortlisting',
        help="Hide candidate-identifying fields during shortlisting scoring, to reduce bias."
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    indicative_cost = fields.Monetary(
        string='Indicative Annual Cost',
        compute='_compute_indicative_cost',
        currency_field='currency_id',
        help="Indicative pay cost for this vacancy's FTE, from the post — shown at approval."
    )
    application_ids = fields.One2many('nhs.application', 'vacancy_id', string='Applications')
    application_count = fields.Integer(string='Application Count', compute='_compute_application_count')
    interview_count = fields.Integer(string='Interviews', compute='_compute_application_count')
    offer_count = fields.Integer(string='Offers', compute='_compute_application_count')
    hired_fte = fields.Float(
        string='Hired FTE',
        compute='_compute_hired_fte',
        store=True,
        digits=(16, 2),
        help="Sum of FTE across applications hired against this vacancy so far."
    )
    days_open = fields.Integer(string='Days Open', compute='_compute_days_open')
    filled_date = fields.Date(string='Filled Date', readonly=True)
    time_to_hire = fields.Integer(
        string='Time to Hire (days)',
        compute='_compute_time_to_hire',
        store=True,
        help="Open → filled days, once filled."
    )
    active = fields.Boolean(string='Active', default=True)

    @api.depends('post_id.funded_fte', 'post_id.vacant_fte')
    def _compute_post_fte_display(self):
        """Non-stored text of the linked post's current funded/vacant FTE —
        the view-only 'post link showing funded/vacant FTE' the spec calls for,
        without adding persisted FTE columns beyond the vacancy's own fte."""
        for vacancy in self:
            post = vacancy.post_id
            if post:
                vacancy.post_fte_display = '%.2f / %.2f' % (post.funded_fte, post.vacant_fte)
            else:
                vacancy.post_fte_display = ''

    @api.depends('post_id.job_title', 'org_unit_id.name', 'reference')
    def _compute_name(self):
        """Builds the display name from the post's job title and org unit,
        with the reference appended once assigned."""
        for vacancy in self:
            title = vacancy.post_id.job_title or ('New Vacancy')
            unit = vacancy.org_unit_id.name
            parts = [p for p in (title, unit) if p]
            label = ' — '.join(parts)
            if vacancy.reference and vacancy.reference != 'New':
                label = f'{label} ({vacancy.reference})'
            vacancy.name = label

    @api.depends('post_id.band_id.indicative_salary', 'post_id.manual_indicative_salary',
                 'post_id.is_medical', 'fte', 'company_id.nhs_on_cost_factor')
    def _compute_indicative_cost(self):
        """Derives indicative annual pay cost from the post's band salary
        (or the manual medical salary for medical posts), scaled by FTE
        and the company's on-cost factor."""
        for vacancy in self:
            post = vacancy.post_id
            on_cost = vacancy.company_id.nhs_on_cost_factor or 1.0
            base_salary = post.manual_indicative_salary if post.is_medical else (
                post.band_id.indicative_salary or 0.0)
            vacancy.indicative_cost = base_salary * vacancy.fte * on_cost

    @api.depends('application_ids.stage', 'application_ids.offer_id.fte')
    def _compute_hired_fte(self):
        """Sums offer FTE across applications that have reached the hired
        stage, to track how much of the vacancy's FTE has been filled."""
        for vacancy in self:
            hired = vacancy.application_ids.filtered(lambda a: a.stage == 'hired')
            vacancy.hired_fte = sum(hired.mapped('offer_id.fte'))

    def _compute_application_count(self):
        """Batches application, interview and offer counts per vacancy via
        read_group, rather than looping searches per record."""
        app_data = self.env['nhs.application']._read_group(
            [('vacancy_id', 'in', self.ids)], ['vacancy_id'], ['__count'])
        app_counts = {vac.id: count for vac, count in app_data}
        interview_data = self.env['nhs.interview']._read_group(
            [('vacancy_id', 'in', self.ids)], ['vacancy_id'], ['__count'])
        interview_counts = {vac.id: count for vac, count in interview_data}
        offer_data = self.env['nhs.offer']._read_group(
            [('vacancy_id', 'in', self.ids)], ['vacancy_id'], ['__count'])
        offer_counts = {vac.id: count for vac, count in offer_data}
        for vacancy in self:
            vacancy.application_count = app_counts.get(vacancy.id, 0)
            vacancy.interview_count = interview_counts.get(vacancy.id, 0)
            vacancy.offer_count = offer_counts.get(vacancy.id, 0)

    @api.depends('state', 'open_date')
    def _compute_days_open(self):
        """Days since opening, for vacancies still open or in progress;
        zero once filled, closed, withdrawn, never opened, or not yet due
        to open (a future Opening Date)."""
        today = fields.Date.context_today(self)
        for vacancy in self:
            if vacancy.state in ('filled', 'closed', 'withdrawn') or not vacancy.open_date:
                vacancy.days_open = 0
            else:
                vacancy.days_open = max(0, (today - vacancy.open_date).days)

    @api.depends('filled_date', 'open_date')
    def _compute_time_to_hire(self):
        """Days elapsed between opening and being filled, once both dates
        are known; zero otherwise."""
        for vacancy in self:
            if vacancy.filled_date and vacancy.open_date:
                vacancy.time_to_hire = (vacancy.filled_date - vacancy.open_date).days
            else:
                vacancy.time_to_hire = 0

    @api.constrains('fte', 'post_id')
    def _check_fte(self):
        """Rejects vacancies with zero or negative FTE, and FTE recruited beyond
        the post's current vacant FTE — per the spec: 'FTE being recruited
        (<= post vacant FTE)'."""
        for vacancy in self:
            if vacancy.fte <= 0:
                raise ValidationError(('Vacancy FTE must be greater than zero.'))
            if vacancy.post_id and float_compare(
                    vacancy.fte, vacancy.post_id.vacant_fte, precision_digits=2) > 0:
                raise ValidationError((
                    "'%s' cannot recruit %.2f FTE: the post '%s' only has %.2f FTE vacant.")
                    % (vacancy.name, vacancy.fte, vacancy.post_id.display_name,
                       vacancy.post_id.vacant_fte))

    @api.constrains('open_date', 'close_date')
    def _check_advert_dates(self):
        """Rejects an Opening or Closing Date set in the past."""
        today = fields.Date.context_today(self)
        for vacancy in self:
            if vacancy.open_date and vacancy.open_date < today:
                raise ValidationError(('Opening Date cannot be in the past.'))
            if vacancy.close_date and vacancy.close_date < today:
                raise ValidationError(('Closing Date cannot be in the past.'))

    @api.onchange('post_id')
    def _onchange_post_id(self):
        """Defaults FTE to the post's vacant capacity (or its funded FTE)
        and, if unset, the check profile to the staff group's default."""
        for vacancy in self:
            if vacancy.post_id:
                post = vacancy.post_id
                vacancy.fte = post.vacant_fte if post.vacant_fte > 0 else (post.funded_fte or 1.0)
                if not vacancy.check_profile_id:
                    vacancy.check_profile_id = self.env['nhs.check.profile'] \
                        ._get_default_for_staff_group(vacancy.post_id.staff_group_id.id)

    @api.model_create_multi
    def create(self, vals_list):
        """Assigns each vacancy the next reference from its sequence unless
        one was already supplied."""
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'nhs.vacancy') or 'New'
        return super().create(vals_list)

    def _check_post_fundable(self):
        """Confirm the post is funded, not frozen, and has vacant capacity available."""
        for vacancy in self:
            post = vacancy.post_id
            if post.funded_fte <= 0:
                raise UserError((
                    "'%s' cannot be approved: the post has no funded FTE.") % vacancy.name)
            if post.is_frozen:
                raise UserError((
                    "'%s' cannot be approved: the post is frozen.") % vacancy.name)
            if post.vacant_fte <= 0:
                raise UserError((
                    "'%s' cannot be approved: the post has no vacant capacity.") % vacancy.name)

    def action_submit(self):
        """Moves a draft vacancy to submitted, then auto-advances past any
        approval steps Settings has disabled."""
        for vacancy in self:
            if vacancy.state != 'draft':
                raise UserError(('Only draft vacancies can be submitted.'))
        self.write({'state': 'submitted'})
        self._auto_advance_approvals()

    def _check_can_approve(self):
        """Approvals (workforce and finance) are a Recruitment Manager
        capability only — enforced here so it holds regardless of how the
        transition is triggered, not just when the view button is used."""
        if not self.env.user.has_group('odoo_nhs_recruitment.group_nhs_recruit_manager'):
            raise AccessError(('Only a Recruitment Manager can approve a vacancy.'))

    def action_workforce_approve(self):
        """Gives workforce sign-off, after re-checking the post is still
        fundable, then auto-advances past a disabled finance approval step."""
        self._check_can_approve()
        for vacancy in self:
            if vacancy.state != 'submitted':
                raise UserError(('Only submitted vacancies can be workforce-approved.'))
            vacancy._check_post_fundable()
        self.write({'state': 'workforce_approved'})
        self._auto_advance_approvals()

    def action_finance_approve(self):
        """Gives finance sign-off, after re-checking the post is still
        fundable."""
        self._check_can_approve()
        for vacancy in self:
            if vacancy.state != 'workforce_approved':
                raise UserError(('Only workforce-approved vacancies can be finance-approved.'))
            vacancy._check_post_fundable()
        self.write({'state': 'finance_approved'})

    def _auto_advance_approvals(self):
        """Skip the workforce/finance approval steps that Settings has switched
        off, so a vacancy only stops for approval clicks it actually requires."""
        for vacancy in self:
            if vacancy.state == 'submitted' and not vacancy.company_id.nhs_recruit_workforce_approval_required:
                vacancy._check_post_fundable()
                vacancy.state = 'workforce_approved'
            if vacancy.state == 'workforce_approved' and not vacancy.company_id.nhs_recruit_finance_approval_required:
                vacancy._check_post_fundable()
                vacancy.state = 'finance_approved'

    def action_open(self):
        """Opens a finance-approved vacancy for advertising, stamping the
        opening date the first time it's opened."""
        today = fields.Date.context_today(self)
        for vacancy in self:
            if vacancy.state != 'finance_approved':
                raise UserError(('Only finance-approved vacancies can be opened.'))
            if not vacancy.open_date:
                vacancy.open_date = today
        self.write({'state': 'open'})

    def action_mark_in_progress(self):
        """Flags an open vacancy as having active candidates in the
        pipeline (e.g. once shortlisting has started)."""
        for vacancy in self:
            if vacancy.state == 'open':
                vacancy.state = 'in_progress'

    def action_mark_filled(self):
        """Called by the onboarding wizard once a hire is confirmed."""
        today = fields.Date.context_today(self)
        self.write({'state': 'filled', 'filled_date': today})

    def _advance_after_hire(self):
        """Called by the onboarding wizard after each hire is confirmed. A
        vacancy's fte can represent more than one hire (e.g. 3.0 FTE across
        3 candidates), so it should only close out once hired_fte reaches
        the vacancy's target fte, not after the first hire."""
        for vacancy in self:
            if float_compare(vacancy.hired_fte, vacancy.fte, precision_digits=2) >= 0:
                vacancy.action_mark_filled()
                vacancy.action_close()

    def action_close(self):
        """Closes the vacancy, ending recruitment activity on it."""
        self.write({'state': 'closed'})

    def action_withdraw(self):
        """Withdraws the vacancy from recruitment; blocked once filled."""
        for vacancy in self:
            if vacancy.state == 'filled':
                raise UserError(('A filled vacancy cannot be withdrawn.'))
        self.write({'state': 'withdrawn'})

    def action_view_applications(self):
        """Opens this vacancy's applications in a dedicated list/kanban view.
        New applications can only be raised once the vacancy is actually
        Open/In Progress — not while it's still draft or awaiting approval."""
        self.ensure_one()
        return {
            'name': ('Applications'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.application',
            'view_mode': 'kanban,list,form',
            'domain': [('vacancy_id', '=', self.id)],
            'context': {
                'default_vacancy_id': self.id,
                'create': self.state in ('open', 'in_progress'),
            },
        }

    def action_view_interviews(self):
        """Opens this vacancy's interviews in a dedicated list view. New
        interviews follow the same Open/In Progress gate as applications."""
        self.ensure_one()
        return {
            'name': ('Interviews'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.interview',
            'view_mode': 'list,form',
            'domain': [('vacancy_id', '=', self.id)],
            'context': {'create': self.state in ('open', 'in_progress')},
        }

    def action_view_offers(self):
        """Opens this vacancy's offers in a dedicated list view. New offers
        follow the same Open/In Progress gate as applications/interviews —
        normally made from an application, but this closes the direct-from-
        vacancy smart-button path too."""
        self.ensure_one()
        return {
            'name': ('Offers'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.offer',
            'view_mode': 'list,form',
            'domain': [('vacancy_id', '=', self.id)],
            'context': {'create': self.state in ('open', 'in_progress')},
        }

    @api.model
    def _cron_check_vacancy_ageing(self, threshold_days=60):
        """Nudge followers on vacancies open beyond the ageing threshold."""
        vacancies = self.search([('state', 'in', ('open', 'in_progress'))])
        for vacancy in vacancies:
            if vacancy.days_open and vacancy.days_open >= threshold_days \
                    and vacancy.days_open % 30 == 0:
                vacancy.message_post(
                    body=("This vacancy has been open for %d days.") % vacancy.days_open)

    @api.model
    def get_recruitment_dashboard_data(self):
        """Aggregate the recruitment dashboard data: vacancy pipeline, approvals,
        applications in flight, stage funnel, vacancy ageing and (only for
        authorised users) pre-employment-check status. Kept as light,
        read-only summaries — never sensitive check detail."""
        Application = self.env['nhs.application']
        Check = self.env['nhs.check']
        can_view_checks = self.env.user.has_group('odoo_nhs_recruitment.group_nhs_recruit_checks') \
            or self.env.user.has_group('odoo_nhs_recruitment.group_nhs_recruit_manager')

        # 1. Open vacancy pipeline
        open_domain = [('state', 'in', ('open', 'in_progress'))]
        open_recs = self.search(open_domain, limit=10, order='create_date desc')
        open_count = self.search_count(open_domain)
        open_list = [{
            'id': v.id,
            'name': v.name,
            'reference': v.reference,
            'org_unit': v.org_unit_id.name or '',
            'state_label': dict(v._fields['state'].selection).get(v.state, v.state),
            'days_open': v.days_open,
            'application_count': v.application_count,
        } for v in open_recs]

        # 2. Awaiting approval
        approval_domain = [('state', 'in', ('submitted', 'workforce_approved'))]
        approval_count = self.search_count(approval_domain)

        # 3. Applications in flight
        in_flight_domain = [('stage', 'not in', ('hired', 'rejected', 'withdrawn'))]
        in_flight_count = Application.search_count(in_flight_domain)

        # 4. Stage funnel (application counts per pipeline stage)
        funnel_data = Application._read_group(
            [], ['stage'], ['__count'])
        funnel_counts = {stage: count for stage, count in funnel_data}
        stage_labels = dict(Application._fields['stage'].selection)
        funnel = [{
            'stage': stage,
            'label': label,
            'count': funnel_counts.get(stage, 0),
        } for stage, label in stage_labels.items()]

        # 5. Vacancy ageing — longest-open vacancies (days_open is a live, non-stored
        # computed field, so sort in Python rather than via ORM order)
        ageing_candidates = self.search(open_domain)
        ageing_sorted = ageing_candidates.sorted('days_open', reverse=True)[:10]
        ageing_list = [{
            'id': v.id,
            'name': v.name,
            'org_unit': v.org_unit_id.name or '',
            'days_open': v.days_open,
        } for v in ageing_sorted if v.days_open]

        # 6. Time-to-hire (average, across filled vacancies)
        filled_recs = self.search([('time_to_hire', '>', 0)])
        avg_time_to_hire = round(
            sum(filled_recs.mapped('time_to_hire')) / len(filled_recs), 1) if filled_recs else 0

        # 7. Pre-employment checks (restricted — counts/list only for authorised users)
        checks_outstanding_count = 0
        checks_outstanding_list = []
        checks_concern_count = 0
        if can_view_checks:
            outstanding_domain = [('status', 'in', ('not_started', 'in_progress'))]
            checks_outstanding_count = Check.search_count(outstanding_domain)
            outstanding_recs = Check.search(outstanding_domain, limit=10, order='id desc')
            checks_outstanding_list = [{
                'id': c.id,
                'candidate': c.candidate_id.name or '',
                'check_type': c.check_type_id.name or '',
                'status_label': dict(c._fields['status'].selection).get(c.status, c.status),
            } for c in outstanding_recs]
            checks_concern_count = Check.search_count([('status', '=', 'concern')])

        return {
            'open_count': open_count,
            'open_list': open_list,
            'approval_count': approval_count,
            'in_flight_count': in_flight_count,
            'funnel': funnel,
            'ageing_list': ageing_list,
            'avg_time_to_hire': avg_time_to_hire,
            'can_view_checks': can_view_checks,
            'checks_outstanding_count': checks_outstanding_count,
            'checks_outstanding_list': checks_outstanding_list,
            'checks_concern_count': checks_concern_count,
        }
