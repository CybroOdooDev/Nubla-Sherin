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
from odoo.exceptions import ValidationError, UserError


class NhsAction(models.Model):
    _name = 'nhs.action'
    _description = 'Corrective / Preventive Action (CAPA)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, priority desc'

    name = fields.Char(string='Action Title', required=True,
                       help='A concise title for this action (e.g. "Update medication double-check SOP").')
    reference = fields.Char(string='Reference', readonly=True, copy=False, default='New',
                            help='Auto-generated unique reference for this action (e.g. ACT/2026/00001).')
    description = fields.Text(string='Description / Acceptance Criteria',
                               help='A clear description of what must be done and the measurable criteria '
                                    'that confirm the action is fully complete.')
    action_type = fields.Selection([
        ('corrective', 'Corrective'),
        ('preventive', 'Preventive'),
        ('improvement', 'Improvement'),
    ], string='Type', required=True, default='corrective',
       help='Corrective: addresses the immediate cause of an incident or risk. '
            'Preventive: prevents a similar event occurring in future. '
            'Improvement: enhances a process or system beyond baseline requirements.')
    incident_id = fields.Many2one('nhs.incident', string='Incident', ondelete='restrict',
                                  help='The incident this action was raised from. '
                                       'An action can only be linked to one parent record.')
    investigation_id = fields.Many2one('nhs.investigation', string='Investigation',
                                       ondelete='restrict',
                                       help='The investigation this action was raised from. '
                                            'An action can only be linked to one parent record.')
    risk_id = fields.Many2one('nhs.risk', string='Risk', ondelete='restrict',
                              help='The risk register entry this action was raised from. '
                                   'An action can only be linked to one parent record.')
    incident_risk_count = fields.Integer(related='incident_id.risk_count', store=False)
    owner_id = fields.Many2one('res.users', string='Owner', required=True,
                               default=lambda self: self.env.user, tracking=True,
                               help='The person responsible for completing this action by the due date. '
                                    'Receives an activity reminder when the action is created and escalation '
                                    'alerts when it is approaching or past its due date.')
    due_date = fields.Date(string='Due Date', required=True, tracking=True,
                           help='The date by which this action must be completed. '
                                'Overdue actions trigger automatic escalation alerts to the owner.')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority', default='medium',
       help='The urgency of this action. High priority actions should be monitored closely '
            'and reported in quality governance forums.')
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('evidence_review', 'Evidence Review'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='open', required=True, tracking=True,
       help='The current stage of this action: Open → In Progress → Evidence Review → Done. '
            'Completion evidence must be recorded before moving to Evidence Review.')
    cancellation_reason = fields.Text(string='Cancellation Reason',
                                      help='Required when cancelling an action. Explain why this action '
                                           'is no longer being pursued.')
    completion_evidence = fields.Text(string='Completion Evidence',
                                      help='Required before moving to Evidence Review.')
    verified_by_id = fields.Many2one('res.users', string='Verified By',
                                     help='The person who independently verified that this action has been '
                                          'completed to the required standard.')
    verified_at = fields.Datetime(string='Verified At',
                                  help='The date and time this action was formally verified as complete.')
    effectiveness_check = fields.Boolean(string='Schedule Effectiveness Check',
                                         help='When ticked, an activity is automatically scheduled after '
                                              'the specified number of days to verify whether the action '
                                              'has had the intended effect.')
    effectiveness_days = fields.Integer(string='Effectiveness Check Days', default=90,
                                        help='Number of days after completion to schedule the effectiveness '
                                             'check activity (default: 90 days).')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help='The organisation this action belongs to.')

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = seq.next_by_code('nhs.action') or 'New'
        records = super().create(vals_list)
        for rec in records:
            rec.activity_schedule('mail.mail_activity_data_todo',
                                  user_id=rec.owner_id.id,
                                  note=f'Action assigned: {rec.name}')
        return records

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Auto-fill from investigation context
        inv_id = res.get('investigation_id') or self.env.context.get('default_investigation_id')
        if inv_id and not res.get('risk_id'):
            investigation = self.env['nhs.investigation'].browse(inv_id)
            incident = investigation.incident_id
            if incident and incident.risk_ids:
                res['risk_id'] = incident.risk_ids[0].id
        # Auto-fill incident + investigation when creating from a risk context
        risk_id = res.get('risk_id') or self.env.context.get('default_risk_id')
        if risk_id and not res.get('incident_id'):
            risk = self.env['nhs.risk'].browse(risk_id)
            if risk.incident_ids:
                incident = risk.incident_ids[0]
                res['incident_id'] = incident.id
                if incident.investigation_id and not res.get('investigation_id'):
                    res['investigation_id'] = incident.investigation_id.id
        return res

    @api.onchange('risk_id')
    def _onchange_risk_id(self):
        if self.risk_id and self.risk_id.incident_ids:
            if not self.incident_id:
                incident = self.risk_id.incident_ids[0]
                self.incident_id = incident
                if incident.investigation_id and not self.investigation_id:
                    self.investigation_id = incident.investigation_id

    @api.onchange('investigation_id')
    def _onchange_investigation_id(self):
        if self.investigation_id and not self.incident_id:
            self.incident_id = self.investigation_id.incident_id

    @api.constrains('incident_id', 'investigation_id', 'risk_id')
    def _check_single_parent(self):
        for rec in self:
            # incident + investigation (no risk): allowed if investigation belongs to incident
            if rec.incident_id and rec.investigation_id and not rec.risk_id:
                if rec.investigation_id.incident_id == rec.incident_id:
                    continue
            # incident + risk (no investigation): allowed if risk is linked to incident
            if rec.incident_id and rec.risk_id and not rec.investigation_id:
                if rec.risk_id in rec.incident_id.risk_ids:
                    continue
            # all three: allowed when they form a consistent chain
            if rec.incident_id and rec.investigation_id and rec.risk_id:
                if (rec.investigation_id.incident_id == rec.incident_id
                        and rec.risk_id in rec.incident_id.risk_ids):
                    continue
            parents = bool(rec.incident_id) + bool(rec.investigation_id) + bool(rec.risk_id)
            if parents > 1:
                raise ValidationError('An action can only be linked to one parent record.')

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_submit_evidence(self):
        for rec in self:
            if not rec.completion_evidence:
                raise UserError('Please enter completion evidence before submitting for review.')
            rec.write({'state': 'evidence_review'})

    def action_verify(self):
        self.write({
            'state': 'done',
            'verified_by_id': self.env.user.id,
            'verified_at': fields.Datetime.now(),
        })
        for rec in self.filtered('effectiveness_check'):
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fields.Date.today() + \
                    timedelta(days=rec.effectiveness_days),
                user_id=rec.owner_id.id,
                note=f'Effectiveness check: {rec.name}',
            )

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def write(self, vals):
        if 'state' in vals:
            for rec in self:
                new_state = vals['state']
                if new_state == 'evidence_review' and not (
                        vals.get('completion_evidence') or rec.completion_evidence):
                    raise UserError('Completion evidence is required before evidence review.')
        return super().write(vals)

    @api.model
    def _cron_action_escalation(self):
        today = fields.Date.today()
        warn_date = today + timedelta(days=3)
        actions = self.search([
            ('state', 'not in', ['done', 'cancelled']),
            ('due_date', '<=', warn_date),
        ])
        for action in actions:
            if not action.due_date:
                continue
            days_over = (today - action.due_date).days
            if days_over > 0:
                action.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=action.owner_id.id,
                    note=f'Action OVERDUE by {days_over} days: {action.name}')
