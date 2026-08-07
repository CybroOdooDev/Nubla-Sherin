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

class ReportEstateRegister(models.AbstractModel):
    """Abstract model for custom estate register report data loading.
    Loads the dataset for the Estate Register PDF report. If no specific
    IDs are provided (e.g. when run from the Reporting menu), it defaults
    to loading all active sites in the system.
    """
    _name = 'report.odoo_nhs_estate.report_estate_register'
    _description = 'Estate Register Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Retrieve report data, returning all sites if no specific IDs are provided.
        Args:
            docids (list): List of site record IDs to print.
            data (dict): Optional additional report execution context data.
        Returns:
            dict: The template rendering data context.
        """
        if not docids:
            docs = self.env['nhs.estate.site'].search([])
        else:
            docs = self.env['nhs.estate.site'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'nhs.estate.site',
            'docs': docs,
        }
