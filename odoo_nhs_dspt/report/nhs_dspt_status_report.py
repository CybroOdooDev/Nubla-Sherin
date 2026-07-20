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


class ReportDsptStatus(models.AbstractModel):
    """Report parser for the DSPT Status PDF report."""
    _name = 'report.odoo_nhs_dspt.report_nhs_dspt_status_view'
    _description = 'DSPT Status QWeb PDF Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepares template values for the DSPT Status report."""
        assessments = self.env['nhs.dspt.assessment'].browse(docids) if docids else \
            self.env['nhs.dspt.assessment']._default_report_assessments()
        standard_rows = []
        outstanding_rows = []
        for assessment in assessments:
            for standard in assessment.assertion_ids.standard_id.sorted('sequence'):
                evidence = assessment.evidence_ids.filtered(
                    lambda e, std=standard: e.standard_id == std and e.is_mandatory
                    and e.status != 'not_applicable')
                total = len(evidence) or 1
                met = len(evidence.filtered(lambda e: e.status == 'met'))
                standard_rows.append({
                    'assessment': assessment,
                    'name': standard.name,
                    'rate': round(met / total * 100.0, 1),
                    'met': met,
                    'total': len(evidence),
                })
            outstanding = assessment.evidence_ids.filtered(
                lambda e: e.is_mandatory and e.status == 'not_met')
            for evidence in outstanding:
                outstanding_rows.append({
                    'assessment': assessment,
                    'standard': evidence.standard_id.name,
                    'reference': evidence.reference,
                    'name': evidence.name,
                    'owner': evidence.owner_id.name or '-',
                })

        return {
            'doc_ids': assessments.ids,
            'doc_model': 'nhs.dspt.assessment',
            'docs': assessments,
            'standard_rows': standard_rows,
            'outstanding_rows': outstanding_rows,
            'generated_on': fields.Date.context_today(self),
        }
