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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class NhsInterviewRescheduleWizard(models.TransientModel):
    """Captures the new date/time (and optionally a new location) for an
    interview before flagging its invite status as rescheduled, so the old
    slot can never be left in place by mistake."""
    _name = 'nhs.interview.reschedule.wizard'
    _description = 'Interview reschedule wizard'

    interview_id = fields.Many2one(
        'nhs.interview', string='Interview', required=True, ondelete='cascade')
    old_datetime = fields.Datetime(
        related='interview_id.interview_datetime', string='Current Date & Time', readonly=True)
    new_datetime = fields.Datetime(string='New Date & Time', required=True)
    new_location = fields.Char(string='Location / Virtual Link')
    reason = fields.Char(string='Reason for Rescheduling')

    @api.constrains('new_datetime', 'old_datetime')
    def _check_new_datetime_changed(self):
        for wizard in self:
            if wizard.new_datetime == wizard.old_datetime:
                raise UserError(_(
                    "Set a new date/time for the interview — it's still the same as the"
                    " current one."))

    def action_apply(self):
        """Writes the new date/time and location onto the interview, flags
        it as rescheduled, and logs the reason on the interview's chatter."""
        self.ensure_one()
        self.interview_id.write({
            'interview_datetime': self.new_datetime,
            'location': self.new_location or self.interview_id.location,
            'invite_status': 'rescheduled',
        })
        if self.reason:
            self.interview_id.message_post(
                body=_("Interview rescheduled: %s") % self.reason)
        return {'type': 'ir.actions.act_window_close'}
