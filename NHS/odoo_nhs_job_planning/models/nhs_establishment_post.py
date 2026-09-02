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

CURRENT_PLAN_STATES = ('draft', 'proposed', 'in_discussion', 'agreed', 'signed', 'revised')


class NhsEstablishmentPost(models.Model):
    """Adds the job-planning reverse link to a medical post."""
    _inherit = 'nhs.establishment.post'

    job_plan_ids = fields.One2many(
        'nhs.job.plan',
        'post_id',
        string='Job Plans',
        help="Every job plan ever raised against this post, across every plan year."
    )
    job_plan_count = fields.Integer(
        string='Job Plan Count',
        compute='_compute_job_plan_count',
        help="Number of job plans raised against this post."
    )
    current_job_plan_id = fields.Many2one(
        'nhs.job.plan',
        string='Current Job Plan',
        compute='_compute_current_job_plan_id',
        store=True,
        help="This post's most recent non-superseded job plan. Stored (rather"
             " than a plain compute) so it stays searchable - needed for"
             " job_plan_state's own dependency resolution and for the Gaps view."
    )
    job_plan_state = fields.Selection(
        related='current_job_plan_id.state',
        string='Job Plan Status',
        readonly=True,
        help="Status of the current job plan, for a quick glance on the post."
    )

    def _compute_job_plan_count(self):
        """Count job plans raised against each post."""
        data = self.env['nhs.job.plan']._read_group(
            [('post_id', 'in', self.ids)], ['post_id'], ['__count'])
        counts = {post.id: count for post, count in data}
        for post in self:
            post.job_plan_count = counts.get(post.id, 0)

    @api.depends('job_plan_ids.state', 'job_plan_ids.plan_year_id')
    def _compute_current_job_plan_id(self):
        """Find the most recent non-superseded job plan for each post.
        'plan_year_id desc' alone doesn't determine recency when two plans
        share a year - exactly what an in-year revision produces (the old
        plan flips to 'revised', a new draft is created in the same year).
        'id desc' breaks that tie in favour of the newer row, so a post
        mid-revision correctly shows its new unsigned draft as current
        (job_plan_state back to 'draft') rather than the superseded-in-
        spirit 'revised' row silently keeping it out of Gaps/completeness."""
        JobPlan = self.env['nhs.job.plan']
        for post in self:
            post.current_job_plan_id = JobPlan.search([
                ('post_id', '=', post.id),
                ('state', 'in', CURRENT_PLAN_STATES),
            ], order='plan_year_id desc, id desc', limit=1)

    def action_view_job_plans(self):
        """Open the job plans raised against this post."""
        self.ensure_one()
        return {
            'name': 'Job Plans',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.job.plan',
            'view_mode': 'list,form',
            'domain': [('post_id', '=', self.id)],
            'context': {'default_post_id': self.id},
        }
