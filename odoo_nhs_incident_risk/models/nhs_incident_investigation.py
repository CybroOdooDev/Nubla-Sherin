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


class NhsInvestigation(models.Model):
    _name = 'nhs.investigation'
    _description = 'Investigation / Learning Response (PSIRF-aligned)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, readonly=True,
                       copy=False, default='New',
                       help='Auto-generated unique reference for this investigation (e.g. INV/2026/00001).')
    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='restrict',
                                  help='The patient safety incident this investigation was opened against.')
    response_level = fields.Selection([
        ('swarm', 'SWARM Huddle'),
        ('aar', 'After Action Review'),
        ('mdt_review', 'MDT Review'),
        ('psii', 'PSII — Patient Safety Incident Investigation'),
    ], string='Response Level', required=True, tracking=True,
       help='The PSIRF learning response type: SWARM for a rapid debrief, AAR for a structured review, '
            'MDT Review for multidisciplinary input, or PSII for a formal patient safety incident investigation.')
    lead_investigator_id = fields.Many2one('res.users', string='Lead Investigator',
                                           required=True, tracking=True,
                                           help='The person responsible for leading and coordinating the investigation.')
    team_member_ids = fields.Many2many('res.users', string='Team Members / Panel',
                                       help='Additional investigators, clinicians, or panel members involved in the review.')
    terms_of_reference = fields.Text(string='Terms of Reference',
                                     help='Required for PSII-level investigations. '
                                          'Defines the scope, objectives, methodology, and boundaries of the investigation.')
    timeline_ids = fields.One2many('nhs.investigation.timeline', 'investigation_id',
                                   string='Chronology',
                                   help='A sequential log of events and actions leading up to and following the incident.')
    contributing_factor_ids = fields.Many2many('nhs.contributing.factor',
                                               string='Contributing Factors',
                                               help='Factors from the Yorkshire Contributory Factors Framework that '
                                                    'contributed to the incident (e.g. task factors, team factors, environment).')
    findings = fields.Text(string='Findings',
                           help='The key findings from the investigation — what happened, why, and the immediate causes.')
    lessons_learned = fields.Text(string='Lessons Learned',
                                  help='Learning points identified that should be shared across the organisation '
                                       'to prevent recurrence.')
    good_practice = fields.Text(string='Areas of Good Practice',
                                help='Positive practice identified during the investigation that should be recognised and shared.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted for Approval'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', required=True, tracking=True,
       help='The current stage of the investigation workflow.')
    approved_by_id = fields.Many2one('res.users', string='Approved By',
                                     help='The Quality Lead who approved this investigation report.')
    approved_at = fields.Datetime(string='Approved At',
                                  help='The date and time the investigation report was formally approved.')
    action_ids = fields.One2many('nhs.action', 'investigation_id', string='Actions',
                                 help='Corrective and preventive actions arising from this investigation.')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help='The organisation this investigation belongs to.')

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('nhs.investigation') or 'New'
        return super().create(vals_list)

    @api.constrains('response_level', 'terms_of_reference')
    def _check_psii_tor(self):
        for rec in self:
            if rec.response_level == 'psii' and rec.state != 'draft' \
               and not rec.terms_of_reference:
                raise ValidationError('Terms of Reference are required for PSII investigations.')

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_submit(self):
        for rec in self:
            if rec.response_level == 'psii' and not rec.terms_of_reference:
                raise UserError('Terms of Reference must be completed before submission.')
            if not rec.findings:
                raise UserError('Findings must be recorded before submission.')
        self.write({'state': 'submitted'})

    def action_approve(self):
        if not self.env.user.has_group(
                'odoo_nhs_incident_risk.group_hc_quality_lead'):
            raise UserError('Only Quality Lead users can approve investigations.')
        for rec in self:
            open_actions = rec.action_ids.filtered(
                lambda a: a.state not in ('done', 'cancelled')
            )
            if open_actions:
                titles = ', '.join(open_actions.mapped('name'))
                raise UserError(
                    f'Cannot approve: {len(open_actions)} action(s) must be '
                    f'completed or cancelled before approving this investigation.\n'
                    f'Pending: {titles}'
                )
        self.write({
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approved_at': fields.Datetime.now(),
        })
        for rec in self:
            if rec.incident_id and rec.incident_id.state == 'investigation':
                rec.incident_id.with_context(nhs_workflow=True).write(
                    {'state': 'actions'}
                )

    def action_rework(self):
        self.write({'state': 'in_progress'})

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref(
            'odoo_nhs_incident_risk.action_report_investigation_summary'
        ).report_action(self)
