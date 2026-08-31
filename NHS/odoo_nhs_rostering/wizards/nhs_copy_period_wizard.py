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
from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class NhsCopyPeriodWizard(models.TransientModel):
    """Copies a roster period as the starting point for a new one: a new
    period is created for the new dates, duties are generated fresh from
    the unit's current demand template (never stale), and - optionally -
    the source period's assignments are carried across to the equivalent
    new duty (same weekday offset, same shift type)."""
    _name = 'nhs.copy.period.wizard'
    _description = 'Copy Roster Period Wizard'

    source_period_id = fields.Many2one('nhs.roster.period', string='Source Period', required=True, help="Source Period")
    new_date_start = fields.Date(string='New Start Date', required=True, help="New Start Date")
    new_date_end = fields.Date(string='New End Date', required=True, help="New End Date")
    copy_assignments = fields.Boolean(
        string='Copy Assignments', default=True,
        help="Carry the source period's assignments across to the equivalent new duty.")

    @api.onchange('source_period_id', 'new_date_start')
    def _onchange_new_date_start(self):
        """ Method for onchange new date start """
        if self.source_period_id and self.new_date_start:
            length = (self.source_period_id.date_end - self.source_period_id.date_start).days
            self.new_date_end = self.new_date_start + timedelta(days=length)

    def action_copy(self):
        """ Method for action copy """
        self.ensure_one()
        source = self.source_period_id
        new_period = self.env['nhs.roster.period'].create({
            'unit_id': source.unit_id.id,
            'date_start': self.new_date_start,
            'date_end': self.new_date_end,
        })
        new_period.action_generate_duties()
        if self.copy_assignments:
            offset = (self.new_date_start - source.date_start).days
            for duty in source.duty_ids:
                new_date = duty.duty_date + timedelta(days=offset)
                target_duty = new_period.duty_ids.filtered(
                    lambda d: d.duty_date == new_date and d.shift_type_id == duty.shift_type_id)[:1]
                if not target_duty:
                    continue
                for assignment in duty.assignment_ids.filtered(lambda a: a.state != 'cancelled'):
                    if target_duty.assignment_ids.filtered(
                            lambda a: a.member_id == assignment.member_id):
                        continue
                    try:
                        self.env['nhs.duty.assignment'].create({
                            'duty_id': target_duty.id, 'member_id': assignment.member_id.id})
                    except ValidationError:
                        continue
        return {
            'name': new_period.name,
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.roster.period',
            'view_mode': 'form',
            'res_id': new_period.id,
        }
