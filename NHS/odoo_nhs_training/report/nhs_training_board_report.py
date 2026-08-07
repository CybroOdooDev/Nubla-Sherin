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


class ReportTrainingBoard(models.AbstractModel):
    _name = 'report.odoo_nhs_training.report_nhs_training_board_view'
    _description = 'Board Assurance QWeb PDF Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Aggregate compliance figures for the org units in ``docids`` (or
        all top-level units if none given): the overall and per-staff-group
        compliance rates against the configured target, per-team compliance
        stats, and lapsed registrations, for the Board Assurance PDF."""
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
