# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class NhsMeeting(models.Model):
    _name = 'nhs.meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'NHS Committee or Board Meeting'
    _order = 'meeting_date desc, id desc'

    name = fields.Char(
        compute='_compute_name',
        store=True,
        help="Display name built from the committee and meeting date.",
    )
    committee_id = fields.Many2one(
        'nhs.committee',
        required=True,
        tracking=True,
        help="Committee or board holding this meeting.",
    )
    company_id = fields.Many2one(
        related='committee_id.company_id',
        store=True,
        help="Owning company inherited from the committee.",
    )
    meeting_date = fields.Datetime(required=True, tracking=True, help="Scheduled date and time of the meeting.")
    location = fields.Char(string='Venue / Virtual Link', help="Physical venue or virtual meeting link descriptor.")
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('agenda_set', 'Agenda Set'),
        ('held', 'Held'),
        ('minuted', 'Minuted'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], default='scheduled', required=True, tracking=True,
        help="Meeting workflow from scheduled through agenda, held, minuted and closed.")
    attendee_ids = fields.One2many(
        'nhs.meeting.attendance',
        'meeting_id',
        help="Attendance lines showing present, apologies or absent for each committee member.",
    )
    present_voting_count = fields.Integer(
        compute='_compute_quoracy',
        help="Number of present voting members counted toward quorum.",
    )
    present_ned_count = fields.Integer(
        compute='_compute_quoracy',
        help="Number of present non-executive directors counted toward NED quorum.",
    )
    is_quorate = fields.Boolean(
        compute='_compute_quoracy',
        store=True,
        help="Whether attendance meets the committee quorum and NED quorum rules.",
    )
    agenda_item_ids = fields.One2many(
        'nhs.agenda.item',
        'meeting_id',
        help="Agenda items, papers, item minutes and decisions for this meeting.",
    )
    action_ids = fields.One2many(
        'nhs.meeting.action',
        'meeting_id',
        help="Actions arising from the meeting.",
    )
    declaration_ids = fields.One2many(
        'nhs.declaration',
        'meeting_id',
        help="Declarations of interest made at this meeting.",
    )
    minutes = fields.Html(help="Overall meeting minutes; item-level minutes are captured on agenda items.")
    pack_generated = fields.Boolean(help="Indicates that a board or committee pack has been assembled.")
    pack_issued_date = fields.Datetime(help="Date and time the meeting pack was issued to members.")
    cancellation_reason = fields.Text(help="Reason for cancellation when the meeting is cancelled.")

    @api.depends('committee_id', 'meeting_date')
    def _compute_name(self):
        for rec in self:
            date_text = fields.Datetime.to_string(rec.meeting_date) if rec.meeting_date else ''
            rec.name = ' - '.join(filter(None, [rec.committee_id.name, date_text[:16]]))

    @api.depends('attendee_ids.status', 'attendee_ids.member_id.voting', 'attendee_ids.member_id.is_ned',
                 'committee_id.quorum_min', 'committee_id.quorum_min_ned')
    def _compute_quoracy(self):
        for rec in self:
            present = rec.attendee_ids.filtered(lambda line: line.status == 'present')
            voting = present.filtered(lambda line: line.member_id.voting)
            neds = voting.filtered(lambda line: line.member_id.is_ned)
            rec.present_voting_count = len(voting)
            rec.present_ned_count = len(neds)
            rec.is_quorate = (
                len(voting) >= (rec.committee_id.quorum_min or 0)
                and len(neds) >= (rec.committee_id.quorum_min_ned or 0)
            )

    def action_set_agenda(self):
        self.write({'state': 'agenda_set'})

    def action_mark_held(self):
        self.write({'state': 'held'})

    def action_mark_minuted(self):
        self.write({'state': 'minuted'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_populate_attendance(self):
        for meeting in self:
            existing = meeting.attendee_ids.mapped('member_id')
            for member in meeting.committee_id.member_ids - existing:
                self.env['nhs.meeting.attendance'].create({
                    'meeting_id': meeting.id,
                    'member_id': member.id,
                    'status': 'present',
                })

    def _frequency_delta(self):
        self.ensure_one()
        return {
            'monthly': relativedelta(months=1),
            'bi_monthly': relativedelta(months=2),
            'quarterly': relativedelta(months=3),
            'annual': relativedelta(years=1),
        }.get(self.committee_id.frequency, relativedelta(months=1))


class NhsMeetingAttendance(models.Model):
    _name = 'nhs.meeting.attendance'
    _description = 'NHS Meeting Attendance'
    _order = 'meeting_id, member_id'

    meeting_id = fields.Many2one(
        'nhs.meeting',
        required=True,
        ondelete='cascade',
        help="Meeting this attendance line belongs to.",
    )
    company_id = fields.Many2one(
        related='meeting_id.company_id',
        store=True,
        help="Owning company inherited from the meeting.",
    )
    member_id = fields.Many2one(
        'nhs.committee.member',
        required=True,
        help="Committee member whose attendance is being recorded.",
    )
    director_id = fields.Many2one(
        related='member_id.director_id',
        store=True,
        help="Director or officer linked to the committee member.",
    )
    status = fields.Selection([
        ('present', 'Present'),
        ('apologies', 'Apologies'),
        ('absent', 'Absent'),
    ], default='present', required=True, help="Attendance outcome for the meeting.")
    note = fields.Char(help="Optional attendance note, such as partial attendance or apology detail.")
