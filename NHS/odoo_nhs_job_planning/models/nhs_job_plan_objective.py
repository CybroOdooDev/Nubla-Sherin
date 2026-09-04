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
from odoo.exceptions import UserError

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
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Set to False to hide the objective without removing it."
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
    service_objective_id = fields.Many2one(
        'nhs.service.objective',
        string='Linked Service Objective',
        help="The wider directorate/service objective this personal"
             " objective supports."
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
    active = fields.Boolean(
        default=True,
        help="Achieved objectives are archived automatically, dropping them"
             " out of the Objectives tab's default list so it stays focused"
             " on what's still in progress. Recoverable from the plan's"
             " 'Objectives' stat button, which includes an Archived filter."
    )
    review_notes = fields.Text(
        string='Review Notes',
        help="Notes recorded at annual review."
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('status') == 'achieved':
                vals.setdefault('active', False)
        return super().create(vals_list)

    def write(self, vals):
        """Keep active in sync with status: reaching Achieved archives the
        line (dropping it out of the Objectives tab's default list), and
        moving off Achieved un-archives it again."""
        if 'status' in vals and 'active' not in vals:
            vals = dict(vals, active=vals['status'] != 'achieved')
        return super().write(vals)

    def _check_plan_is_draft(self):
        """Objective status is only changeable while the owning plan is in
        Draft - same rule nhs.job.plan.write() enforces for objective_ids
        edited through the parent form. These status buttons write directly
        on this model, which bypasses that parent-side guard, so the check
        is repeated here. Only reachable on a saved record anyway (the view
        hides these buttons with invisible="not id" on a brand-new line)."""
        for objective in self:
            if objective.plan_id.state != 'draft':
                raise UserError(
                    "'%s' is no longer in Draft. Reset it to Draft to change"
                    " an objective's status." % objective.plan_id.display_name)

    def action_set_status_not_started(self):
        self._check_plan_is_draft()
        self.write({'status': 'not_started'})

    def action_set_status_on_track(self):
        self._check_plan_is_draft()
        self.write({'status': 'on_track'})

    def action_set_status_at_risk(self):
        self._check_plan_is_draft()
        self.write({'status': 'at_risk'})

    def action_set_status_achieved(self):
        self._check_plan_is_draft()
        self.write({'status': 'achieved'})

    def action_set_status_not_achieved(self):
        self._check_plan_is_draft()
        self.write({'status': 'not_achieved'})
