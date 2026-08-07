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
from odoo import  _, api, fields, models
from odoo.exceptions import ValidationError


class NhsInterviewScoreLine(models.Model):
    """A single panellist's score against one person-spec criterion."""
    _name = 'nhs.interview.score.line'
    _description = 'Interview score line'
    _order = 'id'

    interview_id = fields.Many2one(
        'nhs.interview', string='Interview', required=True, ondelete='cascade', index=True)
    criterion_id = fields.Many2one(
        'nhs.person.spec.criterion', string='Criterion', required=True)
    panellist_id = fields.Many2one('res.users', string='Panellist', required=True)
    score = fields.Float(string='Score', help="0 (not met) to 5 (fully met).")
    notes = fields.Char(string='Notes')

    @api.constrains('criterion_id', 'interview_id')
    def _check_criterion_matches_vacancy_spec(self):
        """Panel scoring is only meaningful against the vacancy's own person
        specification — enforced here so it holds even if a score line is
        created another way than the view's (now-filtered) picker."""
        for line in self:
            vacancy = line.interview_id.vacancy_id
            spec = vacancy.person_spec_id
            if not spec:
                raise ValidationError(_(
                    "Set a Person Specification on vacancy '%s' before scoring "
                    "interviews against it.") % vacancy.name)
            if line.criterion_id.spec_id != spec:
                raise ValidationError(_(
                    "'%s' is not a criterion of this vacancy's Person Specification "
                    "('%s').") % (line.criterion_id.name, spec.name))


class NhsInterview(models.Model):
    """An interview event for a shortlisted application: panel, schedule,
    per-criterion per-panellist scoring, outcome and ranking."""
    _name = 'nhs.interview'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Interview'
    _order = 'interview_datetime'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True, default='New')
    company_id = fields.Many2one(
        related='vacancy_id.company_id', string='Company', store=True, readonly=True)
    vacancy_id = fields.Many2one(
        related='application_id.vacancy_id', string='Vacancy', store=True, readonly=True)
    person_spec_id = fields.Many2one(
        related='vacancy_id.person_spec_id', string='Person Specification', readonly=True,
        help="The vacancy's person specification — panel scores are recorded"
             " only against this template's criteria.")
    application_id = fields.Many2one(
        'nhs.application', string='Application', required=True, ondelete='cascade', tracking=True)
    interview_datetime = fields.Datetime(string='Date & Time', required=True, tracking=True)
    location = fields.Char(string='Location / Virtual Link')
    panel_ids = fields.Many2many('res.users', string='Panel Members')
    invite_status = fields.Selection([
        ('invited', 'Invited'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('rescheduled', 'Rescheduled'),
        ('attended', 'Attended'),
        ('no_show', 'No Show'),
    ], string='Invite Status', default='invited', tracking=True)
    score_line_ids = fields.One2many(
        'nhs.interview.score.line', 'interview_id', string='Scores')
    total_score = fields.Float(
        string='Total Score', compute='_compute_total_score', store=True)
    outcome = fields.Selection([
        ('appointable', 'Appointable'),
        ('not_appointable', 'Not Appointable'),
        ('hold', 'Hold'),
        ('reserve', 'Reserve'),
    ], string='Outcome', tracking=True)
    rank = fields.Integer(string='Rank')
    notes = fields.Text(string='Panel Notes')
    active = fields.Boolean(string='Active', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Assigns each interview its sequence reference and advances the
        linked application into the interview stage."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'nhs.interview') or 'New'
        interviews = super().create(vals_list)
        for interview in interviews:
            if interview.application_id.stage in ('shortlisted', 'shortlisting'):
                interview.application_id.stage = 'interview'
        return interviews

    @api.depends('score_line_ids.score', 'score_line_ids.criterion_id.weight')
    def _compute_total_score(self):
        """Weighted average of the panel's score lines against the person
        specification's criterion weights."""
        for interview in self:
            lines = interview.score_line_ids
            total_weight = sum(lines.mapped('criterion_id.weight'))
            if total_weight:
                interview.total_score = sum(
                    line.score * line.criterion_id.weight for line in lines) / total_weight
            else:
                interview.total_score = 0.0

    def action_mark_accepted(self):
        """Records that the candidate accepted the interview invite."""
        self.write({'invite_status': 'accepted'})

    def action_mark_declined(self):
        """Records that the candidate declined the interview invite."""
        self.write({'invite_status': 'declined'})

    def action_mark_rescheduled(self):
        """Opens a wizard to capture the new date/time (and optionally a new
        location) before flagging the invite as rescheduled — so the old
        slot is never left in place by mistake."""
        self.ensure_one()
        return {
            'name': _('Reschedule Interview'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.interview.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_interview_id': self.id,
                'default_new_datetime': self.interview_datetime,
                'default_new_location': self.location,
            },
        }

    def action_mark_attended(self):
        """Records that the candidate attended the interview."""
        self.write({'invite_status': 'attended'})

    def action_mark_no_show(self):
        """Records that the candidate failed to attend the interview."""
        self.write({'invite_status': 'no_show'})

    def action_mark_appointable(self):
        """Records the panel's verdict that the candidate is appointable."""
        self.write({'outcome': 'appointable'})

    def action_mark_not_appointable(self):
        """Records the panel's verdict as not appointable, and rejects the
        application once none of its interviews remain appointable or
        undecided."""
        self.write({'outcome': 'not_appointable'})
        for interview in self:
            if not interview.application_id.interview_ids.filtered(
                    lambda i: i.outcome in ('appointable', False)):
                interview.application_id.action_reject()

    def action_view_application(self):
        """Opens the interview's parent application form."""
        self.ensure_one()
        return {
            'name': ('Application'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.application',
            'view_mode': 'form',
            'res_id': self.application_id.id,
        }
