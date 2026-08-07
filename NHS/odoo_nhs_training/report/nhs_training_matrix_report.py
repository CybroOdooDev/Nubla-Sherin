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

# Subject columns per printed page. A landscape A4 page is wide enough for the
# Member/Team columns plus about this many status columns before content would
# run past the printable margin and get silently clipped by the PDF engine.
MATRIX_SUBJECTS_PER_PAGE = 8


class ReportTrainingMatrix(models.AbstractModel):
    _name = 'report.odoo_nhs_training.report_nhs_training_matrix_view'
    _description = 'Team Training Matrix QWeb PDF Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Build per-page rows of member x subject status cells for the Team
        Training Matrix PDF: gather the members in ``docids`` (or all active
        members) and their required subjects, compute each member's status
        per subject, then chunk the subject columns into landscape-page-sized
        groups (``MATRIX_SUBJECTS_PER_PAGE``)."""
        members = self.env['nhs.workforce.member'].browse(docids) if docids else \
            self.env['nhs.workforce.member'].search([('is_leaver', '=', False)])
        lines_by_member = members.get_requirement_lines()
        subjects = self.env['nhs.training.subject']
        for lines in lines_by_member.values():
            subjects |= self.env['nhs.training.subject'].browse([l['subject'].id for l in lines])
        subjects = subjects.sorted(key=lambda s: (s.name, s.level or ''))

        rows = []
        for member in members:
            cells = []
            for subject in subjects:
                line = next((l for l in lines_by_member.get(member.id, [])
                             if l['subject'].id == subject.id), None)
                if not line:
                    cells.append({'status': '', 'label': '—'})
                    continue
                status = member._subject_status(subject, line['lead_days'], line['exempt'])
                cells.append({'status': status, 'label': STATUS_LABELS.get(status, status)})
            rows.append({'member': member, 'cells': cells})

        subjects_list = list(subjects)
        chunk_starts = range(0, len(subjects_list), MATRIX_SUBJECTS_PER_PAGE) or [0]
        pages = [{
            'subjects': subjects_list[start:start + MATRIX_SUBJECTS_PER_PAGE],
            'rows': [{
                'member': row['member'],
                'cells': row['cells'][start:start + MATRIX_SUBJECTS_PER_PAGE],
            } for row in rows],
        } for start in chunk_starts]

        return {
            'doc_ids': members.ids,
            'doc_model': 'nhs.workforce.member',
            'docs': members,
            'subjects': subjects,
            'rows': rows,
            'pages': pages,
            'generated_on': fields.Date.context_today(self),
        }
