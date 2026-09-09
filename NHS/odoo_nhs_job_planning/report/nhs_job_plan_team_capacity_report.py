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


class ReportNhsJobPlanTeamCapacity(models.AbstractModel):
    """Team capacity report: aggregate DCC/SPA PAs by activity across every
    signed job plan in an org unit's subtree - the service's planned
    weekly capacity."""
    _name = 'report.odoo_nhs_job_planning.report_nhs_job_plan_team_capacity'
    _description = 'Job Plan Team Capacity Report'

    def _get_report_values(self, docids, data=None):
        """ Method for get report values """
        units = self.env['nhs.org.unit'].browse(docids)
        JobPlan = self.env['nhs.job.plan']
        capacity_by_unit = {}
        for unit in units:
            plans = JobPlan.search([
                ('org_unit_id', 'child_of', unit.id),
                ('state', 'in', COMPLETE_STATES),
            ])
            activity_lines = plans.mapped('timetable_activity_ids')
            rows = {}
            for line in activity_lines:
                key = (line.session_category_id.name or line.activity, line.classification)
                row = rows.setdefault(key, {'label': key[0], 'classification': key[1], 'pa': 0.0})
                row['pa'] += line.effective_pa_value
            capacity_by_unit[unit.id] = {
                'doctor_count': len(plans.mapped('post_id')),
                'rows': sorted(rows.values(), key=lambda r: (r['classification'], r['label'])),
            }
        return {
            'doc_ids': docids,
            'doc_model': 'nhs.org.unit',
            'docs': units,
            'capacity_by_unit': capacity_by_unit,
        }
