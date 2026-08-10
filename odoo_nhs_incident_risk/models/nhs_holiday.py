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
from datetime import  timedelta


class NhsHoliday(models.Model):
    _name = 'nhs.holiday'
    _description = 'Bank Holiday (England & Wales)'
    _order = 'date'

    name = fields.Char(string='Name', required=True,
                       help='Name of the bank or public holiday (e.g. Christmas Day, Easter Monday).')
    date = fields.Date(string='Date', required=True,
                       help='The calendar date of this bank holiday. Used to exclude non-working days '
                            'when calculating incident closure times and Duty of Candour deadlines.')
    company_id = fields.Many2one('res.company', string='Company',
                                 help='Leave blank to apply this holiday to all companies. '
                                      'Set a company to restrict it to a single organisation.')

    @api.model
    def add_working_days(self, start_date, n):
        """Return the date that is n working days after start_date."""
        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)
        holidays = set(self.search([]).mapped('date'))
        current = start_date
        days_added = 0
        while days_added < n:
            current += timedelta(days=1)
            if current.weekday() < 5 and current not in holidays:
                days_added += 1
        return current
