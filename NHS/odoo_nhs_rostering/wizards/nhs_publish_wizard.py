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


class NhsPublishWizard(models.TransientModel):
    """The approver's final view before publishing: violations, fill % and
    the lead time this publication would give staff, so they see exactly
    what they are signing off - then nhs.roster.period.action_publish()
    itself is still the one place that blocks on hard violations."""
    _name = 'nhs.publish.wizard'
    _description = 'Publish Roster Wizard'

    period_id = fields.Many2one('nhs.roster.period', string='Roster Period',
                                required=True, help="Roster Period")
    fill_pct = fields.Float(related='period_id.fill_pct', readonly=True,
                            help="Detailed information about this field")
    gap_count = fields.Integer(related='period_id.gap_count', readonly=True,
                               help="Detailed information about this field")
    open_violation_count = fields.Integer(related='period_id.open_violation_count', readonly=True,
                                          help="Detailed information about this field")
    hard_violation_count = fields.Integer(related='period_id.hard_violation_count', readonly=True,
                                          help="Detailed information about this field")
    lead_days_preview = fields.Integer(string='Lead Time if Published Today', compute='_compute_lead_days_preview',
                                       help="Lead Time if Published Today")
    lead_days_target = fields.Integer(related='period_id.company_id.nhs_roster_publish_lead_days_target',
                                       readonly=True, help="Detailed information about this field")

    @api.depends('period_id.date_start')
    def _compute_lead_days_preview(self):
        """ Method for compute lead days preview """
        today = fields.Date.context_today(self)
        for wizard in self:
            wizard.lead_days_preview = (wizard.period_id.date_start - today).days if wizard.period_id.date_start else 0

    def action_confirm(self):
        """ Method for action confirm """
        self.ensure_one()
        self.period_id.action_publish()
        return {'type': 'ir.actions.act_window_close'}
