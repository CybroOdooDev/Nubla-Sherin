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

APPLICATION_STAGES = [
    ('received', 'Received'),
    ('shortlisting', 'Shortlisting'),
    ('shortlisted', 'Shortlisted'),
    ('interview', 'Interview'),
    ('offered', 'Offered'),
    ('hired', 'Hired'),
    ('rejected', 'Rejected'),
    ('withdrawn', 'Withdrawn'),
]


class NhsApplicationScoreLine(models.Model):
    """A single criterion score recorded during shortlisting."""
    _name = 'nhs.application.score.line'
    _description = 'Shortlisting score line'
    _order = 'id'

    application_id = fields.Many2one(
        'nhs.application', string='Application', required=True, ondelete='cascade', index=True)
    criterion_id = fields.Many2one(
        'nhs.person.spec.criterion', string='Criterion', required=True)
    score = fields.Float(string='Score', help="0 (not met) to 5 (fully met).")
    notes = fields.Char(string='Notes')

    @api.constrains('criterion_id', 'application_id')
    def _check_criterion_matches_vacancy_spec(self):
        """Scoring is only meaningful against the vacancy's own person
        specification — enforced here so it holds even if a score line is
        created another way than the view's (now-filtered) picker."""
        for line in self:
            vacancy = line.application_id.vacancy_id
            spec = vacancy.person_spec_id
            if not spec:
                raise ValidationError((
                    "Set a Person Specification on vacancy '%s' before scoring "
                    "applications against it.") % vacancy.name)
            if line.criterion_id.spec_id != spec:
                raise ValidationError((
                    "'%s' is not a criterion of this vacancy's Person Specification "
                    "('%s').") % (line.criterion_id.name, spec.name))


class NhsApplication(models.Model):
    """A candidate's application to a vacancy — the recruiter's pipeline
    spine (received → shortlisting → shortlisted → interview → offered →
    hired), scored against the vacancy's person specification."""
    _name = 'nhs.application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "A candidate's application to a vacancy"
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, default='New')
    company_id = fields.Many2one(
        related='vacancy_id.company_id', string='Company', store=True, readonly=True)
    vacancy_id = fields.Many2one(
        'nhs.vacancy', string='Vacancy', required=True, ondelete='restrict', tracking=True,
        domain="[('state', 'in', ('open', 'in_progress'))]")
    person_spec_id = fields.Many2one(
        related='vacancy_id.person_spec_id', string='Person Specification', readonly=True,
        help="The vacancy's person specification — shortlisting scores are recorded"
             " only against this template's criteria.")
    candidate_id = fields.Many2one(
        'nhs.candidate', string='Candidate', required=True, ondelete='restrict', tracking=True)
    source = fields.Selection([
        ('portal', 'Public Portal'),
        ('internal', 'Internal'),
    ], string='Source', default='internal', required=True)
    supporting_statement = fields.Text(string='Supporting Statement')
    cv_attachment_ids = fields.Many2many('ir.attachment', string='CV / Documents')
    employment_history = fields.Text(string='Employment History')
    right_to_work_flagged = fields.Boolean(
        string='Right to Work — Flag for Review',
        help="Eligibility pre-screen: candidate indicated a possible right-to-work concern."
    )
    registration_flagged = fields.Boolean(
        string='Professional Registration — Flag for Review',
        help="Eligibility pre-screen: candidate indicated a possible registration concern."
    )
    stage = fields.Selection(
        APPLICATION_STAGES, string='Stage', default='received', required=True, tracking=True)
    rejection_reason = fields.Text(string='Rejection / Withdrawal Reason')
    decision_date = fields.Date(
        string='Decision Date',
        readonly=True,
        help="Date the application reached a final (unsuccessful) outcome;"
             " starts the unsuccessful-applicant retention clock."
    )
    duplicate_warning = fields.Boolean(
        string='Possible Duplicate', compute='_compute_duplicate_warning')
    score_line_ids = fields.One2many(
        'nhs.application.score.line', 'application_id', string='Shortlisting Scores')
    shortlist_score = fields.Float(
        string='Shortlist Score', compute='_compute_shortlist_score', store=True,
        help="Sum of each shortlisting score line's score x its criterion's weight"
             " (e.g. (5x3)+(4x2)+(3x1) = 26). Not normalised, so it is not on a 0-5"
             " scale — it grows with the number of criteria and their weights.")
    shortlist_outcome = fields.Selection([
        ('shortlisted', 'Shortlisted'),
        ('not_shortlisted', 'Not Shortlisted'),
        ('hold', 'Hold'),
    ], string='Shortlist Outcome', tracking=True)
    shortlist_reason = fields.Text(string='Shortlist Reason')
    interview_ids = fields.One2many('nhs.interview', 'application_id', string='Interviews')
    interview_count = fields.Integer(string='Interview Count', compute='_compute_interview_count')
    has_appointable_interview = fields.Boolean(
        string='Has Appointable Interview', compute='_compute_has_appointable_interview',
        help="At least one of this application's interviews recorded an Appointable"
             " outcome — required before an offer can be made.")
    offer_id = fields.Many2one('nhs.offer', string='Offer', readonly=True, copy=False)
    equality_id = fields.Many2one(
        'nhs.equality.monitoring', string='Equality Monitoring', copy=False,
        help="Segregated equality & diversity record — never shown on this form"
             " or visible to the selection panel."
    )
    equality_age_band = fields.Selection(
        related='equality_id.age_band', string='Age Band', readonly=False)
    equality_ethnicity = fields.Selection(
        related='equality_id.ethnicity', string='Ethnicity', readonly=False)
    equality_disability = fields.Selection(
        related='equality_id.disability', string='Disability', readonly=False)
    equality_sex = fields.Selection(
        related='equality_id.sex', string='Sex', readonly=False)
    equality_religion = fields.Char(
        related='equality_id.religion', string='Religion / Belief', readonly=False)
    equality_sexual_orientation = fields.Char(
        related='equality_id.sexual_orientation', string='Sexual Orientation', readonly=False)
    acknowledged = fields.Boolean(string='Acknowledged', readonly=True)
    active = fields.Boolean(string='Active', default=True)

    _vacancy_candidate_uniq = models.Constraint(
        'unique(vacancy_id, candidate_id)',
        'This candidate has already applied to this vacancy.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Assigns each application its sequence reference and creates its
        segregated equality-monitoring record, kept off the main form.

        Also re-checks each vacancy is actually open for applications: the
        vacancy_id field's UI domain only filters the picker, so it does
        nothing when a vacancy is pre-filled via context (e.g. the "+" on
        the vacancy's own Applications kanban, or the public portal submit
        route) — this is the one place every creation path passes through,
        so it's enforced here rather than relying on the domain alone."""
        vacancy_ids = {vals['vacancy_id'] for vals in vals_list if vals.get('vacancy_id')}
        if vacancy_ids:
            for vacancy in self.env['nhs.vacancy'].browse(vacancy_ids):
                if vacancy.state not in ('open', 'in_progress'):
                    state_label = dict(
                        vacancy._fields['state'].selection).get(vacancy.state, vacancy.state)
                    raise UserError((
                        "'%s' is not open for applications (status: %s)."
                    ) % (vacancy.name, state_label))
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'nhs.application') or 'New'
        applications = super().create(vals_list)
        for application in applications:
            if not application.equality_id:
                application.equality_id = self.env['nhs.equality.monitoring'].sudo().create({
                    'application_id': application.id,
                })
        return applications

    duplicate_warning_message = fields.Char(
        string='Warning Message', compute='_compute_duplicate_warning')

    @api.depends('vacancy_id', 'candidate_id')
    def _compute_duplicate_warning(self):
        """Flags whether this candidate has another application against
        the same vacancy, or any other vacancy if the setting is enabled."""
        for application in self:
            domain = [('candidate_id', '=', application.candidate_id.id)]
            
            warn_multiple = self.env.company.nhs_recruit_warn_multiple_applications
            if not warn_multiple:
                domain.append(('vacancy_id', '=', application.vacancy_id.id))
                
            if application._origin.id:
                domain.append(('id', '!=', application._origin.id))
                
            has_duplicate = bool(application.candidate_id) and bool(self.search_count(domain))
            application.duplicate_warning = has_duplicate
            
            if has_duplicate:
                if warn_multiple:
                    application.duplicate_warning_message = "This candidate has multiple applications in the system."
                else:
                    application.duplicate_warning_message = "This candidate has applied to this vacancy more than once."
            else:
                application.duplicate_warning_message = False

    @api.depends('score_line_ids.score', 'score_line_ids.criterion_id.weight')
    def _compute_shortlist_score(self):
        """Weighted sum of the shortlisting score lines against the person
        specification's criterion weights, e.g. (5x3)+(4x2)+(3x1) = 26."""
        for application in self:
            application.shortlist_score = sum(
                line.score * line.criterion_id.weight for line in application.score_line_ids)

    @api.depends('interview_ids')
    def _compute_interview_count(self):
        """Counts interviews linked to this application."""
        for application in self:
            application.interview_count = len(application.interview_ids)

    def action_view_interviews(self):
        """Opens the list of interviews for this application."""
        self.ensure_one()
        return {
            'name': 'Interviews',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.interview',
            'view_mode': 'list,form',
            'domain': [('application_id', '=', self.id)],
            'context': {'default_application_id': self.id},
        }

    @api.depends('interview_ids.outcome')
    def _compute_has_appointable_interview(self):
        """Whether any interview on this application has recorded an
        Appointable outcome — gates the Make Offer button."""
        for application in self:
            application.has_appointable_interview = bool(
                application.interview_ids.filtered(lambda i: i.outcome == 'appointable'))

    def action_start_shortlisting(self):
        """Moves a received application into shortlisting, or straight to
        interview if one has already been scheduled."""
        for application in self:
            if application.stage != 'received':
                raise UserError(('Only received applications can start shortlisting.'))
        for application in self:
            application.stage = 'interview' if application.interview_ids else 'shortlisting'

    def action_shortlist_decide(self):
        """Apply the recorded shortlist_outcome to the pipeline stage."""
        today = fields.Date.context_today(self)
        for application in self:
            if not application.shortlist_outcome:
                raise UserError(('Set a shortlist outcome before deciding.'))
            if application.shortlist_outcome == 'shortlisted':
                application.stage = 'interview' if application.interview_ids else 'shortlisted'
                application.vacancy_id.action_mark_in_progress()
            elif application.shortlist_outcome == 'not_shortlisted':
                application.write({'stage': 'rejected', 'decision_date': today})

    def action_reject(self):
        """Rejects the application and stamps the decision date, starting
        the unsuccessful-applicant retention clock."""
        today = fields.Date.context_today(self)
        self.write({'stage': 'rejected', 'decision_date': today})

    def action_withdraw(self):
        """Marks the application withdrawn by the candidate and stamps the
        decision date."""
        today = fields.Date.context_today(self)
        self.write({'stage': 'withdrawn', 'decision_date': today})

    def action_make_offer(self):
        """Creates the offer record for this application, advances it to
        the offered stage, and opens the new offer's form."""
        self.ensure_one()
        if self.stage != 'interview':
            raise UserError(('An offer can only be made from the Interview stage.'))
        if self.offer_id:
            raise UserError(('This application already has an offer.'))
        if not self.interview_ids.filtered(lambda i: i.outcome == 'appointable'):
            raise UserError((
                'An offer can only be made once an interview has recorded an'
                ' Appointable outcome.'))
        offer = self.env['nhs.offer'].create({'application_id': self.id})
        self.write({'stage': 'offered', 'offer_id': offer.id})
        return {
            'name': ('Offer'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.offer',
            'view_mode': 'form',
            'res_id': offer.id,
        }

    def action_send_acknowledgement(self):
        """Emails the candidate the acknowledgement template, if configured
        and an address is on file, and marks the application acknowledged
        regardless so it isn't retried."""
        template = self.env.ref(
            'odoo_nhs_recruitment.mail_template_application_ack', raise_if_not_found=False)
        for application in self:
            if template and application.candidate_id.email:
                template.send_mail(
                    application.id, 
                    force_send=True, 
                    email_values={'email_to': application.candidate_id.email}
                )
            application.acknowledged = True

    @api.constrains('shortlist_outcome')
    def _check_shortlist_outcome_reason(self):
        """Requires a reason whenever the shortlist outcome is negative,
        so rejections at this stage are always justified."""
        for application in self:
            if application.shortlist_outcome == 'not_shortlisted' and not application.shortlist_reason:
                raise ValidationError((
                    'A reason is required when an application is not shortlisted.'))

    @api.constrains('stage', 'offer_id', 'interview_ids')
    def _check_stage_progression(self):
        """Blocks the pipeline stage from being set ahead of the records
        that are supposed to justify it — closes the same class of bypass
        as directly clicking the statusbar past steps that normally only
        advance via the action_* methods (e.g. reaching 'hired' with no
        offer ever made, or 'interview' with no interview ever scheduled)."""
        for application in self:
            if application.stage in ('offered', 'hired') and not application.offer_id:
                raise ValidationError((
                    "An application can't be in stage '%s' without an offer record."
                ) % dict(application._fields['stage'].selection).get(application.stage))
            if application.stage == 'hired' and application.offer_id.state != 'hired':
                raise ValidationError((
                    'An application can only be Hired once its offer itself is Hired.'))
            if application.stage == 'interview' and not application.interview_ids:
                raise ValidationError((
                    "An application can't be in the Interview stage without an"
                    " interview scheduled."))
