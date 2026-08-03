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
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

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
        domain="[('company_id', '=', company_id)]",
        help="The funded post being recruited to. Pulls band/staff group/FTE/unit."
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
    person_spec_id = fields.Many2one('nhs.person.spec', string='Person Specification')
    check_profile_id = fields.Many2one(
        'nhs.check.profile',
        string='Check Profile',
        help="Which pre-employment checks apply to a successful candidate;"
             " defaulted from the post's staff group."
    )
    state = fields.Selection(
        VACANCY_STATES, string='Status', required=True, default='draft', tracking=True)
    withdrawn_reason = fields.Text(string='Withdrawal Reason')
    advert_text = fields.Html(string='Advert Text')
    advert_summary = fields.Char(string='Advert Summary')
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
    days_open = fields.Integer(string='Days Open', compute='_compute_days_open')
    filled_date = fields.Date(string='Filled Date', readonly=True)
    time_to_hire = fields.Integer(
        string='Time to Hire (days)',
        compute='_compute_time_to_hire',
        store=True,
        help="Open → filled days, once filled."
    )
    active = fields.Boolean(string='Active', default=True)

    @api.depends('post_id.job_title', 'org_unit_id.name', 'reference')
    def _compute_name(self):
        for vacancy in self:
            title = vacancy.post_id.job_title or _('New Vacancy')
            unit = vacancy.org_unit_id.name
            parts = [p for p in (title, unit) if p]
            label = ' — '.join(parts)
            if vacancy.reference and vacancy.reference != 'New':
                label = f'{label} ({vacancy.reference})'
            vacancy.name = label

    @api.depends('post_id.band_id.indicative_salary', 'post_id.manual_indicative_salary',
                 'post_id.is_medical', 'fte', 'company_id.nhs_on_cost_factor')
    def _compute_indicative_cost(self):
        for vacancy in self:
            post = vacancy.post_id
            on_cost = vacancy.company_id.nhs_on_cost_factor or 1.0
            base_salary = post.manual_indicative_salary if post.is_medical else (
                post.band_id.indicative_salary or 0.0)
            vacancy.indicative_cost = base_salary * vacancy.fte * on_cost

    def _compute_application_count(self):
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

    def _compute_days_open(self):
        today = fields.Date.context_today(self)
        for vacancy in self:
            if vacancy.state in ('filled', 'closed', 'withdrawn') or not vacancy.open_date:
                vacancy.days_open = 0
            else:
                vacancy.days_open = (today - vacancy.open_date).days

    @api.depends('filled_date', 'open_date')
    def _compute_time_to_hire(self):
        for vacancy in self:
            if vacancy.filled_date and vacancy.open_date:
                vacancy.time_to_hire = (vacancy.filled_date - vacancy.open_date).days
            else:
                vacancy.time_to_hire = 0

    @api.constrains('fte', 'post_id')
    def _check_fte(self):
        for vacancy in self:
            if vacancy.fte <= 0:
                raise ValidationError(_('Vacancy FTE must be greater than zero.'))

    @api.onchange('post_id')
    def _onchange_post_id(self):
        for vacancy in self:
            if vacancy.post_id:
                vacancy.fte = vacancy.post_id.vacant_fte or vacancy.post_id.funded_fte or 1.0
                if not vacancy.check_profile_id:
                    vacancy.check_profile_id = self.env['nhs.check.profile'] \
                        ._get_default_for_staff_group(vacancy.post_id.staff_group_id.id)

    @api.model_create_multi
    def create(self, vals_list):
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
                raise UserError(_(
                    "'%s' cannot be approved: the post has no funded FTE.") % vacancy.name)
            if post.is_frozen:
                raise UserError(_(
                    "'%s' cannot be approved: the post is frozen.") % vacancy.name)
            if post.vacant_fte <= 0:
                raise UserError(_(
                    "'%s' cannot be approved: the post has no vacant capacity.") % vacancy.name)

    def action_submit(self):
        for vacancy in self:
            if vacancy.state != 'draft':
                raise UserError(_('Only draft vacancies can be submitted.'))
        self.write({'state': 'submitted'})

    def action_workforce_approve(self):
        for vacancy in self:
            if vacancy.state != 'submitted':
                raise UserError(_('Only submitted vacancies can be workforce-approved.'))
            vacancy._check_post_fundable()
        self.write({'state': 'workforce_approved'})

    def action_finance_approve(self):
        for vacancy in self:
            if vacancy.state != 'workforce_approved':
                raise UserError(_('Only workforce-approved vacancies can be finance-approved.'))
            vacancy._check_post_fundable()
        self.write({'state': 'finance_approved'})

    def action_open(self):
        today = fields.Date.context_today(self)
        for vacancy in self:
            if vacancy.state != 'finance_approved':
                raise UserError(_('Only finance-approved vacancies can be opened.'))
            if not vacancy.open_date:
                vacancy.open_date = today
        self.write({'state': 'open'})

    def action_mark_in_progress(self):
        for vacancy in self:
            if vacancy.state == 'open':
                vacancy.state = 'in_progress'

    def action_mark_filled(self):
        """Called by the onboarding wizard once a hire is confirmed."""
        today = fields.Date.context_today(self)
        self.write({'state': 'filled', 'filled_date': today})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_withdraw(self):
        for vacancy in self:
            if vacancy.state == 'filled':
                raise UserError(_('A filled vacancy cannot be withdrawn.'))
        self.write({'state': 'withdrawn'})

    def action_view_applications(self):
        self.ensure_one()
        return {
            'name': _('Applications'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.application',
            'view_mode': 'kanban,list,form',
            'domain': [('vacancy_id', '=', self.id)],
            'context': {'default_vacancy_id': self.id},
        }

    def action_view_interviews(self):
        self.ensure_one()
        return {
            'name': _('Interviews'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.interview',
            'view_mode': 'list,form',
            'domain': [('vacancy_id', '=', self.id)],
        }

    def action_view_offers(self):
        self.ensure_one()
        return {
            'name': _('Offers'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.offer',
            'view_mode': 'list,form',
            'domain': [('vacancy_id', '=', self.id)],
        }

    @api.model
    def _cron_check_vacancy_ageing(self, threshold_days=60):
        """Nudge followers on vacancies open beyond the ageing threshold."""
        vacancies = self.search([('state', 'in', ('open', 'in_progress'))])
        for vacancy in vacancies:
            if vacancy.days_open and vacancy.days_open >= threshold_days \
                    and vacancy.days_open % 30 == 0:
                vacancy.message_post(
                    body=_("This vacancy has been open for %d days.") % vacancy.days_open)
