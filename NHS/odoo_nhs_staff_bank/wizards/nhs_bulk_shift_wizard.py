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
from datetime import datetime, timedelta
from odoo import fields, models
from odoo.exceptions import UserError


class NhsBulkShiftWizard(models.TransientModel):
    """Bulk-create recurring open shifts across a date range on the chosen
    weekdays (e.g. a run of nights, or every weekend for a month)."""
    _name = 'nhs.bulk.shift.wizard'
    _description = 'Bulk-Create Recurring Shifts Wizard'

    org_unit_id = fields.Many2one('nhs.org.unit', string='Area / Ward', required=True)
    band_id = fields.Many2one('nhs.afc.band', string='Band')
    role = fields.Char(string='Role')
    skill_ids = fields.Many2many('nhs.skill', string='Skills Required')
    shift_type_id = fields.Many2one('nhs.shift.type', string='Shift Type')
    headcount = fields.Integer(string='Headcount Needed', default=1)
    reason = fields.Selection([
        ('sickness', 'Sickness Cover'), ('vacancy', 'Vacancy Cover'),
        ('demand', 'Extra Demand'), ('special', 'Special'),
    ], string='Reason')
    urgency = fields.Selection([
        ('planned', 'Planned'), ('urgent', 'Urgent'), ('last_minute', 'Last-Minute'),
    ], string='Urgency', default='planned')
    date_from = fields.Date(string='From Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    start_time = fields.Float(string='Start Time', default=20.0, help="24h decimal, e.g. 20.0 = 20:00.")
    end_time = fields.Float(string='End Time', default=8.0, help="24h decimal; a value <= start"
                             " time is treated as ending the following day (an overnight shift).")
    weekday_ids = fields.Many2many(
        'nhs.weekday',
        string='Days',
        default=lambda self: self.env['nhs.weekday'].search([]),
        help="Days of the week the pattern recurs on."
    )

    def _float_to_time(self, value):
        """Split a 24h decimal time (e.g. 20.5) into (hours, minutes)."""
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        return hours, minutes

    def action_create_shifts(self):
        """Create one nhs.bank.shift per matching weekday in the date range."""
        self.ensure_one()
        if self.date_to < self.date_from:
            raise UserError(("'To Date' cannot be before 'From Date'."))
        active_weekdays = set(self.weekday_ids.mapped('index'))
        if not active_weekdays:
            raise UserError(("Select at least one day of the week."))

        start_h, start_m = self._float_to_time(self.start_time)
        end_h, end_m = self._float_to_time(self.end_time)
        overnight = self.end_time <= self.start_time

        vals_list = []
        current = self.date_from
        while current <= self.date_to:
            if current.weekday() in active_weekdays:
                shift_start = datetime.combine(current, datetime.min.time()).replace(hour=start_h, minute=start_m)
                end_date = current + timedelta(days=1) if overnight else current
                shift_end = datetime.combine(end_date, datetime.min.time()).replace(hour=end_h, minute=end_m)
                vals_list.append({
                    'org_unit_id': self.org_unit_id.id,
                    'band_id': self.band_id.id,
                    'role': self.role,
                    'skill_ids': [(6, 0, self.skill_ids.ids)],
                    'shift_type_id': self.shift_type_id.id,
                    'headcount': self.headcount,
                    'reason': self.reason,
                    'urgency': self.urgency,
                    'shift_start': fields.Datetime.to_string(shift_start),
                    'shift_end': fields.Datetime.to_string(shift_end),
                    # Bulk creation is a deliberate "raise these shifts now" action —
                    # skip the draft review step new single shifts get by default.
                    'state': 'open',
                })
            current += timedelta(days=1)
        if not vals_list:
            raise UserError(("No dates in range matched the selected weekdays."))
        shifts = self.env['nhs.bank.shift'].create(vals_list)
        return {
            'name': ('Created Shifts'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.bank.shift',
            'view_mode': 'list,form',
            'domain': [('id', 'in', shifts.ids)],
        }
