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

class ReportEricReturn(models.AbstractModel):
    """QWeb PDF report parser for ERIC Return report."""
    _name = 'report.odoo_nhs_eric.report_nhs_eric_return_template'
    _description = 'NHS ERIC Return Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['nhs.eric.return'].browse(docids) if docids else self.env['nhs.eric.return'].search([])
        if not docs:
            raise UserError("No ERIC Return records found. Report generation cancelled.")
        return {
            'doc_ids': docids,
            'doc_model': 'nhs.eric.return',
            'docs': docs,
        }

class ReportEricGap(models.AbstractModel):
    """QWeb PDF report parser for ERIC Gap report."""
    _name = 'report.odoo_nhs_eric.report_nhs_eric_gap_template'
    _description = 'NHS ERIC Gap Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['nhs.eric.return'].browse(docids) if docids else self.env['nhs.eric.return'].search([])
        if not docs:
            raise UserError("No ERIC Return records found. Report generation cancelled.")
        return {
            'doc_ids': docids,
            'doc_model': 'nhs.eric.return',
            'docs': docs,
        }
