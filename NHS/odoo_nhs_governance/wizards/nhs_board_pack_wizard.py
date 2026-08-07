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


class NhsBoardPackWizard(models.TransientModel):
    _name = 'nhs.board.pack.wizard'
    _description = 'Assemble & distribute the board/committee pack'

    meeting_id = fields.Many2one('nhs.meeting', string='Meeting', required=True,
                                 help='The meeting to assemble the pack for.')
    include_confidential = fields.Boolean(string='Include Confidential (Part II) Section', default=False,
                                          help='Include the confidential/Part-II items in a separate '
                                               'section of the pack. Only entitled members should '
                                               'receive this version.')
    distribute = fields.Boolean(string='Distribute To Members', default=True,
                                help='Post a notification to committee members recording issue of the pack.')

    def action_assemble(self):
        """Mark the pack as generated, notify members, and return the printable report action."""
        self.ensure_one()
        meeting = self.meeting_id
        meeting.pack_generated = True
        if self.distribute:
            meeting.message_post(
                body='Board pack assembled and issued (%s).' % (
                    'including confidential section' if self.include_confidential else 'public section only'))
            template = self.env.ref('odoo_nhs_governance.mail_template_meeting_pack_issued',
                                    raise_if_not_found=False)
            if template:
                for member in meeting.committee_id.member_ids.filtered('email'):
                    template.send_mail(meeting.id, force_send=False,
                                       email_values={'email_to': member.email})
        return self.env.ref('odoo_nhs_governance.action_report_board_pack').with_context(
            include_confidential=self.include_confidential
        ).report_action(meeting, data={
            'doc_ids': meeting.ids,
            'include_confidential': self.include_confidential,
        })
