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
import datetime
from odoo import api, models
from odoo.exceptions import UserError


class ReportNhsKo41a(models.AbstractModel):
    """Report parser supplying the QWeb data for the KO41a board pack summary of formal complaints."""
    _name = 'report.odoo_nhs_complaints.report_nhs_ko41a'
    _description = 'KO41a Board Pack Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Build the rendering context for the KO41a report, defaulting to all of the company's formal complaints when no docids are given."""
        if not docids:
            docids = self.env['nhs.complaint'].search([
                ('company_id', '=', self.env.company.id),
                ('record_type', '=', 'complaint')
            ]).ids
        docs = self.env['nhs.complaint'].browse(docids)
        for doc in docs:
            if doc.record_type != 'complaint':
                raise UserError("The KO41a Complaint Return is only applicable to Formal Complaints.")
        return {
            'doc_ids': docids,
            'doc_model': 'nhs.complaint',
            'docs': docs,
            'datetime': datetime,
        }
