from odoo import api, fields, models
from datetime import date, timedelta


class NhsHoliday(models.Model):
    _name = 'nhs.holiday'
    _description = 'Bank Holiday (England & Wales)'
    _order = 'date'

    name = fields.Char(string='Name', required=True)
    date = fields.Date(string='Date', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 help='Leave blank for all companies.')

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
