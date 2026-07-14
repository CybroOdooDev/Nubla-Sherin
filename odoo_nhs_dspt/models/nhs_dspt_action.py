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


class NhsDsptAction(models.Model):
    _name = 'nhs.dspt.action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'DSPT Improvement Action (gap → action)'
    _order = 'target_date, id'

    name = fields.Char(
        string='Action',
        required=True,
        tracking=True,
        help="Action description."
    )
    reference = fields.Char(
        string='Reference',
        copy=False,
        readonly=True,
        default='New',
        help="Sequenced action reference."
    )
    assessment_id = fields.Many2one(
        'nhs.dspt.assessment',
        string='Assessment',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning assessment."
    )
    evidence_id = fields.Many2one(
        'nhs.dspt.evidence',
        string='Originating Gap',
        ondelete='set null',
        help="The evidence item this action closes."
    )
    assertion_id = fields.Many2one(
        'nhs.dspt.assertion',
        string='Assertion',
        related='evidence_id.assertion_id',
        store=True,
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        required=True,
        tracking=True,
        help="Responsible for closing this action."
    )
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority', default='medium')
    target_date = fields.Date(
        string='Target Date',
        required=True,
        tracking=True,
        help="Deadline; overdue escalation keys off this."
    )
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
    ], string='Status', required=True, default='open', tracking=True)
    completion_note = fields.Text(
        string='Completion Note',
        help="How the gap was closed."
    )
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_is_overdue',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='assessment_id.company_id',
        store=True,
    )

    @api.depends('target_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for action in self:
            action.is_overdue = bool(
                action.target_date and action.target_date < today
                and action.state not in ('completed', 'verified')
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'nhs.dspt.action') or 'New'
        return super().create(vals_list)

    def action_mark_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_mark_completed(self):
        self.write({'state': 'completed'})

    def action_mark_verified(self):
        self.write({'state': 'verified'})
        for action in self:
            if action.evidence_id and action.evidence_id.status == 'not_met':
                action.evidence_id.status = 'met'

    def action_reopen(self):
        self.write({'state': 'open'})

    @api.model
    def _cron_escalate_overdue(self):
        self.search([])._compute_is_overdue()
        overdue = self.search([('is_overdue', '=', True)])
        manager_group = self.env.ref('odoo_nhs_dspt.group_nhs_dspt_manager', raise_if_not_found=False)
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        for action in overdue:
            recipients = manager_group.users if manager_group else self.env['res.users']
            for user in recipients:
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'nhs.dspt.action'),
                    ('res_id', '=', action.id),
                    ('user_id', '=', user.id),
                    ('activity_type_id', '=', activity_type.id),
                ], limit=1)
                if not existing:
                    action.activity_schedule(
                        activity_type_id=activity_type.id,
                        user_id=user.id,
                        summary=('Overdue DSPT improvement action'),
                        note=('%s (owner: %s) was due %s and is still open.') % (
                            action.name, action.owner_id.name, action.target_date),
                    )
