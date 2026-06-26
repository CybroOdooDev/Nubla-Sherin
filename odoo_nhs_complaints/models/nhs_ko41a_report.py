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
#############################################################################
import datetime
from odoo import api, fields, models


class ReportNhsKo41a(models.AbstractModel):
    _name = 'report.odoo_nhs_complaints.report_nhs_ko41a'
    _description = 'KO41a Board Pack Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            docids = self.env['nhs.complaint'].search([
                ('company_id', '=', self.env.company.id),
                ('record_type', '=', 'complaint')
            ]).ids
        docs = self.env['nhs.complaint'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'nhs.complaint',
            'docs': docs,
            'datetime': datetime,
        }
