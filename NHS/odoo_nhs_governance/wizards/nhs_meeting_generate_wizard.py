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
from dateutil.relativedelta import relativedelta
from odoo import fields, models

FREQUENCY_MONTHS = {
    'monthly': 1,
    'bi_monthly': 2,
    'quarterly': 3,
    'annual': 12,
    'ad_hoc': None,
}


class NhsMeetingGenerateWizard(models.TransientModel):
    _name = 'nhs.meeting.generate.wizard'
    _description = 'Generate a recurring meeting series'

    committee_id = fields.Many2one('nhs.committee', string='Committee', required=True,
                                   help='The committee to generate meetings for.')
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('bi_monthly', 'Bi-Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Frequency', required=True, default='monthly',
       help='How often meetings recur. Defaults to the committee\'s configured frequency.')
    start_date = fields.Datetime(string='First Meeting Date', required=True,
                                 default=fields.Datetime.now,
                                 help='Date/time of the first meeting in the series.')
    number_of_meetings = fields.Integer(string='Number Of Meetings', required=True, default=12,
                                        help='How many meetings to generate in this series.')
    location = fields.Char(string='Venue', help='Venue / virtual link descriptor applied to every meeting.')

    def action_generate(self):
        """Create the recurring series of meetings and return a view of the created records."""
        self.ensure_one()
        months_step = FREQUENCY_MONTHS.get(self.frequency, 1)
        meetings = self.env['nhs.meeting']
        current_date = self.start_date
        for _i in range(self.number_of_meetings):
            meetings |= self.env['nhs.meeting'].create({
                'committee_id': self.committee_id.id,
                'meeting_date': current_date,
                'location': self.location,
            })
            current_date = current_date + relativedelta(months=months_step)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generated Meetings',
            'res_model': 'nhs.meeting',
            'view_mode': 'calendar,list,form',
            'domain': [('id', 'in', meetings.ids)],
        }
