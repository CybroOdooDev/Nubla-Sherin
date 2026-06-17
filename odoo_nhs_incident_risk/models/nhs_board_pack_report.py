# -*- coding: utf-8 -*-
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
