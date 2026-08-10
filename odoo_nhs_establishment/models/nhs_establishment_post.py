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

VACANCY_STATUSES = [
    ('fully_staffed', 'Fully Staffed'),
    ('part_vacant', 'Part Vacant'),
    ('fully_vacant', 'Fully Vacant'),
    ('over_established', 'Over-Established'),
]

CONTROLLED_FIELDS = ('funded_fte', 'band_id', 'org_unit_id')


class NhsEstablishmentPost(models.Model):
    _name = 'nhs.establishment.post'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A funded establishment post (position, not person)'
    _order = 'org_unit_id, job_title'

    name = fields.Char(
        string='Post Summary',
        compute='_compute_name',
        store=True,
        help="Display, e.g. 'Band 5 Theatre Nurse — Main Theatres'."
    )
    reference = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help="Establishment/post number, sequenced."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning company."
    )
    job_title = fields.Char(
        string='Job Title',
        required=True,
        tracking=True,
        help="Post job title."
    )
    org_unit_id = fields.Many2one(
        'nhs.org.unit',
        string='Team / Department',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
        help="Team/department the post belongs to."
    )
    staff_group_id = fields.Many2one(
        'nhs.staff.group',
        string='Staff Group',
        required=True,
        tracking=True,
        index=True,
        help="Standard NHS staff group."
    )
    band_id = fields.Many2one(
        'nhs.afc.band',
        string='Agenda for Change Band',
        tracking=True,
        help="Agenda for Change band. Left blank when Medical / Non-AfC is ticked."
    )
    is_medical = fields.Boolean(
        string='Medical / Non-AfC',
        tracking=True,
        help="Post sits outside Agenda for Change (medical/dental/VSM); enables a manual pay value."
    )
    manual_indicative_salary = fields.Monetary(
        string='Manual Indicative Salary',
        currency_field='currency_id',
        help="Indicative annual salary for Medical/Non-AfC posts, entered manually since"
             " they are not on an Agenda for Change band."
    )
    cost_centre = fields.Many2one(
        'nhs.cost.centre',
        string='Cost Centre',
        help="Cost centre. Defaults from the org unit when the org unit is set."
    )
    manager_id = fields.Many2one(
        'res.users',
        string='Manager / Lead',
        related='org_unit_id.manager_id',
        readonly=True,
        store=True,
        help="Manager of the organisational unit."
    )
    contracted_hours = fields.Float(
        string='Contracted Hours (per week)',
        default=37.5,
        digits=(16, 2),
        help="Weekly contracted hours for one full post (default 37.5)."
    )
    funded_fte = fields.Float(
        string='Funded FTE',
        required=True,
        tracking=True,
        digits=(16, 2),
        help="Funded FTE this post line represents (e.g. 4.0 for four full-time nurses)."
    )
    funded_headcount = fields.Integer(
        string='Funded Headcount',
        default=1,
        help="Funded headcount (posts), where tracked distinctly from FTE."
    )
    in_post_fte = fields.Float(
        string='In-Post FTE',
        default=0.0,
        tracking=True,
        digits=(16, 2),
        help="FTE currently filled. Maintained directly or via an optional hr soft-link."
    )
    in_post_headcount = fields.Integer(
        string='In-Post Headcount',
        default=0,
        help="Headcount currently in post."
    )
    vacant_fte = fields.Float(
        string='Vacant FTE',
        compute='_compute_vacant',
        store=True,
        digits=(16, 2),
        help="funded_fte - in_post_fte."
    )
    vacancy_status = fields.Selection(
        VACANCY_STATUSES,
        string='Vacancy Status',
        compute='_compute_vacant',
        store=True,
        help="fully_staffed / part_vacant / fully_vacant / over_established (in-post > funded)."
    )
    is_frozen = fields.Boolean(
        string='Frozen Post',
        tracking=True,
        help="Funded but recruitment paused — counted separately from true vacancies"
             " in the vacancy register."
    )
    vacancy_start_date = fields.Date(
        string='Vacancy Start Date',
        tracking=True,
        help="When the current vacancy began; drives time-vacant reporting."
             " Set automatically when a post becomes vacant, cleared when fully staffed."
    )
    days_vacant = fields.Integer(
        string='Days Vacant',
        compute='_compute_days_vacant',
        help="Age of the current vacancy in days, for reporting."
    )
    contract_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('fixed_term', 'Fixed Term'),
    ],
        string='Contract Type',
        default='permanent',
        help="Fixed-term vs permanent indicator."
    )
    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('deleted', 'Deleted'),
    ],
        string='Status',
        required=True,
        default='draft',
        tracking=True,
        help="Draft = newly created post, Active = active funded post, Frozen = paused post, Deleted = removed post."
    )
    effective_from = fields.Date(
        string='Effective From',
        help="Post validity start date."
    )
    effective_to = fields.Date(
        string='Effective To',
        help="Post validity end date."
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        help="Currency used for indicative pay figures."
    )
    indicative_pay = fields.Monetary(
        string='Indicative Annual Pay',
        compute='_compute_indicative_pay',
        store=True,
        currency_field='currency_id',
        help="Band value (or manual value for Medical/Non-AfC) x funded FTE x on-cost"
             " factor. Indicative budget planning figure only."
    )
    job_description = fields.Binary(
        string='Job Description',
        attachment=True,
        help="Optional job description document."
    )
    job_description_filename = fields.Char(string='Job Description Filename')
    notes = fields.Text(
        string='Notes',
        help="Free-text notes about this post."
    )
    change_ids = fields.One2many(
        'nhs.establishment.change',
        'post_id',
        string='Change History',
        help="Full change-control history for this post."
    )
    change_count = fields.Integer(
        string='Change Count',
        compute='_compute_change_count',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    @api.depends('job_title', 'org_unit_id.name')
    def _compute_name(self):
        for post in self:
            parts = [p for p in (post.job_title, post.org_unit_id.name) if p]
            post.name = ' — '.join(parts) if parts else 'New Post'

    @api.depends('funded_fte', 'in_post_fte')
    def _compute_vacant(self):
        for post in self:
            post.vacant_fte = post.funded_fte - post.in_post_fte
            if post.in_post_fte > post.funded_fte:
                post.vacancy_status = 'over_established'
            elif post.in_post_fte == post.funded_fte:
                post.vacancy_status = 'fully_staffed'
            elif post.in_post_fte == 0:
                post.vacancy_status = 'fully_vacant'
            else:
                post.vacancy_status = 'part_vacant'

    def _compute_days_vacant(self):
        today = fields.Date.context_today(self)
        for post in self:
            if post.vacancy_start_date and post.vacancy_status in ('part_vacant', 'fully_vacant'):
                post.days_vacant = (today - post.vacancy_start_date).days
            else:
                post.days_vacant = 0

    @api.depends('band_id.indicative_salary', 'manual_indicative_salary', 'funded_fte',
                 'is_medical', 'company_id.nhs_on_cost_factor')
    def _compute_indicative_pay(self):
        for post in self:
            on_cost_factor = post.company_id.nhs_on_cost_factor or 1.0
            base_salary = post.manual_indicative_salary if post.is_medical else (
                post.band_id.indicative_salary or 0.0)
            post.indicative_pay = base_salary * post.funded_fte * on_cost_factor

    def _compute_change_count(self):
        change_data = self.env['nhs.establishment.change']._read_group(
            [('post_id', 'in', self.ids)],
            ['post_id'], ['__count'],
        )
        counts = {post.id: count for post, count in change_data}
        for post in self:
            post.change_count = counts.get(post.id, 0)

    @api.model
    def _compute_fte_value(self, contracted_hours, headcount, basis):
        """Pure FTE math helper: FTE = contracted hours / full-time basis * headcount."""
        if not basis:
            return 0.0
        val = 0 if headcount == 0 else (headcount or 1)
        return round((contracted_hours or 0.0) / basis * val, 2)

    @api.onchange('contracted_hours', 'funded_headcount', 'in_post_headcount')
    def _onchange_fte_basis(self):
        basis = self.company_id.nhs_full_time_hours_basis or 37.5
        if self.contracted_hours:
            self.funded_fte = self._compute_fte_value(
                self.contracted_hours, self.funded_headcount, basis)
            self.in_post_fte = self._compute_fte_value(
                self.contracted_hours, self.in_post_headcount, basis)

    @api.onchange('org_unit_id')
    def _onchange_org_unit_id(self):
        if self.org_unit_id and not self.cost_centre:
            self.cost_centre = self.org_unit_id.cost_centre

    @api.onchange('is_medical')
    def _onchange_is_medical(self):
        if self.is_medical:
            self.band_id = False

    @api.constrains('funded_fte', 'in_post_fte')
    def _check_fte_non_negative(self):
        for post in self:
            if post.funded_fte < 0:
                raise ValidationError('Funded FTE cannot be negative!')
            if post.in_post_fte < 0:
                raise ValidationError('In-Post FTE cannot be negative!')

    @api.constrains('band_id', 'is_medical', 'status')
    def _check_band_required(self):
        for post in self:
            if post.status != 'deleted' and not post.is_medical and not post.band_id:
                raise ValidationError(
                    'An Agenda for Change band is required unless the post is'
                    ' marked Medical / Non-AfC.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'nhs.establishment.post') or 'New'
            if vals.get('status') == 'deleted':
                vals['active'] = False
                vals['is_frozen'] = False
            elif vals.get('status') == 'frozen':
                vals['active'] = True
                vals['is_frozen'] = True
            elif vals.get('status') in ('active', 'draft'):
                vals['active'] = True
                vals['is_frozen'] = False
            elif vals.get('is_frozen'):
                vals['status'] = 'frozen'
        posts = super().create(vals_list)
        posts._update_vacancy_start_date()
        return posts

    def write(self, vals):
        if any(field_name in vals for field_name in CONTROLLED_FIELDS) \
                and not self.env.context.get('nhs_change_control_apply'):
            for post in self:
                if post.company_id.nhs_change_control_required:
                    raise UserError(
                        "Changes to funded FTE, band or team must go through an"
                        " Establishment Change Request. Use the 'Raise Change Request'"
                        " button on the post.")

        if 'active' in vals and not vals['active'] and 'status' not in vals:
            vals['status'] = 'deleted'
        elif 'active' in vals and vals['active'] and 'status' not in vals:
            vals['status'] = 'active'

        if 'status' in vals:
            if vals['status'] == 'deleted':
                vals['active'] = False
                vals['is_frozen'] = False
            elif vals['status'] == 'frozen':
                vals['active'] = True
                vals['is_frozen'] = True
            elif vals['status'] in ('active', 'draft'):
                vals['active'] = True
                vals['is_frozen'] = False
        elif 'is_frozen' in vals:
            if vals['is_frozen']:
                vals['status'] = 'frozen'
            else:
                vals['status'] = 'active'

        result = super().write(vals)
        if 'in_post_fte' in vals or 'funded_fte' in vals or 'is_frozen' in vals or 'status' in vals:
            self._update_vacancy_start_date()
        return result

    def _update_vacancy_start_date(self):
        today = fields.Date.context_today(self)
        for post in self:
            if post.vacancy_status in ('part_vacant', 'fully_vacant'):
                if not post.vacancy_start_date:
                    post.vacancy_start_date = today
            elif post.vacancy_start_date:
                post.vacancy_start_date = False

    def action_raise_change_request(self):
        self.ensure_one()
        return {
            'name': 'Raise Establishment Change Request',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.establishment.change.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_post_id': self.id,
                'default_org_unit_id': self.org_unit_id.id,
                'default_change_type': 'increase_fte',
            },
        }

    def action_view_changes(self):
        self.ensure_one()
        return {
            'name': 'Change History',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.establishment.change',
            'view_mode': 'list,form',
            'domain': [('post_id', '=', self.id)],
        }

    def action_freeze_post(self):
        self.write({'status': 'frozen'})

    def action_activate_post(self):
        self.write({'status': 'active'})

    def action_delete_post(self):
        self.write({'status': 'deleted'})

    @api.model
    def get_import_templates(self):
        """Provide the standard template offered on the Posts import screen.

        The '?v=2' query string busts the browser's static-file cache after the
        template content changes; bump it whenever the .xlsx is regenerated."""
        return [{
            'label': 'Import Template for Posts',
            'template': '/odoo_nhs_establishment/static/import_templates/posts_import_template.xlsx?v=3',
        }]

    @api.model
    def _cron_check_long_vacancies(self, threshold_days=90):
        """Nightly refresh: nudge followers on posts vacant beyond the threshold
        so long-standing vacancies don't go unnoticed between reporting cycles."""
        posts = self.search([
            ('vacancy_status', 'in', ('part_vacant', 'fully_vacant')),
            ('is_frozen', '=', False),
            ('status', '=', 'active'),
        ])
        for post in posts:
            if post.days_vacant and post.days_vacant >= threshold_days and post.days_vacant % 30 == 0:
                post.message_post(
                    body=f"This post has been vacant for {post.days_vacant} days "
                         f"({post.vacant_fte:.2f} FTE vacant).")
