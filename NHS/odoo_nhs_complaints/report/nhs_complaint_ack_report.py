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
from odoo import api, models
from odoo.exceptions import UserError


class ReportNhsComplaintAck(models.AbstractModel):
    """Report parser supplying the QWeb data for the formal complaint acknowledgement letter."""
    _name = 'report.odoo_nhs_complaints.report_nhs_complaint_ack'
    _description = 'NHS Complaint Acknowledgement Letter'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Build the rendering context for the acknowledgement letter, restricted to formal complaints."""
        docs = self.env['nhs.complaint'].browse(docids)
        for doc in docs:
            if doc.record_type != 'complaint':
                raise UserError("The Acknowledgement Letter is only applicable to Formal Complaints.")
        return {
            'doc_ids': docids,
            'doc_model': 'nhs.complaint',
            'docs': docs,
        }
