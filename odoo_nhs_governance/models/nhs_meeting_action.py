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
#    You should have received a copy of the GNU LESSER PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models
from odoo.exceptions import UserError


class NhsMeetingAction(models.Model):
    _name = 'nhs.meeting.action'
    _description = 'Meeting Action (reuses the CAPA action pattern for governance actions)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, id'

    name = fields.Char(string='Action Description', required=True, help='The action description.')
    reference = fields.Char(string='Reference', readonly=True, copy=False, default='New',
                            help='Auto-generated unique reference (e.g. GOV-ACT/2026/00001).')
    meeting_id = fields.Many2one('nhs.meeting', string='Source Meeting', ondelete='cascade',
                                 help='The meeting this action was raised from, if raised at a meeting.')
    baf_risk_id = fields.Many2one('nhs.baf.risk', string='BAF Gap', ondelete='cascade',
                                  help='The BAF principal risk this action closes a control/assurance '
                                       'gap for, if raised directly from a BAF review rather than a meeting.')
    committee_id = fields.Many2one('nhs.committee', string='Committee', compute='_compute_committee_id',
                                   store=True, help='For the committee action log.')
    agenda_item_id = fields.Many2one('nhs.agenda.item', string='Source Item',
                                     domain="[('meeting_id', '=', meeting_id)]",
                                     help='The agenda item this action arose from.')
    owner_id = fields.Many2one('res.users', string='Owner', required=True,
                               default=lambda self: self.env.user, tracking=True,
                               help='The person responsible for completing this action.')
    due_date = fields.Date(string='Due Date', required=True, tracking=True, help='Deadline for this action.')
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    ], string='Status', default='open', required=True, tracking=True,
       help='Open / In Progress / Completed / Overdue. The Overdue state is set '
            'automatically by the daily escalation cron once the due date passes.')
    completion_note = fields.Text(string='Completion Note', help='How this action was closed.')
    reported_meeting_id = fields.Many2one('nhs.meeting', string='Reported To Meeting',
                                          help='The meeting where completion of this action was reported '
                                               '(matters arising).')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company,
                                 help='The company this governance action belongs to.')

    @api.constrains('meeting_id', 'baf_risk_id')
    def _check_parent(self):
        """Ensure every action is linked to a meeting or a BAF gap."""
        for rec in self:
            if not rec.meeting_id and not rec.baf_risk_id:
                raise UserError('A governance action must be linked to either a meeting or a BAF gap.')

    @api.depends('meeting_id.committee_id', 'baf_risk_id.owning_committee_id')
    def _compute_committee_id(self):
        """Derive the owning committee from the source meeting or BAF risk."""
        for rec in self:
            rec.committee_id = rec.meeting_id.committee_id or rec.baf_risk_id.owning_committee_id

    @api.model_create_multi
    def create(self, vals_list):
        """Assign a sequence reference and schedule an owner activity for new actions."""
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = seq.next_by_code('nhs.meeting.action') or 'New'
        records = super().create(vals_list)
        records._check_parent()
        template = self.env.ref('odoo_nhs_governance.mail_template_action_assigned', raise_if_not_found=False)
        for rec in records:
            rec.activity_schedule('mail.mail_activity_data_todo', user_id=rec.owner_id.id,
                                  note=f'Governance action assigned: {rec.name}')
            if template and rec.owner_id.email:
                template.send_mail(rec.id, force_send=False)
        return records

    def action_start(self):
        """Mark this action as in progress."""
        self.write({'state': 'in_progress'})

    def action_complete(self):
        """Mark this action as completed, requiring a completion note first."""
        for rec in self:
            if not rec.completion_note:
                raise UserError('Please enter a completion note before marking this action complete.')
        self.write({'state': 'completed'})

    def action_report_to_next_meeting(self):
        """Link this action to the next scheduled meeting of its committee."""
        for rec in self:
            if not rec.meeting_id or not rec.committee_id:
                raise UserError('This action has no source meeting/committee to report against.')
            next_meeting = self.env['nhs.meeting'].search([
                ('committee_id', '=', rec.committee_id.id),
                ('meeting_date', '>', rec.meeting_id.meeting_date),
                ('state', 'not in', ['cancelled']),
            ], order='meeting_date', limit=1)
            if not next_meeting:
                raise UserError(
                    'No future meeting was found for "%s" to report this action to. '
                    'Schedule the next meeting first.' % rec.committee_id.name
                )
            rec.reported_meeting_id = next_meeting.id

    @api.model
    def _cron_action_escalation(self):
        """Overdue-action escalation to the committee chair / secretary."""
        today = fields.Date.today()
        actions = self.search([
            ('state', '!=', 'completed'),
            ('due_date', '<', today),
        ])
        for action in actions:
            days_over = (today - action.due_date).days
            if action.state != 'overdue':
                action.state = 'overdue'
            recipients = action.committee_id.member_ids.filtered(
                lambda m: m.role in ('chair', 'secretary')).mapped('user_id')
            for user in recipients or action.owner_id:
                action.activity_schedule(
                    'mail.mail_activity_data_todo', user_id=user.id,
                    note=f'Governance action OVERDUE by {days_over} days: {action.name}')
