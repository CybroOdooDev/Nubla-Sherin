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
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round

STATES = [
    ('draft', 'Draft'),
    ('proposed', 'Proposed'),
    ('in_discussion', 'In Discussion'),
    ('agreed', 'Agreed'),
    ('signed', 'Signed'),
    ('revised', 'Revised'),
    ('superseded', 'Superseded'),
]

LOCKED_STATES = ('signed', 'revised')
CONTROLLED_FIELDS = ('timetable_activity_ids', 'objective_ids', 'contracted_pas', 'oncall_profile_id')
PROPOSERS = [
    ('doctor', 'Doctor'),
    ('manager', 'Manager'),
]


class NhsJobPlan(models.Model):
    """One consultant/SAS doctor's annual job plan: the weekly timetable of
    Programmed Activities against their Establishment post, on-call profile,
    objectives and the doctor/manager two-party sign-off cycle."""
    _name = 'nhs.job.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'NHS Medical Job Plan'
    _order = 'plan_year_id desc, doctor_name'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="Display, e.g. 'Dr A Patel — 2026/27'."
    )
    reference = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help="Job plan number, sequenced, e.g. 'JP/2026/0001'."
    )
    doctor_user_id = fields.Many2one(
        'res.users',
        string='Doctor User',
        required=True,
        domain="[('share', '=', False)]",
        tracking=True,
        help="The doctor's login - single source of identity for the plan.")
    doctor_name = fields.Char(
        string='Doctor',
        related='doctor_user_id.name',
        store=True,
        index=True,
        help="Doctor's display name, derived from Doctor User - not entered"
             " by hand. Kept as a stored field so sorting, search, templates"
             " and reports can keep referencing it unchanged."
    )
    can_edit_doctor_user_id = fields.Boolean(
        string='Can Edit Doctor',
        compute='_compute_can_edit_doctor_user_id',
        help="Technical field for the view: only clinical managers/admins may"
             " (re)point a plan at a different doctor."
    )

    post_id = fields.Many2one(
        'nhs.establishment.post',
        string='Medical Post',
        required=True,
        domain="[('is_medical', '=', True), ('status', '=', 'active'), ('id', 'in', allowed_post_ids)]",
        tracking=True,
        index=True,
        help="The doctor's funded Establishment post."
    )
    allowed_post_ids = fields.Many2many(
        'nhs.establishment.post',
        compute='_compute_allowed_post_ids',
        help="Backs the Medical Post field's selection list: every active"
             " medical post for an Admin, only those under the current"
             " user's own Clinical Manager directorate scope otherwise (so a"
             " manager can't accidentally raise a plan against an unrelated"
             " directorate's post). A Doctor with no manager scope of their"
             " own still sees every active medical post - there is no"
             " post-to-holder link in this suite to narrow it further."
    )
    specialty = fields.Char(
        string='Specialty',
        help="Specialty this plan covers, defaulted from the post's job title"
             " but editable per plan."
    )
    org_unit_id = fields.Many2one(
        'nhs.org.unit',
        string='Directorate / Unit',
        related='post_id.org_unit_id',
        store=True,
        help="Organisational unit, from the post. Drives directorate-scoped"
             " access for clinical managers."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='post_id.company_id',
        store=True,
        help="Owning company, from the post."
    )
    manager_ids = fields.Many2many(
        'res.users',
        string='Directorate Managers',
        compute='_compute_manager_ids',
        store=True,
        help="Every manager/lead in this plan's org-unit ancestor chain -"
             " the set of users a clinical-manager-tier record rule matches"
             " against, so a directorate lead sees every plan under them."
    )
    plan_year_id = fields.Many2one(
        'nhs.plan.year',
        string='Plan Year',
        required=True,
        tracking=True,
        index=True,
        help="The annual job-planning cycle this plan belongs to."
    )
    contracted_pas = fields.Float(
        string='Contracted PAs',
        required=True,
        default=10.0,
        digits=(16, 2),
        tracking=True,
        help="Contracted Programmed Activities (nominally 10 for a full-time plan)."
    )
    fte = fields.Float(
        string='FTE',
        compute='_compute_fte',
        store=True,
        digits=(16, 3),
        help="contracted_pas / company's configured PAs-per-WTE."
    )
    timetable_activity_ids = fields.One2many(
        'nhs.job.plan.activity',
        'plan_id',
        string='Timetable Activities',
        copy=True,
        help="The weekly timetable lines (Programmed Activities). copy=True"
             " (One2many defaults to copy=False) so action_start_revision and"
             " the rollover wizard's plan.copy({...}) both carry the timetable"
             " across onto the new record."
    )
    dcc_pas = fields.Float(
        string='DCC PAs',
        compute='_compute_pa_totals',
        store=True,
        digits=(16, 2),
        help="Total Direct Clinical Care PAs from the timetable."
    )
    spa_pas = fields.Float(
        string='SPA PAs',
        compute='_compute_pa_totals',
        store=True,
        digits=(16, 2),
        help="Total Supporting Professional Activities PAs from the timetable."
    )
    additional_pas = fields.Float(
        string='Additional PAs',
        compute='_compute_pa_totals',
        store=True,
        digits=(16, 2),
        help="Total Additional Responsibility PAs from the timetable, plus the"
             " on-call profile's total on-call PAs."
    )
    external_pas = fields.Float(
        string='External PAs',
        compute='_compute_pa_totals',
        store=True,
        digits=(16, 2),
        help="Total External Duty PAs from the timetable."
    )
    total_pas = fields.Float(
        string='Total PAs',
        compute='_compute_pa_totals',
        store=True,
        digits=(16, 2),
        help="dcc_pas + spa_pas + additional_pas + external_pas."
    )
    pa_balance = fields.Float(
        string='PA Balance',
        compute='_compute_pa_totals',
        store=True,
        digits=(16, 2),
        help="total_pas - contracted_pas. Positive = over-committed, negative ="
             " under-committed against contract."
    )
    dcc_spa_ratio = fields.Char(
        string='DCC : SPA Ratio',
        compute='_compute_pa_totals',
        store=True,
        help="Display-only 'DCC : SPA' split string, e.g. '7.5 : 2.5'."
    )
    oncall_profile_id = fields.Many2one(
        'nhs.oncall.profile',
        string='On-Call Profile',
        tracking=True,
        help="On-call frequency, category and PA commitment for this plan."
    )
    objective_ids = fields.One2many(
        'nhs.job.plan.objective',
        'plan_id',
        string='Objectives',
        copy=True,
        help="Personal objectives on the plan. copy=True so revisions and"
             " rollover carry objectives across onto the new record."
    )
    objective_count = fields.Integer(
        string='Objective Count',
        compute='_compute_objective_count',
        help="Number of objectives on the plan."
    )
    rostered_duties_count = fields.Integer(
        string='Rostered Duties',
        compute='_compute_rostered_metrics',
        help="Number of rostered duties for this doctor in this plan year."
    )
    rostered_pas = fields.Float(
        string='Rostered PAs',
        compute='_compute_rostered_metrics',
        digits=(16, 2),
        help="Total Paid Hours from rostered duties converted to PAs (Paid Hours / 4.0)."
    )
    rostered_pa_variance = fields.Float(
        string='PA Variance',
        compute='_compute_rostered_metrics',
        digits=(16, 2),
        help="Rostered PAs minus Total Planned PAs."
    )
    state = fields.Selection(
        STATES,
        string='Status',
        required=True,
        default='draft',
        tracking=True,
        help="draft -> proposed -> in_discussion -> agreed -> signed ->"
             " (in-year revision) -> revised / superseded."
    )   
    previous_plan_id = fields.Many2one(
        'nhs.job.plan',
        string='Previous Version',
        ondelete='set null',
        readonly=True,
        copy=False,
        help="The plan this one revises, if it was created via in-year revision."
    )
    revision_number = fields.Integer(
        string='Revision Number',
        default=1,
        readonly=True,
        copy=False,
        help="Increments each time this plan is revised in-year."
    )
    superseded_by_id = fields.Many2one(
        'nhs.job.plan',
        string='Superseded By',
        readonly=True,
        copy=False,
        help="The later revision that replaced this plan, if any."
    )
    proposed_by = fields.Selection(
        PROPOSERS,
        string='Proposed By',
        tracking=True,
        help="Who initiated the current proposal - the doctor or the manager."
    )
    doctor_signed_at = fields.Datetime(
        string='Doctor Signed At',
        readonly=True,
        copy=False,
        help="Timestamp of the doctor's sign-off."
    )
    doctor_signed_by = fields.Many2one(
        'res.users',
        string='Doctor Signed By',
        readonly=True,
        copy=False,
        help="User who actually signed as the doctor."
    )
    manager_signed_at = fields.Datetime(
        string='Manager Signed At',
        readonly=True,
        copy=False,
        help="Timestamp of the clinical manager's sign-off."
    )
    manager_signed_by = fields.Many2one(
        'res.users',
        string='Manager Signed By',
        readonly=True,
        copy=False,
        help="User who actually signed as the clinical manager."
    )
    escalation_note = fields.Text(
        string='Escalation / Mediation Note',
        help="Escalation route recorded where agreement fails - mediation or"
             " appeal notes."
    )
    supporting_resources_note = fields.Text(
        string='Supporting Resources',
        help="Supporting resources/facilities notes, e.g. clinic space,"
             " secretarial support."
    )
    review_due_date = fields.Date(
        string='Review Due Date',
        compute='_compute_review_due_date',
        store=True,
        help="plan_year_id's end date minus the company's configured review"
             " lead days. Drives the annual-review reminder cron."
    )
    is_locked = fields.Boolean(
        string='Locked',
        compute='_compute_is_locked',
        store=True,
        help="True once both parties have signed (state signed/revised)."
             " Locked plans cannot have their timetable, contracted PAs or"
             " on-call profile edited - a new revision must be started instead."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    def _compute_can_edit_doctor_user_id(self):
        can_edit = self.env.user.has_group('odoo_nhs_job_planning.group_nhs_jobplan_manager')
        for plan in self:
            plan.can_edit_doctor_user_id = can_edit

    @api.depends('doctor_name', 'plan_year_id.name')
    def _compute_name(self):
        """Build the display name from doctor and plan year."""
        for plan in self:
            if plan.doctor_name and plan.plan_year_id:
                plan.name = '%s — %s' % (plan.doctor_name, plan.plan_year_id.name)
            else:
                plan.name = plan.doctor_name or 'New Job Plan'

    @api.depends('contracted_pas', 'company_id.nhs_jobplan_pas_per_wte')
    def _compute_fte(self):
        """Derive FTE from contracted PAs and the company's PAs-per-WTE setting."""
        for plan in self:
            basis = plan.company_id.nhs_jobplan_pas_per_wte or 10.0
            plan.fte = round((plan.contracted_pas or 0.0) / basis, 3) if basis else 0.0

    @api.depends('timetable_activity_ids.effective_pa_value', 'timetable_activity_ids.classification',
                 'contracted_pas', 'oncall_profile_id.total_oncall_pas')
    def _compute_pa_totals(self):
        """Sum timetable PAs by classification and derive the balance/ratio."""
        for plan in self:
            lines = plan.timetable_activity_ids
            dcc = sum(lines.filtered(lambda l: l.classification == 'dcc').mapped('effective_pa_value'))
            spa = sum(lines.filtered(lambda l: l.classification == 'spa').mapped('effective_pa_value'))
            additional = sum(lines.filtered(
                lambda l: l.classification == 'additional').mapped('effective_pa_value'))
            additional += plan.oncall_profile_id.total_oncall_pas or 0.0
            external = sum(lines.filtered(lambda l: l.classification == 'external').mapped('effective_pa_value'))
            plan.dcc_pas = dcc
            plan.spa_pas = spa
            plan.additional_pas = additional
            plan.external_pas = external
            plan.total_pas = dcc + spa + additional + external
            plan.pa_balance = plan.total_pas - (plan.contracted_pas or 0.0)
            plan.dcc_spa_ratio = '%.1f : %.1f' % (dcc, spa)

    def _compute_objective_count(self):
        """Count objectives on each plan."""
        for plan in self:
            plan.objective_count = len(plan.objective_ids)

    @api.depends('state', 'doctor_signed_at', 'manager_signed_at')
    def _compute_is_locked(self):
        """A plan is locked once it has reached signed/revised."""
        for plan in self:
            plan.is_locked = plan.state in LOCKED_STATES

    @api.depends('plan_year_id.date_end', 'company_id.nhs_jobplan_review_lead_days')
    def _compute_review_due_date(self):
        """Review is due a configurable number of days before plan-year end."""
        for plan in self:
            if plan.plan_year_id.date_end:
                lead_days = plan.company_id.nhs_jobplan_review_lead_days or 60
                plan.review_due_date = plan.plan_year_id.date_end - timedelta(days=lead_days)
            else:
                plan.review_due_date = False

    @api.depends('org_unit_id.parent_path')
    def _compute_manager_ids(self):
        """Collect the manager/lead of every ancestor unit (and this plan's own
        unit) in the org hierarchy - the set a directorate-scoped clinical
        manager record rule matches on, since nhs.org.unit only carries a
        single manager_id per unit rather than a Many2many manager set."""
        OrgUnit = self.env['nhs.org.unit']
        for plan in self:
            if not plan.org_unit_id or not plan.org_unit_id.parent_path:
                plan.manager_ids = [(5, 0, 0)]
                continue
            ancestor_ids = [int(part) for part in plan.org_unit_id.parent_path.split('/') if part]
            managers = OrgUnit.browse(ancestor_ids).mapped('manager_id')
            plan.manager_ids = [(6, 0, managers.ids)]

    @api.depends('plan_year_id.date_start', 'plan_year_id.date_end', 'org_unit_id',
                 'doctor_user_id', 'total_pas')
    def _compute_rostered_metrics(self):
        for plan in self:
            count = 0
            rostered_pas = 0.0

            if plan.plan_year_id:
                member_id = False
                if plan.doctor_user_id:
                    member = self.env['nhs.workforce.member'].search([('user_id', '=', plan.doctor_user_id.id)], limit=1)
                    if member:
                        member_id = member.id

                if member_id:
                    domain = [
                        ('member_id', '=', member_id),
                        ('duty_date', '>=', plan.plan_year_id.date_start),
                        ('duty_date', '<=', plan.plan_year_id.date_end),
                        ('state', 'not in', ('cancelled', 'dna')),
                    ]
                    if plan.org_unit_id:
                        domain.append(('duty_id.unit_id.org_unit_id', '=', plan.org_unit_id.id))

                    assignments = self.env['nhs.duty.assignment'].search(domain)
                    count = len(assignments)

                    total_hours = sum(assignments.mapped('paid_hours'))
                    rostered_pas = float_round(total_hours / 4.0, precision_digits=2)

            plan.rostered_duties_count = count
            plan.rostered_pas = rostered_pas
            plan.rostered_pa_variance = rostered_pas - plan.total_pas

    def action_view_rostered_duties(self):
        """Open the rostered duties view."""
        self.ensure_one()
        member_id = False
        if self.doctor_user_id:
            member = self.env['nhs.workforce.member'].search([('user_id', '=', self.doctor_user_id.id)], limit=1)
            if member:
                member_id = member.id
                
        if not member_id:
            return

        domain = [
            ('member_id', '=', member_id),
            ('duty_date', '>=', self.plan_year_id.date_start),
            ('duty_date', '<=', self.plan_year_id.date_end),
            ('state', 'not in', ('cancelled', 'dna')),
        ]
        if self.org_unit_id:
            domain.append(('duty_id.unit_id.org_unit_id', '=', self.org_unit_id.id))
        return {
            'name': 'Rostered Duties',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.duty.assignment',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_member_id': member_id,
                'create': False,
                'edit': False,
                'delete': False,
            },

        }

    @api.depends_context('uid')
    def _compute_allowed_post_ids(self):
        """The reverse of _compute_manager_ids: instead of walking a plan's
        unit up to its managers, walk the current user's own managed units
        down to every post beneath them, so the Medical Post picker only
        offers posts the current Clinical Manager actually has remit over."""
        user = self.env.user
        Post = self.env['nhs.establishment.post']
        base_domain = [('is_medical', '=', True), ('status', '=', 'active')]
        is_manager_only = (
            user.has_group('odoo_nhs_job_planning.group_nhs_jobplan_manager')
            and not user.has_group('odoo_nhs_job_planning.group_nhs_jobplan_doctor')
            and not user.has_group('odoo_nhs_job_planning.group_nhs_jobplan_admin')
        )
        if not is_manager_only:
            allowed = Post.search(base_domain)
        else:
            managed_units = self.env['nhs.org.unit'].search([('manager_id', '=', user.id)])
            unit_ids = set()
            for unit in managed_units:
                descendants = self.env['nhs.org.unit'].search(
                    [('parent_path', '=like', unit.parent_path + '%')])
                unit_ids.update(descendants.ids)
            allowed = Post.search(base_domain + [('org_unit_id', 'in', list(unit_ids))])
        for plan in self:
            plan.allowed_post_ids = allowed

    @api.onchange('post_id')
    def _onchange_post_id(self):
        """Default the specialty from the post's job title."""
        if self.post_id and not self.specialty:
            self.specialty = self.post_id.job_title


    @api.constrains('doctor_user_id', 'plan_year_id', 'post_id', 'state')
    def _check_one_active_plan_per_year(self):
        """At most one non-superseded plan per doctor per post per plan year.
        A business rule, not a DB uniqueness fact - revisions/rollover
        legitimately leave multiple rows for the same doctor+post+year, only
        one of which may be 'live' (not revised/superseded) at a time."""
        active_plans = self.filtered(
            lambda p: p.state not in ('superseded', 'revised') and p.doctor_user_id
        )
        if not active_plans:
            return
        seen = set()
        for plan in active_plans:
            key = (plan.doctor_user_id.id, plan.plan_year_id.id, plan.post_id.id)
            if key in seen:
                raise ValidationError(
                    "Cannot have multiple active job plans for %s against '%s' in"
                    " %s in the same operation." % (
                        plan.doctor_user_id.name, plan.post_id.display_name,
                        plan.plan_year_id.name))
            seen.add(key)
        existing_plans = self.search([
            ('id', 'not in', self.ids),
            ('doctor_user_id', 'in', active_plans.mapped('doctor_user_id.id')),
            ('plan_year_id', 'in', active_plans.mapped('plan_year_id.id')),
            ('post_id', 'in', active_plans.mapped('post_id.id')),
            ('state', 'not in', ('superseded', 'revised')),
        ])
        existing_dict = {
            (p.doctor_user_id.id, p.plan_year_id.id, p.post_id.id): p for p in existing_plans}

        for plan in active_plans:
            key = (plan.doctor_user_id.id, plan.plan_year_id.id, plan.post_id.id)
            if key in existing_dict:
                other = existing_dict[key]
                raise ValidationError(
                    "%s already has a job plan (%s) against '%s' for %s. Revise"
                    " that plan instead of creating a second one." % (
                        plan.doctor_user_id.name, other.reference,
                        plan.post_id.display_name, plan.plan_year_id.name))

    @api.constrains('plan_year_id')
    def _check_plan_year_open(self):
        """A new job plan may only be raised against an 'open' plan year -
        not a still-draft one (nothing to plan against yet) or a closed one
        (the cycle is finished)."""
        if self.env.context.get('nhs_jobplan_skip_year_state_check'):
            return
        for plan in self:
            if plan.plan_year_id.state != 'open':
                raise ValidationError(
                    "'%s' is %s, not Open. A job plan can only be created"
                    " against an open plan year." % (
                        plan.plan_year_id.name, plan.plan_year_id.state))

    @api.model_create_multi
    def create(self, vals_list):
        """Sequence the reference."""
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('nhs.job.plan') or 'New'
        records = super().create(vals_list)
        records._check_creator_can_access()
        return records

    def _check_creator_can_access(self):
        """Warn the creator up front, with a clear explanation, if they are
        about to lose access to the plan they just created."""
        user = self.env.user
        if user.has_group('odoo_nhs_job_planning.group_nhs_jobplan_admin'):
            return
        is_doctor = user.has_group('odoo_nhs_job_planning.group_nhs_jobplan_doctor')
        is_manager = user.has_group('odoo_nhs_job_planning.group_nhs_jobplan_manager')
        for plan in self:
            owns_as_doctor = is_doctor and plan.doctor_user_id.id == user.id
            owns_as_manager = is_manager and user in plan.manager_ids
            if owns_as_doctor or owns_as_manager:
                continue
            unit_name = plan.org_unit_id.display_name if plan.org_unit_id else 'its org unit'
            if is_manager and not is_doctor:
                reason = (
                    "you are not set as the Manager/Lead of '%s' (or any of its"
                    " parent units) in the Org Structure, and you are not"
                    " granted Doctor self-service access either" % unit_name)
            elif is_doctor:
                reason = "the plan's Doctor is not set to you"
            else:
                reason = "you hold neither Doctor nor Clinical Manager access for it"
            raise UserError(
                "You would not be able to open '%s' again after creating it:"
                " %s.\n\nAsk your administrator to set you as Manager/Lead on"
                " the relevant Org Structure unit, or to grant you the"
                " appropriate Job Planning access level, before creating this"
                " plan." % (plan.display_name, reason))

    def write(self, vals):
        """Block edits to the timetable/objectives/contracted PAs/on-call
        profile once a plan has left Draft - Draft is the only state these
        are built/adjusted in; from Proposed onward the plan's content is
        under discussion/sign-off, not still being assembled, and a signed
        plan must be revised via action_start_revision rather than edited in
        place."""
        if any(field_name in vals for field_name in CONTROLLED_FIELDS) \
                and not self.env.context.get('nhs_jobplan_revision_apply'):
            for plan in self:
                if plan.state != 'draft':
                    if plan.is_locked:
                        raise UserError(
                            "'%s' is signed and locked. Start an in-year"
                            " revision to change its timetable, objectives,"
                            " contracted PAs or on-call profile."
                            % plan.display_name)
                    raise UserError(
                        "'%s' is no longer in Draft. Reset it to Draft to"
                        " change its timetable, objectives, contracted PAs"
                        " or on-call profile." % plan.display_name)
        return super().write(vals)

    def action_propose(self, by='manager'):
        """Move a draft plan to proposed, recording who initiated it."""
        for plan in self:
            if plan.state != 'draft':
                raise UserError("Only a draft plan can be proposed.")
            plan.write({'state': 'proposed', 'proposed_by': by})

    def action_open_discussion(self):
        """Move a proposed plan into discussion."""
        for plan in self:
            if plan.state != 'proposed':
                raise UserError("Only a proposed plan can move to discussion.")
        self.write({'state': 'in_discussion'})

    def action_agree(self):
        """Move a plan in discussion to agreed. A large PA imbalance is not a
        hard block (the spec does not ask for one) - it is logged to the
        chatter so the negotiation trail captures it."""
        for plan in self:
            if plan.state != 'in_discussion':
                raise UserError("Only a plan in discussion can be marked agreed.")
            if abs(plan.pa_balance) > 0.5:
                plan.message_post(
                    body="PA balance is %.2f - contracted (%.2f) and planned (%.2f)"
                         " PAs are not reconciled." % (
                             plan.pa_balance, plan.contracted_pas, plan.total_pas))
        self.write({'state': 'agreed'})

    def action_doctor_sign(self):
        """Sign off as the doctor. Locks the plan once the manager has also signed."""
        for plan in self:
            if plan.state != 'agreed':
                raise UserError("Only an agreed plan can be signed.")
            if plan.doctor_user_id and self.env.user != plan.doctor_user_id \
                    and not self.env.user.has_group('odoo_nhs_job_planning.group_nhs_jobplan_admin'):
                raise UserError(
                    "Only the doctor named on this plan (or an administrator)"
                    " can sign as doctor.")
            plan.write({
                'doctor_signed_at': fields.Datetime.now(),
                'doctor_signed_by': self.env.user.id,
            })
            if plan.manager_signed_at:
                plan._lock_plan()

    def action_manager_sign(self):
        """Sign off as the clinical manager. Locks the plan once the doctor
        has also signed."""
        for plan in self:
            if plan.state != 'agreed':
                raise UserError("Only an agreed plan can be signed.")
            if not self.env.user.has_group('odoo_nhs_job_planning.group_nhs_jobplan_manager'):
                raise UserError(
                    "Only a clinical manager (or an administrator) can sign"
                    " as manager.")
            plan.write({
                'manager_signed_at': fields.Datetime.now(),
                'manager_signed_by': self.env.user.id,
            })
            if plan.doctor_signed_at:
                plan._lock_plan()

    def _lock_plan(self):
        """Flip a fully co-signed plan to 'signed' and notify both parties.
        Wrapped in a savepoint so a failure partway through locking rolls
        back the signature stamps and state change atomically."""
        self.ensure_one()
        with self.env.cr.savepoint():
            self.write({'state': 'signed'})
            self.message_post(
                body="Job plan signed by both parties: doctor on %s, manager on %s." % (
                    self.doctor_signed_at, self.manager_signed_at))
            template = self.env.ref(
                'odoo_nhs_job_planning.mail_template_job_plan_signed', raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=False)

    def action_start_revision(self):
        """Start an in-year revision: create a NEW draft plan copying the
        current timetable/objectives/on-call profile, link it back to this
        plan, and flip this plan to 'revised' - the original signed record
        (with its own signatures) is never mutated, satisfying 'prior version
        retained' as new-record versioning rather than in-place history."""
        self.ensure_one()
        if self.state != 'signed':
            raise UserError("Only a signed plan can be revised.")
        with self.env.cr.savepoint():
            self.write({'state': 'revised'})
            new_plan = self.with_context(nhs_jobplan_revision_apply=True).copy({
                'reference': 'New',
                'state': 'draft',
                'previous_plan_id': self.id,
                'revision_number': self.revision_number + 1,
                'doctor_signed_at': False,
                'doctor_signed_by': False,
                'manager_signed_at': False,
                'manager_signed_by': False,
                'proposed_by': False,
                'superseded_by_id': False,
            })
            self.write({'superseded_by_id': new_plan.id})
        return {
            'name': 'Job Plan Revision',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.job.plan',
            'view_mode': 'form',
            'res_id': new_plan.id,
        }

    def action_reset_to_draft(self):
        """Reset a plan to draft. Signed/revised plans must be revised, not reset."""
        for plan in self:
            if plan.state in LOCKED_STATES:
                raise UserError(
                    "'%s' is signed and locked. Start an in-year revision"
                    " instead of resetting it to draft." % plan.display_name)
        self.write({'state': 'draft', 'proposed_by': False})

    def action_view_activities(self):
        """Open this plan's timetable activities."""
        self.ensure_one()
        return {
            'name': 'Timetable Activities',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.job.plan.activity',
            'view_mode': 'list,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }

    def action_view_previous_revision(self):
        """Open the plan this one revises."""
        self.ensure_one()
        if not self.previous_plan_id:
            return False
        return {
            'name': 'Previous Revision',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.job.plan',
            'view_mode': 'form',
            'res_id': self.previous_plan_id.id,
        }

    def action_view_objectives(self):
        """Open this plan's objectives."""
        self.ensure_one()
        return {
            'name': 'Objectives',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.job.plan.objective',
            'view_mode': 'list,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }

    def _get_rollover_candidates(self, source_year, org_units=None, only_signed=True, target_year=None):
        """The source-year job plans eligible for rollover into another year.
        Shared by the manual rollover wizard (nhs.job.plan.rollover.wizard)
        and the automatic-rollover cron below, so both filter identically."""
        domain = [
            ('plan_year_id', '=', source_year.id),
            ('superseded_by_id', '=', False),
            ('state', '!=', 'superseded'),
        ]
        if only_signed:
            domain.append(('state', '=', 'signed'))
        if org_units:
            domain.append(('org_unit_id', 'child_of', org_units.ids))
        
        candidates = self.search(domain)
        if target_year:
            target_plans = self.search([
                ('plan_year_id', '=', target_year.id),
                ('state', 'not in', ['superseded', 'revised']),
                ('doctor_user_id', '!=', False)
            ])
            excluded_doctors = target_plans.mapped('doctor_user_id.id')
            candidates = candidates.filtered(
                lambda p: not p.doctor_user_id or p.doctor_user_id.id not in excluded_doctors
            )
        return candidates

    def _rollover_plans(self, source_year, target_year, org_units=None, only_signed=True):
        """Clone _get_rollover_candidates(source_year, ...) as fresh drafts in
        target_year. Rollover clones are independent drafts - no
        previous_plan_id is set, since rollover is a new-year restart, not an
        in-year revision of a signed plan. Returns the new plans."""
        new_plans = self.browse()
        for plan in self._get_rollover_candidates(source_year, org_units, only_signed, target_year):
            new_plans |= plan.with_context(nhs_jobplan_skip_year_state_check=True).copy({
                'reference': 'New',
                'plan_year_id': target_year.id,
                'state': 'draft',
                'previous_plan_id': False,
                'revision_number': 1,
                'superseded_by_id': False,
                'doctor_signed_at': False,
                'doctor_signed_by': False,
                'manager_signed_at': False,
                'manager_signed_by': False,
                'proposed_by': False,
            })
        return new_plans

    @api.model
    def _cron_remind_plans_due(self):
        """Scheduled action: chatter/email reminders for plans approaching
        their review due date and unsigned, and for plans stalled in
        proposed/in_discussion beyond the company's staleness threshold."""
        today = fields.Date.context_today(self)
        template = self.env.ref(
            'odoo_nhs_job_planning.mail_template_job_plan_reminder', raise_if_not_found=False)
        due_plans = self.search([
            ('state', 'not in', list(LOCKED_STATES) + ['superseded']),
            ('review_due_date', '!=', False),
            ('review_due_date', '>=', today),
        ])
        for plan in due_plans:
            days_out = (plan.review_due_date - today).days
            if days_out in (60, 30, 14, 7, 1):
                plan.message_post(
                    body="Annual review due in %d day(s) (%s) and this job plan"
                         " is not yet signed." % (days_out, plan.review_due_date))
                if template:
                    template.send_mail(plan.id, force_send=False)

        stalled = self.search([('state', 'in', ('proposed', 'in_discussion'))])
        for plan in stalled:
            threshold = plan.company_id.nhs_jobplan_stale_discussion_days or 21
            last_change = plan.write_date.date() if plan.write_date else today
            if (today - last_change).days >= threshold:
                plan.message_post(
                    body="This job plan has been '%s' for %d+ day(s) without"
                         " progressing." % (dict(STATES).get(plan.state), threshold))
