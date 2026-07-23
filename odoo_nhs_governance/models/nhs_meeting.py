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
from odoo.exceptions import UserError


class NhsMeeting(models.Model):
    _name = 'nhs.meeting'
    _description = 'A committee/board meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'meeting_date desc'

    name = fields.Char(string='Meeting', compute='_compute_name', store=True,
                       help="e.g. 'Audit Committee — 12 May 2026'.")
    committee_id = fields.Many2one('nhs.committee', string='Committee', required=True,
                                   ondelete='cascade', tracking=True, help='The committee meeting.')
    company_id = fields.Many2one(related='committee_id.company_id', string='Company', store=True)
    meeting_date = fields.Datetime(string='Date / Time', required=True, tracking=True,
                                   help='Date and time of the meeting.')
    location = fields.Char(string='Venue', help='Venue / virtual meeting link descriptor.')
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('agenda_set', 'Agenda Set'),
        ('held', 'Held'),
        ('minuted', 'Minuted'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', required=True, tracking=True,
       help='Meeting lifecycle: Scheduled → Agenda Set → Held → Minuted → Closed. '
            'May be cancelled from any state prior to Held.')
    cancellation_reason = fields.Text(string='Cancellation Reason',
                                      help='Required when cancelling a meeting.')
    attendee_ids = fields.One2many('nhs.meeting.attendee', 'meeting_id', string='Attendance',
                                   help='Attendance: present / apologies / absent per member.')
    is_quorate = fields.Boolean(string='Quorate', compute='_compute_is_quorate', store=True,
                                help="Present voting members meet the committee's quorum rule. "
                                     "An inquorate meeting is flagged — decisions may not be valid.")
    agenda_item_ids = fields.One2many('nhs.agenda.item', 'meeting_id', string='Agenda', help='Agenda items.')
    agenda_item_count = fields.Integer(string='Agenda Items', compute='_compute_counts')
    action_ids = fields.One2many('nhs.meeting.action', 'meeting_id', string='Actions',
                                 help='Actions raised from the meeting.')
    action_count = fields.Integer(string='Action Count', compute='_compute_counts')
    declaration_ids = fields.One2many('nhs.declaration', 'meeting_id', string='At-Meeting Declarations',
                                      help='Declarations of interest made at this meeting.')
    minutes = fields.Html(string='Minutes',
                          help='Overall meeting minutes (item-level minutes are on the agenda items).')
    pack_generated = fields.Boolean(string='Pack Generated', default=False,
                                    help='Whether the board/committee pack has been assembled for this meeting.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    @api.depends('committee_id.name', 'meeting_date')
    def _compute_name(self):
        for rec in self:
            if rec.committee_id and rec.meeting_date:
                rec.name = f'{rec.committee_id.name} — {fields.Datetime.context_timestamp(rec, rec.meeting_date).strftime("%d %b %Y")}'
            else:
                rec.name = rec.committee_id.name or 'New Meeting'

    @api.depends('attendee_ids.status', 'attendee_ids.voting', 'attendee_ids.is_ned',
                 'committee_id.quorum_min', 'committee_id.quorum_min_ned')
    def _compute_is_quorate(self):
        for rec in self:
            present = rec.attendee_ids.filtered(lambda a: a.status == 'present' and a.voting)
            quorum_ok = len(present) >= (rec.committee_id.quorum_min or 0)
            ned_ok = True
            if rec.committee_id.quorum_min_ned:
                ned_ok = len(present.filtered('is_ned')) >= rec.committee_id.quorum_min_ned
            rec.is_quorate = quorum_ok and ned_ok

    @api.depends('agenda_item_ids', 'action_ids')
    def _compute_counts(self):
        for rec in self:
            rec.agenda_item_count = len(rec.agenda_item_ids)
            rec.action_count = len(rec.action_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_attendees()
        return records

    def _sync_attendees(self):
        """Seed an attendance line for every current committee member who doesn't have one yet."""
        for rec in self:
            existing = rec.attendee_ids.mapped('member_id')
            missing = rec.committee_id.member_ids.filtered(lambda m: m not in existing)
            for member in missing:
                self.env['nhs.meeting.attendee'].create({
                    'meeting_id': rec.id,
                    'member_id': member.id,
                    'voting': member.voting,
                    'is_ned': member.is_ned,
                })

    def action_set_agenda(self):
        self.write({'state': 'agenda_set'})

    def action_hold(self):
        self.write({'state': 'held'})

    def action_minute(self):
        self.write({'state': 'minuted'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        for rec in self:
            if rec.state in ('held', 'minuted', 'closed'):
                raise UserError('A meeting that has already been held cannot be cancelled.')
        self.write({'state': 'cancelled'})

    def action_view_pack(self):
        self.ensure_one()
        return self.env.ref('odoo_nhs_governance.action_report_board_pack').report_action(self)

    def action_open_agenda_from_cycle_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Populate Agenda From Cycle Of Business',
            'res_model': 'nhs.agenda.from.cycle.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_meeting_id': self.id},
        }

    def action_open_board_pack_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assemble Board Pack',
            'res_model': 'nhs.board.pack.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_meeting_id': self.id},
        }


class NhsMeetingAttendee(models.Model):
    _name = 'nhs.meeting.attendee'
    _description = 'Meeting Attendance Line'
    _order = 'meeting_id, id'

    meeting_id = fields.Many2one('nhs.meeting', string='Meeting', required=True, ondelete='cascade')
    committee_id = fields.Many2one(related='meeting_id.committee_id', string='Committee', store=True)
    member_id = fields.Many2one('nhs.committee.member', string='Committee Member', required=True,
                                ondelete='cascade')
    name = fields.Char(related='member_id.name', string='Name', store=True)
    role = fields.Selection(related='member_id.role', string='Role', store=True)
    status = fields.Selection([
        ('present', 'Present'),
        ('apologies', 'Apologies'),
        ('absent', 'Absent'),
    ], string='Attendance', default='present', required=True,
       help='Present / apologies / absent for this meeting.')
    voting = fields.Boolean(string='Voting', default=True,
                            help='Whether this attendee counts toward quoracy for this meeting.')
    is_ned = fields.Boolean(string='NED', help='Non-executive director — counts toward the NED quorum.')

    _meeting_member_unique = models.Constraint(
        'UNIQUE(meeting_id, member_id)',
        'This member already has an attendance line for this meeting.',
    )
