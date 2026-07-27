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
from odoo import fields, models


class NhsAgendaFromCycleWizard(models.TransientModel):
    _name = 'nhs.agenda.from.cycle.wizard'
    _description = 'Populate a meeting agenda from the committee cycle of business'

    meeting_id = fields.Many2one('nhs.meeting', string='Meeting', required=True,
                                 help='The meeting to build the agenda for.')

    def action_populate(self):
        """Create agenda items for cycle-of-business entries due this meeting's month."""
        self.ensure_one()
        meeting = self.meeting_id
        month = fields.Datetime.context_timestamp(self, meeting.meeting_date).month
        existing_cycle_items = meeting.agenda_item_ids.mapped('cycle_item_id')
        due_items = meeting.committee_id.cycle_item_ids.filtered(
            lambda item: item.active and item not in existing_cycle_items and item.is_due_for_month(month))
        sequence = (max(meeting.agenda_item_ids.mapped('sequence')) + 10) if meeting.agenda_item_ids else 10
        item_no = len(meeting.agenda_item_ids) + 1
        for item in due_items:
            self.env['nhs.agenda.item'].create({
                'meeting_id': meeting.id,
                'item_number': str(item_no),
                'title': item.title,
                'purpose': item.purpose,
                'presenter_id': item.owner_id.id,
                'cycle_item_id': item.id,
                'sequence': sequence,
            })
            sequence += 10
            item_no += 1
        if meeting.state == 'scheduled':
            meeting.action_set_agenda()
        return {'type': 'ir.actions.act_window_close'}
