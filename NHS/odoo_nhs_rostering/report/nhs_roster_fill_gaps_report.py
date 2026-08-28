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


class ReportNhsRosterFillGaps(models.AbstractModel):
    """Fill & gaps report: demand vs assigned per duty, with escalation
    status - the evidence trail for safe-staffing/CQC review."""
    _name = 'report.odoo_nhs_rostering.report_nhs_roster_fill_gaps'
    _description = 'Fill & Gaps Report'

    def _get_report_values(self, docids, data=None):
        periods = self.env['nhs.roster.period'].browse(docids)
        return {'doc_ids': docids, 'doc_model': 'nhs.roster.period', 'docs': periods}
