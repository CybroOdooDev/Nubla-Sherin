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


class ReportNhsRosterPersonalRota(models.AbstractModel):
    """The personal rota PDF: one member's published/worked duties -
    what staff take away/print for themselves."""
    _name = 'report.odoo_nhs_rostering.report_nhs_roster_personal_rota'
    _description = 'Personal Rota Report'

    def _get_report_values(self, docids, data=None):
        members = self.env['nhs.workforce.member'].browse(docids)
        return {'doc_ids': docids, 'doc_model': 'nhs.workforce.member', 'docs': members}
