# -*- coding: utf-8 -*-
from odoo import fields, models


class NhsAgendaItem(models.Model):
    _name = 'nhs.agenda.item'
    _description = 'NHS Meeting Agenda Item and Paper'
    _order = 'meeting_id, sequence, id'

    meeting_id = fields.Many2one(
        'nhs.meeting',
        required=True,
        ondelete='cascade',
        help="Meeting that owns this agenda item.",
    )
    committee_id = fields.Many2one(
        related='meeting_id.committee_id',
        store=True,
        help="Committee inherited from the meeting.",
    )
    company_id = fields.Many2one(
        related='meeting_id.company_id',
        store=True,
        help="Owning company inherited from the meeting.",
    )
    sequence = fields.Integer(default=10, help="Ordering position on the agenda.")
    item_number = fields.Char(help="Agenda item number or reference shown in the pack.")
    title = fields.Char(required=True, help="Agenda item title.")
    purpose = fields.Selection([
        ('decision', 'Decision'),
        ('assurance', 'Assurance'),
        ('information', 'Information'),
        ('discussion', 'Discussion'),
    ], default='information', help="Purpose of the item: decision, assurance, information or discussion.")
    presenter_director_id = fields.Many2one(
        'nhs.director',
        string='Presenter',
        help="Director or officer presenting the item.",
    )
    presenter_user_id = fields.Many2one(
        'res.users',
        string='Presenter User',
        help="Odoo user presenting the item, where different from the director record.",
    )
    time_allocation = fields.Integer(string='Minutes', help="Planned agenda time allocation in minutes.")
    cycle_item_id = fields.Many2one(
        'nhs.cycle.of.business',
        help="Standing cycle-of-business item this agenda item fulfils.",
    )
    is_confidential = fields.Boolean(
        string='Part-II / Confidential',
        help="Marks the item for confidential or Part-II pack handling.",
    )
    paper_ids = fields.Many2many(
        'ir.attachment',
        'nhs_agenda_item_attachment_rel',
        'agenda_item_id',
        'attachment_id',
        help="Papers and reports attached to this agenda item.",
    )
    paper_author_id = fields.Many2one('res.users', string='Paper Author', help="Author responsible for the paper.")
    paper_version = fields.Char(help="Version reference for the paper or report.")
    minute_text = fields.Html(help="Minute recorded for this specific agenda item.")
    decision_text = fields.Text(help="Formal decision or resolution made for this item.")
    deferred_to_id = fields.Many2one(
        'nhs.meeting',
        string='Deferred To',
        help="Future meeting this item has been carried forward to.",
    )
    action_ids = fields.One2many(
        'nhs.meeting.action',
        'agenda_item_id',
        help="Actions raised from this agenda item.",
    )
