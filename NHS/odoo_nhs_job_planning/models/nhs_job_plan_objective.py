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
from odoo import fields, models

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
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display order."
    )
    name = fields.Char(
        string='Objective',
        required=True,
        help="Objective title."
    )
    description = fields.Text(
        string='Description',
        help="Objective detail."
    )
    linked_service_objective = fields.Char(
        string='Linked Service Objective',
        help="Free-text link to the wider service objective this supports."
    )
    target_date = fields.Date(
        string='Target Date',
        help="When the objective is expected to be met."
    )
    status = fields.Selection(
        OBJECTIVE_STATUSES,
        string='Status',
        default='not_started',
        help="Progress against the objective."
    )
    review_notes = fields.Text(
        string='Review Notes',
        help="Notes recorded at annual review."
    )
