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
from odoo.exceptions import UserError, ValidationError

OBJECTIVE_STATUSES = [
    ('not_started', 'Not Started'),
    ('on_track', 'On Track'),
    ('at_risk', 'At Risk'),
    ('achieved', 'Achieved'),
    ('not_achieved', 'Not Achieved'),
]


class NhsJobPlanObjective(models.Model):
    """A personal objective recorded on a job plan, with its review notes."""
    _name = 'nhs.job.plan.objective'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Job Plan Objective'
    _order = 'sequence, target_date'

    plan_id = fields.Many2one(
        'nhs.job.plan',
        string='Job Plan',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning job plan."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='plan_id.company_id',
        store=True,
        help="Owning company, from the plan."
    )
    doctor_user_id = fields.Many2one(
        'res.users',
        string='Doctor',
        related='plan_id.doctor_user_id',
        store=True,
        help="Doctor, from the plan - lets the cross-plan Objectives list be"
             " grouped/filtered by doctor."
    )
    plan_year_id = fields.Many2one(
        'nhs.plan.year',
        string='Plan Year',
        related='plan_id.plan_year_id',
        store=True,
        help="Plan year, from the plan - lets the cross-plan Objectives list"
             " be grouped/filtered by year."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display order."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Achieved objectives are archived automatically, dropping them out of "
             "the Objectives tab's default list so it stays focused on what's still in progress. "
    )
    name = fields.Char(
        string='Objective',
        required=True,
        tracking=True,
        help="Objective title."
    )
    description = fields.Text(
        string='Description',
        help="Objective detail."
    )
    service_objective_id = fields.Many2one(
        'nhs.service.objective',
        string='Linked Service Objective',
        tracking=True,
        help="The wider directorate/service objective this personal"
             " objective supports."
    )
    target_date = fields.Date(
        string='Target Date',
        tracking=True,
        help="When the objective is expected to be met."
    )
    status = fields.Selection(
        OBJECTIVE_STATUSES,
        string='Status',
        default='not_started',
        tracking=True,
        help="Progress against the objective."
    )

    review_notes = fields.Text(
        string='Review Notes',
        tracking=True,
        help="Notes recorded at annual review."
    )

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)

    def write(self, vals):
        return super().write(vals)

    def action_set_status_not_started(self):
        self.write({'status': 'not_started'})

    def action_set_status_on_track(self):
        self.write({'status': 'on_track'})

    def action_set_status_at_risk(self):
        self.write({'status': 'at_risk'})

    def action_set_status_achieved(self):
        self.write({'status': 'achieved'})

    def action_set_status_not_achieved(self):
        self.write({'status': 'not_achieved'})

    @api.constrains('target_date')
    def _check_target_date(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.target_date and record.target_date < today:
                raise ValidationError("The Target Date cannot be set in the past.")

    @api.onchange('target_date')
    def _onchange_target_date(self):
        if self.target_date:
            today = fields.Date.context_today(self)
            if self.target_date < today:
                self.target_date = False
                return {
                    'warning': {
                        'title': "Invalid Date",
                        'message': "The Target Date cannot be set in the past. Please select a future date.",
                    }
                }
