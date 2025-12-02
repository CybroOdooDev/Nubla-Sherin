# -*- coding: utf-8 -*-
#######################################################################################
#
#    Hai Cheung (China) Limited
#
#    Copyright (C) Hai Cheung (China) Limited.
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
########################################################################################
from odoo import models, fields,api
from datetime import datetime

class HrContract(models.Model):
    _inherit = 'hr.contract'


    zx_code = fields.Char(
        string="Contract Sequence",
        compute="_compute_zx_code",
        store=True,

    )

    @api.depends('date_start')
    def _compute_zx_code(self):
        for rec in self:
            if rec.date_start:
                date_str = rec.date_start.strftime('%Y%m%d')

                # count all other records with same date_start
                count = self.search_count([
                    ('date_start', '=', rec.date_start),
                    ('id', '!=', rec.id),
                ]) + 1

                rec.zx_code = f"ZX{date_str}{str(count).zfill(2)}"
            else:
                rec.zx_code = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._compute_zx_code()
        return records

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        emp_contract_report_id = self.env.ref('hc_employee_megawin_contract_report.action_report_megawin_employee_contract').id
        for view in res['views'].values():
            toolbar = view.get('toolbar', {})
            if 'print' in toolbar:
                if self.env.company.id != 4:
                    toolbar['print'] = [
                        rpt for rpt in toolbar['print']
                        if rpt.get('id') != emp_contract_report_id
                    ]
                view['toolbar'] = toolbar
        return res


