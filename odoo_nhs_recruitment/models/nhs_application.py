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
        'nhs.vacancy', string='Vacancy', required=True, ondelete='restrict', tracking=True)
    candidate_id = fields.Many2one(
        'nhs.candidate', string='Candidate', required=True, ondelete='restrict', tracking=True)
    source = fields.Selection([
        ('portal', 'Public Portal'),
        ('internal', 'Internal'),
    ], string='Source', default='portal', required=True)
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
        string='Shortlist Score', compute='_compute_shortlist_score', store=True)
    shortlist_outcome = fields.Selection([
        ('shortlisted', 'Shortlisted'),
        ('not_shortlisted', 'Not Shortlisted'),
        ('hold', 'Hold'),
    ], string='Shortlist Outcome', tracking=True)
    shortlist_reason = fields.Text(string='Shortlist Reason')
    interview_ids = fields.One2many('nhs.interview', 'application_id', string='Interviews')
    interview_count = fields.Integer(string='Interview Count', compute='_compute_interview_count')
    offer_id = fields.Many2one('nhs.offer', string='Offer', readonly=True, copy=False)
    equality_id = fields.Many2one(
        'nhs.equality.monitoring', string='Equality Monitoring', copy=False,
        help="Segregated equality & diversity record — never shown on this form"
             " or visible to the selection panel."
    )
    acknowledged = fields.Boolean(string='Acknowledged', readonly=True)
    active = fields.Boolean(string='Active', default=True)

    _vacancy_candidate_uniq = models.Constraint(
        'unique(vacancy_id, candidate_id)',
        'This candidate has already applied to this vacancy.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'nhs.application') or 'New'
        applications = super().create(vals_list)
        for application in applications:
            if not application.equality_id:
                application.equality_id = self.env['nhs.equality.monitoring'].create({
                    'application_id': application.id,
                })
        return applications

    def _compute_duplicate_warning(self):
        for application in self:
            application.duplicate_warning = bool(application.candidate_id) and bool(
                self.search_count([
                    ('vacancy_id', '=', application.vacancy_id.id),
                    ('candidate_id', '=', application.candidate_id.id),
                    ('id', '!=', application.id),
                ]))

    @api.depends('score_line_ids.score', 'score_line_ids.criterion_id.weight')
    def _compute_shortlist_score(self):
        for application in self:
            lines = application.score_line_ids
            total_weight = sum(lines.mapped('criterion_id.weight'))
            if total_weight:
                application.shortlist_score = sum(
                    line.score * line.criterion_id.weight for line in lines) / total_weight
            else:
                application.shortlist_score = 0.0

    def _compute_interview_count(self):
        for application in self:
            application.interview_count = len(application.interview_ids)

    def action_start_shortlisting(self):
        for application in self:
            if application.stage != 'received':
                raise UserError(_('Only received applications can start shortlisting.'))
        self.write({'stage': 'shortlisting'})

    def action_shortlist_decide(self):
        """Apply the recorded shortlist_outcome to the pipeline stage."""
        today = fields.Date.context_today(self)
        for application in self:
            if not application.shortlist_outcome:
                raise UserError(_('Set a shortlist outcome before deciding.'))
            if application.shortlist_outcome == 'shortlisted':
                application.stage = 'shortlisted'
                application.vacancy_id.action_mark_in_progress()
            elif application.shortlist_outcome == 'not_shortlisted':
                application.write({'stage': 'rejected', 'decision_date': today})

    def action_reject(self):
        today = fields.Date.context_today(self)
        self.write({'stage': 'rejected', 'decision_date': today})

    def action_withdraw(self):
        today = fields.Date.context_today(self)
        self.write({'stage': 'withdrawn', 'decision_date': today})

    def action_make_offer(self):
        self.ensure_one()
        if self.stage != 'interview':
            raise UserError(_('An offer can only be made from the Interview stage.'))
        if self.offer_id:
            raise UserError(_('This application already has an offer.'))
        offer = self.env['nhs.offer'].create({'application_id': self.id})
        self.write({'stage': 'offered', 'offer_id': offer.id})
        return {
            'name': _('Offer'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.offer',
            'view_mode': 'form',
            'res_id': offer.id,
        }

    def action_send_acknowledgement(self):
        template = self.env.ref(
            'odoo_nhs_recruitment.mail_template_application_ack', raise_if_not_found=False)
        for application in self:
            if template and application.candidate_id.email:
                template.send_mail(application.id, force_send=True)
            application.acknowledged = True

    @api.constrains('shortlist_outcome')
    def _check_shortlist_outcome_reason(self):
        for application in self:
            if application.shortlist_outcome == 'not_shortlisted' and not application.shortlist_reason:
                raise ValidationError(_(
                    'A reason is required when an application is not shortlisted.'))
