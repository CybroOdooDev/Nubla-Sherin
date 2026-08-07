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

STATUS_LABELS = {
    'compliant': 'Compliant', 'due_soon': 'Due Soon', 'expired': 'Expired',
    'failed': 'Failed', 'not_done': 'Not Done', 'exempt': 'Exempt',
}


class ReportIndividualRecord(models.AbstractModel):
    _name = 'report.odoo_nhs_training.report_nhs_individual_record_view'
    _description = 'Individual Training Record QWeb PDF Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Build, for each member in ``docids``, a sorted list of per-subject
        rows (status, label, latest expiry/completion date) for the
        Individual Training Record PDF."""
        members = self.env['nhs.workforce.member'].browse(docids)
        lines_by_member = members.get_requirement_lines()
        member_data = []
        for member in members:
            rows = []
            for line in sorted(lines_by_member.get(member.id, []), key=lambda l: l['subject'].name):
                status = member._subject_status(line['subject'], line['lead_days'], line['exempt'])
                latest = member.record_ids.filtered(lambda r: r.subject_id.id == line['subject'].id)
                latest = latest.sorted('completion_date', reverse=True)[:1]
                rows.append({
                    'subject': line['subject'].complete_name,
                    'status': status,
                    'label': STATUS_LABELS.get(status, status),
                    'expiry_date': latest.expiry_date if latest else False,
                    'completion_date': latest.completion_date if latest else False,
                })
            member_data.append({'member': member, 'rows': rows})

        return {
            'doc_ids': members.ids,
            'doc_model': 'nhs.workforce.member',
            'docs': members,
            'member_data': member_data,
            'generated_on': fields.Date.context_today(self),
        }
