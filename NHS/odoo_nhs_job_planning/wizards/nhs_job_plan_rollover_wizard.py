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


class NhsJobPlanRolloverWizard(models.TransientModel):
    """Bulk plan-year rollover: clone last year's job plans as fresh drafts
    in a new plan year."""
    _name = 'nhs.job.plan.rollover.wizard'
    _description = 'Job Plan Year Rollover Wizard'

    source_plan_year_id = fields.Many2one(
        'nhs.plan.year',
        string='Source Plan Year',
        required=True,
        help="Plan year to clone job plans from."
    )
    target_plan_year_id = fields.Many2one(
        'nhs.plan.year',
        string='Target Plan Year',
        required=True,
        help="Plan year to create the new draft job plans in."
    )
    org_unit_ids = fields.Many2many(
        'nhs.org.unit',
        string='Limit to Directorates/Units',
        help="Leave blank to roll over every eligible plan; otherwise only"
             " plans whose post sits in one of these units are cloned."
    )
    only_signed_source = fields.Boolean(
        string='Only Clone Signed Plans',
        default=True,
        help="Only clone plans currently Signed in the source year - skips"
             " abandoned drafts. Superseded/revised rows are never cloned"
             " either way, since the latest version of each already represents"
             " that post."
    )
    plan_preview_count = fields.Integer(
        string='Plans To Roll Over',
        compute='_compute_plan_preview_count',
        help="Number of job plans that will be created by this rollover."
    )

    def _get_source_plans(self):
        """The source-year job plans matching this wizard's filters. Delegates
        to nhs.job.plan._get_rollover_candidates(), the same filter the
        automatic-rollover cron uses, so preview and actual rollover always
        agree."""
        self.ensure_one()
        return self.env['nhs.job.plan']._get_rollover_candidates(
            self.source_plan_year_id, self.org_unit_ids, self.only_signed_source)

    @api.depends('source_plan_year_id', 'org_unit_ids', 'only_signed_source')
    def _compute_plan_preview_count(self):
        """Preview how many plans this rollover will create."""
        for wizard in self:
            wizard.plan_preview_count = len(wizard._get_source_plans()) \
                if wizard.source_plan_year_id else 0

    def action_rollover(self):
        """Clone matching source-year plans as fresh drafts in the target
        year, via nhs.job.plan._rollover_plans() - the same routine the
        automatic-rollover cron uses."""
        self.ensure_one()
        if self.source_plan_year_id == self.target_plan_year_id:
            raise UserError("Source and target plan years must be different.")
        new_plans = self.env['nhs.job.plan']._rollover_plans(
            self.source_plan_year_id, self.target_plan_year_id,
            self.org_unit_ids, self.only_signed_source)
        return {
            'name': 'Rolled-Over Job Plans',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.job.plan',
            'view_mode': 'list,form',
            'domain': [('id', 'in', new_plans.ids)],
        }
