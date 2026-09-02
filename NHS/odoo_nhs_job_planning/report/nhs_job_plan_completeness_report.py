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
from odoo import models

COMPLETE_STATES = ('signed', 'revised')


class ReportNhsJobPlanCompleteness(models.AbstractModel):
    """Completeness report: per directorate, the % of active medical posts
    with a signed job plan for the year, and the list of gaps - the board
    metric."""
    _name = 'report.odoo_nhs_job_planning.report_nhs_job_plan_completeness'
    _description = 'Job Plan Completeness Report'

    def _get_report_values(self, docids, data=None):
        """ Method for get report values """
        years = self.env['nhs.plan.year'].browse(docids)
        Post = self.env['nhs.establishment.post']
        breakdown_by_year = {}
        for year in years:
            posts = Post.search([('is_medical', '=', True), ('status', '=', 'active'),
                                  ('company_id', '=', year.company_id.id)])
            by_unit = {}
            for post in posts:
                unit = post.org_unit_id
                row = by_unit.setdefault(unit.id, {
                    'unit_name': unit.display_name, 'total': 0, 'signed': 0, 'gaps': [],
                })
                row['total'] += 1
                plan = year.job_plan_ids.filtered(lambda p, post=post: p.post_id == post)
                if plan and any(p.state in COMPLETE_STATES for p in plan):
                    row['signed'] += 1
                else:
                    row['gaps'].append(post.display_name)
            rows = []
            for row in by_unit.values():
                row['pct'] = round(row['signed'] / row['total'] * 100, 2) if row['total'] else 0.0
                rows.append(row)
            breakdown_by_year[year.id] = sorted(rows, key=lambda r: r['unit_name'])
        return {
            'doc_ids': docids,
            'doc_model': 'nhs.plan.year',
            'docs': years,
            'breakdown_by_year': breakdown_by_year,
        }
