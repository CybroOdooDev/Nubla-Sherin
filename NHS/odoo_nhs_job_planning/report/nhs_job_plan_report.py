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


class ReportNhsJobPlan(models.AbstractModel):
    """The individual job plan PDF - the formal agreed document."""
    _name = 'report.odoo_nhs_job_planning.report_nhs_job_plan'
    _description = 'Job Plan Report'

    def _get_report_values(self, docids, data=None):
        """ Method for get report values """
        plans = self.env['nhs.job.plan'].browse(docids)
        return {'doc_ids': docids, 'doc_model': 'nhs.job.plan', 'docs': plans}
