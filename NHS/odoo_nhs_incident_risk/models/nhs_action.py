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
    """Corrective, preventive, or improvement action raised from an incident,
    investigation, or risk register entry."""
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
        """Assign a sequence-based reference and schedule an owner reminder for new actions."""
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
        """Pre-fill investigation_id/risk_id from the parent record's own links when creating in context."""
        res = super().default_get(fields_list)
        # Auto-fill investigation_id when creating from an incident context that already
        # has a linked investigation — _check_single_parent allows incident + investigation
        # together as long as they're consistent, so this is a safe, expected default.
        incident_id = res.get('incident_id') or self.env.context.get('default_incident_id')
        if incident_id and not res.get('investigation_id'):
            incident = self.env['nhs.incident'].browse(incident_id)
            if incident.investigation_id:
                res['investigation_id'] = incident.investigation_id.id
        # Auto-fill risk_id when creating from an investigation context
        inv_id = res.get('investigation_id') or self.env.context.get('default_investigation_id')
        if inv_id and not res.get('risk_id'):
            investigation = self.env['nhs.investigation'].browse(inv_id)
            incident = investigation.incident_id
            if incident and incident.risk_ids:
                res['risk_id'] = incident.risk_ids[0].id
        # Auto-fill incident_id/investigation_id when creating from a risk context, but only
        # when the risk has exactly one evidence incident (unambiguous) and that incident has
        # a linked investigation — satisfies the incident+investigation+risk exception in
        # _check_single_parent; a risk with zero or several evidence incidents, or one with
        # no investigation, is left alone rather than guessing.
        risk_id = res.get('risk_id') or self.env.context.get('default_risk_id')
        if risk_id and not res.get('incident_id') and not res.get('investigation_id'):
            risk = self.env['nhs.risk'].browse(risk_id)
            if len(risk.incident_ids) == 1 and risk.incident_ids.investigation_id:
                res['incident_id'] = risk.incident_ids.id
                res['investigation_id'] = risk.incident_ids.investigation_id.id
        return res

    @api.onchange('incident_id')
    def _onchange_incident_id(self):
        """Pre-fill investigation_id as soon as incident_id has a value with a linked investigation.

        Covers the "Add a line" flow on the incident form's embedded Actions list, where
        incident_id is set via the one2many relation itself rather than a default_incident_id
        context key, so default_get() above never sees it.
        """
        if self.incident_id and not self.investigation_id and self.incident_id.investigation_id:
            self.investigation_id = self.incident_id.investigation_id

    @api.onchange('risk_id')
    def _onchange_risk_id(self):
        """Pre-fill incident_id/investigation_id from the risk's evidence incident, covering the
        "Add a line" flow on the risk form's embedded Actions list (see default_get for the
        same rule and why it only applies when the risk has exactly one evidence incident)."""
        if self.risk_id and not self.incident_id and not self.investigation_id:
            incidents = self.risk_id.incident_ids
            if len(incidents) == 1 and incidents.investigation_id:
                self.incident_id = incidents
                self.investigation_id = incidents.investigation_id

    @api.constrains('incident_id', 'investigation_id', 'risk_id')
    def _check_single_parent(self):
        """Ensure an action is linked to at most one parent record (incident, investigation, or risk)."""
        for rec in self:
            # incident + investigation (no risk): allowed if investigation belongs to that incident
            if rec.incident_id and rec.investigation_id and not rec.risk_id:
                if rec.investigation_id.incident_id == rec.incident_id:
                    continue
            # incident + investigation + risk: allowed when all three form a consistent chain
            if rec.incident_id and rec.investigation_id and rec.risk_id:
                if (rec.investigation_id.incident_id == rec.incident_id
                        and rec.risk_id in rec.incident_id.risk_ids):
                    continue
            parents = bool(rec.incident_id) + bool(rec.investigation_id) + bool(rec.risk_id)
            if parents > 1:
                raise ValidationError('An action can only be linked to one parent record.')

    def action_start(self):
        """Move the action to the In Progress state."""
        self.write({'state': 'in_progress'})

    def action_submit_evidence(self):
        """Submit completion evidence and move the action to Evidence Review."""
        for rec in self:
            if not rec.completion_evidence:
                raise UserError('Please enter completion evidence before submitting for review.')
            rec.write({'state': 'evidence_review'})

    def action_verify(self):
        """Mark the action done, record verification details, and schedule an
        effectiveness check activity if one was requested."""
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
        """Cancel the action."""
        self.write({'state': 'cancelled'})

    def write(self, vals):
        """Require completion evidence before allowing a transition to Evidence Review."""
        if 'state' in vals:
            for rec in self:
                new_state = vals['state']
                if new_state == 'evidence_review' and not (
                        vals.get('completion_evidence') or rec.completion_evidence):
                    raise UserError('Completion evidence is required before evidence review.')
        return super().write(vals)

    @api.model
    def _cron_action_escalation(self):
        """Notify owners of actions that are overdue or due within 3 days."""
        today = fields.Date.today()
        warn_date = today + timedelta(days=3)
        actions = self.search([
            ('state', 'not in', ['done', 'cancelled']),
            ('due_date', '<=', warn_date),
        ])
        template = self.env.ref(
            'odoo_nhs_incident_risk.mail_template_action_overdue', raise_if_not_found=False)
        for action in actions:
            if not action.due_date:
                continue
            days_over = (today - action.due_date).days
            if days_over > 0:
                action.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=action.owner_id.id,
                    note=f'Action OVERDUE by {days_over} days: {action.name}')
                if template and action.owner_id.email:
                    template.send_mail(action.id, force_send=True)
