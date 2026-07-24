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


class ReportBoardPack(models.AbstractModel):
    _name = 'report.odoo_nhs_governance.report_board_pack'
    _description = 'Board / Committee Pack Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids and data:
            docids = data.get('doc_ids') or data.get('ids') or data.get('active_ids')
        if not docids:
            docids = self.env.context.get('active_ids') or self.env.context.get('active_id')
        if isinstance(docids, int):
            docids = [docids]
        docs = self.env['nhs.meeting'].browse(docids) if docids else self.env['nhs.meeting']
        if not docs:
            docs = self.env['nhs.meeting'].search([('state', '!=', 'cancelled')], limit=1, order='meeting_date desc') or self.env['nhs.meeting'].search([], limit=1)
        include_confidential = bool(
            (data or {}).get('include_confidential') or self.env.context.get('include_confidential')
        )
        return {
            'doc_ids': docs.ids,
            'doc_model': 'nhs.meeting',
            'docs': docs,
            'include_confidential': include_confidential,
        }
