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


class ReportNhsVacancyRegister(models.AbstractModel):
    """QWeb report parser for the vacancy register report, printed per
    establishment post."""
    _name = 'report.odoo_nhs_establishment.report_nhs_vacancy_register'
    _description = 'NHS Vacancy Register Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Build the rendering context for the selected posts."""
        docs = self.env['nhs.establishment.post'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'nhs.establishment.post',
            'docs': docs,
            'datetime': datetime,
        }
