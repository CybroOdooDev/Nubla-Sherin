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


class ReportTrainingBoard(models.AbstractModel):
    _name = 'report.odoo_nhs_training.report_nhs_training_board_view'
    _description = 'Board Assurance QWeb PDF Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        units = self.env['nhs.org.unit'].browse(docids) if docids else \
            self.env['nhs.org.unit'].search([('parent_id', '=', False)])
        target = float(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_training.compliance_target', 85))

        members = self.env['nhs.workforce.member']
        for unit in units:
            members |= self.env['nhs.workforce.member'].search([
                ('org_unit_id', 'child_of', unit.id), ('is_leaver', '=', False)])
        total_required = sum(members.mapped('required_subject_count'))
        total_compliant = sum(members.mapped('compliant_subject_count'))
        overall_rate = (total_compliant / total_required * 100.0) if total_required else 100.0

        staff_group_stats = []
        for group in members.mapped('staff_group_id'):
            group_members = members.filtered(lambda m: m.staff_group_id == group)
            required = sum(group_members.mapped('required_subject_count'))
            compliant = sum(group_members.mapped('compliant_subject_count'))
            staff_group_stats.append({
                'name': group.name,
                'rate': round((compliant / required * 100.0) if required else 0.0, 1),
                'member_count': len(group_members),
            })

        team_stats = [{
            'name': unit.complete_name,
            'rate': round(unit.team_compliance_pct, 1),
            'member_count': unit.member_count,
        } for unit in units]

        registrations = self.env['nhs.registration'].search([('member_id', 'in', members.ids)])
        lapsed = registrations.filtered(lambda r: r.status == 'lapsed')

        return {
            'doc_ids': units.ids,
            'doc_model': 'nhs.org.unit',
            'docs': units,
            'target': target,
            'overall_rate': round(overall_rate, 1),
            'total_members': len(members),
            'non_compliant_count': len(members.filtered(lambda m: m.compliance_status == 'non_compliant')),
            'staff_group_stats': sorted(staff_group_stats, key=lambda s: s['rate']),
            'team_stats': sorted(team_stats, key=lambda s: s['rate']),
            'lapsed_registrations': lapsed,
            'generated_on': fields.Date.context_today(self),
        }


class ReportTrainingCertificate(models.AbstractModel):
    _name = 'report.odoo_nhs_training.report_nhs_training_certificate_view'
    _description = 'Certificate of Completion QWeb PDF Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['nhs.training.record'].browse(docids)
        return {
            'doc_ids': records.ids,
            'doc_model': 'nhs.training.record',
            'docs': records,
            'generated_on': fields.Date.context_today(self),
        }


class ReportIndividualRecord(models.AbstractModel):
    _name = 'report.odoo_nhs_training.report_nhs_individual_record_view'
    _description = 'Individual Training Record QWeb PDF Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
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
