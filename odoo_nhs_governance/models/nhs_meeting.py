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
from odoo.exceptions import UserError, ValidationError


class NhsMeeting(models.Model):
    _name = 'nhs.meeting'
    _description = 'A committee/board meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'meeting_date desc'

    name = fields.Char(string='Meeting', required=True, copy=False, tracking=True,
                       help="Defaults to e.g. 'Audit Committee — 12 May 2026' but can be edited manually.")
    committee_id = fields.Many2one('nhs.committee', string='Committee', required=True,
                                   ondelete='cascade', tracking=True, help='The committee meeting.')
    company_id = fields.Many2one(related='committee_id.company_id', string='Company', store=True,
                                 help='Company the owning committee belongs to.')
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
    agenda_item_count = fields.Integer(string='Agenda Items', compute='_compute_counts',
                                       help='Number of agenda items on this meeting.')
    action_ids = fields.One2many('nhs.meeting.action', 'meeting_id', string='Actions',
                                 help='Actions raised from the meeting.')
    action_count = fields.Integer(string='Action Count', compute='_compute_counts',
                                  help='Number of actions raised from this meeting.')
    declaration_ids = fields.One2many('nhs.declaration', 'meeting_id', string='At-Meeting Declarations',
                                      help='Declarations of interest made at this meeting.')
    minutes = fields.Html(string='Minutes',
                          help='Overall meeting minutes (item-level minutes are on the agenda items).')
    pack_generated = fields.Boolean(string='Pack Generated', default=False,
                                    help='Whether the board/committee pack has been assembled for this meeting.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    def _default_meeting_name(self, committee, meeting_date):
        """Build the default meeting name from the committee and meeting date."""
        if committee and meeting_date:
            return f'{committee.name} — {fields.Datetime.context_timestamp(self, meeting_date).strftime("%d %b %Y")}'
        return committee.name or 'New Meeting'

    @api.onchange('committee_id', 'meeting_date')
    def _onchange_meeting_name_suggestion(self):
        """Suggest a meeting name once committee and date are known, if not already set."""
        for rec in self:
            if not rec.name:
                rec.name = rec._default_meeting_name(rec.committee_id, rec.meeting_date)

    @api.constrains('meeting_date', 'state')
    def _check_meeting_date_not_past(self):
        """Prevent a scheduled meeting from being dated in the past."""
        now = fields.Datetime.now()
        for rec in self:
            if rec.state == 'scheduled' and rec.meeting_date and rec.meeting_date < now:
                raise ValidationError('A scheduled meeting cannot be dated in the past.')

    @api.depends('attendee_ids.status', 'attendee_ids.voting', 'attendee_ids.is_ned',
                 'committee_id.quorum_min', 'committee_id.quorum_min_ned')
    def _compute_is_quorate(self):
        """Determine whether each meeting meets its committee's quorum rule."""
        for rec in self:
            present = rec.attendee_ids.filtered(lambda a: a.status == 'present' and a.voting)
            quorum_ok = len(present) >= (rec.committee_id.quorum_min or 0)
            ned_ok = True
            if rec.committee_id.quorum_min_ned:
                ned_ok = len(present.filtered('is_ned')) >= rec.committee_id.quorum_min_ned
            rec.is_quorate = quorum_ok and ned_ok

    @api.depends('agenda_item_ids', 'action_ids')
    def _compute_counts(self):
        """Compute the agenda item and action counts for each meeting."""
        for rec in self:
            rec.agenda_item_count = len(rec.agenda_item_ids)
            rec.action_count = len(rec.action_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """Default the meeting name if missing, then seed attendance for committee members."""
        for vals in vals_list:
            if not vals.get('name'):
                committee = self.env['nhs.committee'].browse(vals.get('committee_id'))
                meeting_date = fields.Datetime.to_datetime(vals.get('meeting_date'))
                vals['name'] = self._default_meeting_name(committee, meeting_date)
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
        """Move the meeting to the Agenda Set state, once it has agenda items."""
        for rec in self:
            if not rec.agenda_item_ids:
                raise UserError('Add at least one agenda item before setting the agenda.')
        self.write({'state': 'agenda_set'})

    def action_hold(self):
        """Mark the meeting as held, once all agenda items are resolved."""
        for rec in self:
            if any(item.state == 'draft' for item in rec.agenda_item_ids):
                raise UserError('All agenda items must be marked as Completed or Deferred before the meeting can be held.')
        self.write({'state': 'held'})

    def action_minute(self):
        """Mark the meeting as minuted."""
        self.write({'state': 'minuted'})

    def action_close(self):
        """Close the meeting."""
        self.write({'state': 'closed'})

    def action_cancel(self):
        """Cancel the meeting, unless it has already been held."""
        for rec in self:
            if rec.state in ('held', 'minuted', 'closed'):
                raise UserError('A meeting that has already been held cannot be cancelled.')
        self.write({'state': 'cancelled'})

    def action_view_pack(self):
        """Open the generated board pack report for this meeting."""
        self.ensure_one()
        return self.env.ref('odoo_nhs_governance.action_report_board_pack').report_action(self)

    def action_open_agenda_from_cycle_wizard(self):
        """Open the wizard to populate the agenda from the cycle of business."""
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
        """Open the wizard to assemble the board pack for this meeting."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assemble Board Pack',
            'res_model': 'nhs.board.pack.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_meeting_id': self.id},
        }

    @api.model
    def get_governance_dashboard_data(self):
        """Aggregate the governance dashboard data: meetings, actions, DoI, ToR and BAF status."""
        today = fields.Date.context_today(self)
        today_str = today.strftime('%Y-%m-%d')

        # 1. Upcoming Meetings
        upcoming_domain = [('meeting_date', '>=', today_str), ('state', '!=', 'cancelled')]
        upcoming_meetings_recs = self.search(upcoming_domain, limit=10, order='meeting_date asc')
        upcoming_count = self.search_count(upcoming_domain)
        upcoming_list = []
        for m in upcoming_meetings_recs:
            upcoming_list.append({
                'id': m.id,
                'name': m.name,
                'committee_name': m.committee_id.name if m.committee_id else '',
                'date': fields.Datetime.context_timestamp(m, m.meeting_date).strftime('%b %d, %Y %I:%M %p') if m.meeting_date else '',
                'venue': m.location or '',
                'is_quorate': m.is_quorate,
                'state': m.state,
                'state_label': dict(m._fields['state'].selection).get(m.state, m.state),
            })

        # 2. Inquorate Meetings
        inquorate_domain = [('is_quorate', '=', False), ('state', 'not in', ('scheduled', 'cancelled'))]
        inquorate_recs = self.search(inquorate_domain, limit=10, order='meeting_date desc')
        inquorate_count = self.search_count(inquorate_domain)
        inquorate_list = []
        for m in inquorate_recs:
            inquorate_list.append({
                'id': m.id,
                'name': m.name,
                'committee_name': m.committee_id.name if m.committee_id else '',
                'date': fields.Datetime.context_timestamp(m, m.meeting_date).strftime('%b %d, %Y %I:%M %p') if m.meeting_date else '',
                'venue': m.location or '',
                'state_label': dict(m._fields['state'].selection).get(m.state, m.state),
            })

        # 3. Overdue Actions
        overdue_actions_domain = [('state', '=', 'overdue')]
        overdue_actions_recs = self.env['nhs.meeting.action'].search(overdue_actions_domain, limit=10, order='due_date asc')
        overdue_actions_count = self.env['nhs.meeting.action'].search_count(overdue_actions_domain)
        overdue_actions_list = []
        for act in overdue_actions_recs:
            overdue_actions_list.append({
                'id': act.id,
                'name': act.name,
                'meeting_name': act.meeting_id.name if act.meeting_id else '',
                'assigned_to': act.owner_id.name if act.owner_id else '',
                'due_date': act.due_date.strftime('%b %d, %Y') if act.due_date else '',
                'state': act.state,
            })

        # 4. DoI Refreshes Due (nhs.director with committee memberships)
        doi_domain = [('committee_membership_ids', '!=', False)]
        doi_recs = self.env['nhs.director'].search(doi_domain, limit=10)
        doi_count = self.env['nhs.director'].search_count(doi_domain)
        doi_list = []
        for d in doi_recs:
            doi_list.append({
                'id': d.id,
                'name': d.name,
                'email': d.partner_id.email or '',
                'memberships_count': len(d.committee_membership_ids),
            })

        # 5. ToR Reviews Due
        tor_domain = [('tor_review_date', '!=', False), ('tor_review_date', '<=', today_str), ('state', '=', 'active')]
        tor_recs = self.env['nhs.committee'].search(tor_domain, limit=10)
        tor_count = self.env['nhs.committee'].search_count(tor_domain)
        tor_list = []
        for c in tor_recs:
            tor_list.append({
                'id': c.id,
                'name': c.name,
                'tor_review_date': c.tor_review_date.strftime('%b %d, %Y') if c.tor_review_date else '',
                'chair_name': c.chair_id.name if c.chair_id else '',
            })

        # 6. BAF Risks Un-Reviewed
        baf_unreviewed_domain = [('last_reviewed', '=', False)]
        baf_unreviewed_recs = self.env['nhs.baf.risk'].search(baf_unreviewed_domain, limit=10)
        baf_unreviewed_count = self.env['nhs.baf.risk'].search_count(baf_unreviewed_domain)
        baf_unreviewed_list = []
        for r in baf_unreviewed_recs:
            baf_unreviewed_list.append({
                'id': r.id,
                'name': r.name,
                'objective_name': r.objective_id.name if r.objective_id else '',
                'score': r.current_score,
                'band': r.current_band,
            })

        # 7. BAF Status
        all_baf_risks = self.env['nhs.baf.risk'].search([])
        baf_total = len(all_baf_risks)
        baf_bands = {'extreme': 0, 'high': 0, 'moderate': 0, 'low': 0}
        for r in all_baf_risks:
            if r.current_band in baf_bands:
                baf_bands[r.current_band] += 1

        return {
            'upcoming_count': upcoming_count,
            'upcoming_list': upcoming_list,
            'inquorate_count': inquorate_count,
            'inquorate_list': inquorate_list,
            'overdue_actions_count': overdue_actions_count,
            'overdue_actions_list': overdue_actions_list,
            'doi_count': doi_count,
            'doi_list': doi_list,
            'tor_count': tor_count,
            'tor_list': tor_list,
            'baf_unreviewed_count': baf_unreviewed_count,
            'baf_unreviewed_list': baf_unreviewed_list,
            'baf_total': baf_total,
            'baf_bands': baf_bands,
        }



class NhsMeetingAttendee(models.Model):
    _name = 'nhs.meeting.attendee'
    _description = 'Meeting Attendance Line'
    _order = 'meeting_id, id'

    meeting_id = fields.Many2one('nhs.meeting', string='Meeting', required=True, ondelete='cascade',
                                 help='The meeting this attendance line belongs to.')
    committee_id = fields.Many2one(related='meeting_id.committee_id', string='Committee', store=True,
                                   help='Committee holding the meeting, for filtering/grouping.')
    member_id = fields.Many2one('nhs.committee.member', string='Committee Member', required=True,
                                ondelete='cascade', help='The committee member this attendance line records.')
    name = fields.Char(related='member_id.name', string='Name', store=True,
                       help="The member's name, mirrored for display in attendance lists.")
    role = fields.Selection(related='member_id.role', string='Role', store=True,
                            help="The member's role on the committee, mirrored for display.")
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
