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


class ReportTrainingCertificate(models.AbstractModel):
    _name = 'report.odoo_nhs_training.report_nhs_training_certificate_view'
    _description = 'Certificate of Completion QWeb PDF Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Fetch the training records in ``docids`` to render as Certificates
        of Completion."""
        records = self.env['nhs.training.record'].browse(docids)
        return {
            'doc_ids': records.ids,
            'doc_model': 'nhs.training.record',
            'docs': records,
            'generated_on': fields.Date.context_today(self),
        }
