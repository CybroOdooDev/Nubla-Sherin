# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NhsMeetingAction(models.Model):
    _name = 'nhs.meeting.action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'NHS Meeting Action'
    _order = 'due_date, id'

    name = fields.Char(required=True, tracking=True, help="Action description arising from a meeting or BAF gap.")
    reference = fields.Char(
        default='New',
        copy=False,
        readonly=True,
        help="Sequenced action reference used in the committee action log.",
    )
    meeting_id = fields.Many2one(
        'nhs.meeting',
        required=True,
        ondelete='cascade',
        help="Source meeting where the action was raised.",
    )
    committee_id = fields.Many2one(
        related='meeting_id.committee_id',
        store=True,
        help="Committee inherited from the source meeting for action-log grouping.",
    )
    company_id = fields.Many2one(
        related='meeting_id.company_id',
        store=True,
        help="Owning company inherited from the source meeting.",
    )
    agenda_item_id = fields.Many2one(
        'nhs.agenda.item',
        help="Agenda item that generated the action.",
    )
    baf_risk_id = fields.Many2one(
        'nhs.baf.risk',
        string='BAF Risk',
        help="Principal BAF risk this action helps close, usually for a control or assurance gap.",
    )
    owner_user_id = fields.Many2one(
        'res.users',
        string='Owner User',
        tracking=True,
        help="Odoo user responsible for completing the action.",
    )
    owner_director_id = fields.Many2one(
        'nhs.director',
        string='Owner Director',
        tracking=True,
        help="Director or officer responsible for completing the action.",
    )
    due_date = fields.Date(required=True, tracking=True, help="Deadline for completing the action.")
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('deferred', 'Deferred'),
        ('overdue', 'Overdue'),
    ], default='open', tracking=True, help="Action workflow status, including automatic overdue marking.")
    completion_note = fields.Text(help="Closure note explaining how the action was completed.")
    reported_meeting_id = fields.Many2one(
        'nhs.meeting',
        string='Reported At',
        help="Meeting where completion was reported as matters arising.",
    )
    active = fields.Boolean(default=True, help="Archive flag; actions are archived rather than hard-deleted.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('nhs.meeting.action') or 'New'
        return super().create(vals_list)

    def action_refresh_overdue_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state not in ('completed', 'deferred') and rec.due_date and rec.due_date < today:
                rec.state = 'overdue'

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_defer(self):
        self.write({'state': 'deferred'})
