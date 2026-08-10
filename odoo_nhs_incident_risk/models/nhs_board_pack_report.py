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
from odoo import api, fields, models

class ReportBoardPack(models.AbstractModel):
    _name = 'report.odoo_nhs_incident_risk.report_board_pack'
    _description = 'Monthly Board Pack Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        # When printing from a menu item directly, docids is empty.
        # Fallback to the current active company.
        if not docids:
            docids = [self.env.company.id]
        docs = self.env['res.company'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'res.company',
            'docs': docs,
            'today_date': fields.Date.context_today(self),
        }
