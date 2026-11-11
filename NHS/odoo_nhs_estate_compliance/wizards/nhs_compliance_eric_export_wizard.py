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
import base64
from io import BytesIO
import xlsxwriter
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError

class NHSComplianceERICExportWizardLine(models.TransientModel):
    """Line model to preview aggregated compliance status by building and discipline for ERIC export."""
    _name = 'nhs.compliance.eric.export.wizard.line'
    _description = 'ERIC Compliance Export Preview Line'

    wizard_id = fields.Many2one('nhs.compliance.eric.export.wizard', string='Wizard', ondelete='cascade')
    site_id = fields.Many2one('nhs.estate.site', string='Site')
    building_id = fields.Many2one('nhs.estate.building', string='Building')
    discipline_id = fields.Many2one('nhs.compliance.discipline', string='Discipline')
    total_items = fields.Integer(string='Total Items')
    compliant_items = fields.Integer(string='Compliant Items')
    overdue_items = fields.Integer(string='Overdue Items')
    failed_items = fields.Integer(string='Failed Items')
    due_soon_items = fields.Integer(string='Due Soon Items')
    compliance_rate = fields.Float(string='Compliance Rate (%)')
    is_data_gap = fields.Boolean(string='Data Gap', help='True if building/discipline has no compliance items configured.')
    data_gap_warning = fields.Char(string='Data Gap Flag')


class NHSComplianceERICExportWizard(models.TransientModel):
    """Transient wizard for exporting building compliance matrix data to an ERIC Excel workbook."""
    _name = 'nhs.compliance.eric.export.wizard'
    _description = 'ERIC Compliance Export'

    site_id = fields.Many2one('nhs.estate.site', string='Site')
    discipline_id = fields.Many2one('nhs.compliance.discipline', string='Discipline')
    compliance_type_id = fields.Many2one('nhs.compliance.type',
                                         domain="[('discipline_id', '=', discipline_id )]", string='Compliance Type')
    data = fields.Binary(string='Export Data', readonly=True)
    filename = fields.Char(string='Filename', readonly=True)
    statutory_filter = fields.Selection([
        ('all', 'All records'),
        ('statutory', 'Statutory records only'),
        ('non_statutory', 'Non-statutory (advisory/good-practice) records only')
    ], string='Statutory Filter', default='all', required=True)
    line_ids = fields.One2many('nhs.compliance.eric.export.wizard.line', 'wizard_id', string='Preview & Data Gaps',
                               help='Aggregated compliance status by building and discipline with data gap indicators.')
    data_gap_count = fields.Integer(string='Data Gap Count', compute='_compute_data_gap_count')

    @api.depends('line_ids', 'line_ids.is_data_gap')
    def _compute_data_gap_count(self):
        for wizard in self:
            wizard.data_gap_count = len(wizard.line_ids.filtered(lambda l: l.is_data_gap))

    def _get_item_status(self, item, as_at_date):
        """Calculate the status of a single item."""
        tests = item.test_ids.filtered(
            lambda t: t.active and t.test_date and t.test_date <= as_at_date
        )
        latest_test = tests.sorted('test_date', reverse=True)[:1]
        last_completed = latest_test.test_date if latest_test else False
        next_due_date = False
        if last_completed:
            if item.frequency_unit == 'day':
                delta = timedelta(days=item.frequency_value)
            elif item.frequency_unit == 'week':
                delta = timedelta(weeks=item.frequency_value)
            elif item.frequency_unit == 'month':
                delta = relativedelta(months=item.frequency_value)
            elif item.frequency_unit == 'year':
                delta = relativedelta(years=item.frequency_value)
            else:
                delta = relativedelta(months=1)
            raw_due_date = last_completed + delta
            if hasattr(item, '_adjust_to_working_day'):
                next_due_date = item._adjust_to_working_day(raw_due_date)
            else:
                next_due_date = raw_due_date
        else:
            if item.next_due_date and item.create_date.date() <= as_at_date:
                next_due_date = item.next_due_date

        if latest_test and latest_test.outcome in ['fail', 'remedial_required']:
            return 'failed'
        elif not next_due_date:
            return 'not_applicable'
        elif next_due_date < as_at_date:
            return 'overdue'
        elif (next_due_date - as_at_date).days <= (item.lead_days or 0):
            return 'due_soon'
        else:
            return 'compliant'

    def _get_compliance_stats(self, items, as_at_date):
        """Calculate compliance statistics."""
        total = len(items)
        if total == 0:
            return {
                'total': 0,
                'compliant': 0,
                'failed': 0,
                'overdue': 0,
                'due_soon': 0,
                'not_applicable': 0,
                'compliance_rate': 0.0
            }
        compliant = 0
        failed = 0
        overdue = 0
        due_soon = 0
        not_applicable = 0
        for item in items:
            status = self._get_item_status(item, as_at_date)
            if status == 'compliant':
                compliant += 1
            elif status == 'failed':
                failed += 1
            elif status == 'overdue':
                overdue += 1
            elif status == 'due_soon':
                due_soon += 1
            else:
                not_applicable += 1
        active = total - not_applicable
        compliance_rate = (compliant / active * 100.0) if active > 0 else 0.0
        return {
            'total': total,
            'compliant': compliant,
            'failed': failed,
            'overdue': overdue,
            'due_soon': due_soon,
            'not_applicable': not_applicable,
            'compliance_rate': compliance_rate
        }

    def action_preview(self):
        """Aggregate compliance status by discipline and building into preview lines, flagging data gaps."""
        self.ensure_one()
        self.line_ids.unlink()
        as_at_date = fields.Date.today()
        b_domain = [('active', '=', True)]
        if self.site_id:
            b_domain.append(('site_id', '=', self.site_id.id))
        buildings = self.env['nhs.estate.building'].sudo().search(b_domain)
        d_domain = []
        if self.discipline_id:
            d_domain.append(('id', '=', self.discipline_id.id))
        disciplines = self.env['nhs.compliance.discipline'].sudo().search(d_domain)
        lines_vals = []
        for bld in buildings:
            for disc in disciplines:
                all_item_domain = [
                    ('active', '=', True),
                    ('building_id', '=', bld.id),
                    ('discipline_id', '=', disc.id),
                ]
                filtered_item_domain = all_item_domain.copy()
                if self.compliance_type_id:
                    filtered_item_domain.append(('compliance_type_id', '=', self.compliance_type_id.id))
                if self.statutory_filter == 'statutory':
                    filtered_item_domain.append(('compliance_type_id.is_statutory', '=', True))
                elif self.statutory_filter == 'non_statutory':
                    filtered_item_domain.append(('compliance_type_id.is_statutory', '=', False))
                all_items = self.env['nhs.compliance.item'].sudo().search(all_item_domain)
                filtered_items = self.env['nhs.compliance.item'].sudo().search(filtered_item_domain)
                include_combination = False
                is_gap = False
                warning_text = "OK"
                if self.statutory_filter == 'all':
                    include_combination = True
                    if not all_items:
                        is_gap = True
                        warning_text = "DATA GAP: No compliance items for this building/discipline"
                    else:
                        is_gap = False
                        warning_text = "OK"
                else:
                    if filtered_items:
                        include_combination = True
                        is_gap = False
                        warning_text = "OK"
                        if len(filtered_items) < len(all_items):
                            filter_type = "statutory" if self.statutory_filter == 'statutory' else "non-statutory"
                            warning_text = f"Has {len(all_items)} total items, {len(filtered_items)} {filter_type}"
                    else:
                        continue
                if include_combination:
                    stats = self._get_compliance_stats(filtered_items, as_at_date)
                    lines_vals.append({
                        'wizard_id': self.id,
                        'building_id': bld.id,
                        'site_id': bld.site_id.id,
                        'discipline_id': disc.id,
                        'total_items': stats['total'],
                        'compliant_items': stats['compliant'],
                        'overdue_items': stats['overdue'],
                        'failed_items': stats['failed'],
                        'due_soon_items': stats['due_soon'],
                        'compliance_rate': stats['compliance_rate'],
                        'is_data_gap': is_gap,
                        'data_gap_warning': warning_text,
                    })
        if lines_vals:
            self.env['nhs.compliance.eric.export.wizard.line'].create(lines_vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.compliance.eric.export.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_export_excel(self):
        """Generate the ERIC Building Compliance Matrix Excel workbook."""
        as_at_date = fields.Date.today()
        company = self.env.company
        if not self.line_ids:
            self.action_preview()
        if not self.line_ids:
            raise UserError("No building compliance matrix data found matching your criteria.")
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        matrix_ws = workbook.add_worksheet('Building Compliance Matrix')
        matrix_ws.set_column(0, 0, 26)
        matrix_ws.set_column(1, 1, 28)
        matrix_ws.set_column(2, 2, 28)
        matrix_ws.set_column(3, 3, 15)
        matrix_ws.set_column(4, 4, 15)
        matrix_ws.set_column(5, 5, 15)
        matrix_ws.set_column(6, 6, 18)
        matrix_ws.set_column(7, 7, 52)
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 16, 'font_name': 'Segoe UI', 'font_color': '#FFFFFF',
            'bg_color': '#005EB8', 'align': 'center', 'valign': 'vcenter'
        })
        info_label_fmt = workbook.add_format({
            'font_name': 'Segoe UI', 'font_size': 10, 'bold': True, 'align': 'left', 'valign': 'vcenter',
            'bg_color': '#F8FAFC', 'border': 1, 'border_color': '#E2E8F0', 'indent': 1
        })
        info_val_fmt = workbook.add_format({
            'font_name': 'Segoe UI', 'font_size': 10, 'align': 'left', 'valign': 'vcenter',
            'bg_color': '#FFFFFF', 'border': 1, 'border_color': '#E2E8F0', 'indent': 1
        })
        card_lbl_fmt = workbook.add_format({
            'font_name': 'Segoe UI', 'font_size': 9, 'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#F1F5F9', 'border': 1, 'border_color': '#CBD5E1', 'font_color': '#475569'
        })
        card_val_fmt = workbook.add_format({
            'font_name': 'Segoe UI', 'font_size': 14, 'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#FFFFFF', 'border': 1, 'border_color': '#CBD5E1', 'font_color': '#005EB8'
        })
        card_gap_val_fmt = workbook.add_format({
            'font_name': 'Segoe UI', 'font_size': 14, 'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#FFFFFF', 'border': 1, 'border_color': '#CBD5E1', 'font_color': '#D97706'
        })
        hdr_fmt = workbook.add_format({
            'bold': True, 'font_size': 10, 'font_name': 'Segoe UI', 'bg_color': '#0A2240', 'font_color': '#FFFFFF',
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': '#E2E8F0'
        })
        m_row = 0
        matrix_ws.merge_range(m_row, 0, m_row, 7, 'ERIC BUILDING COMPLIANCE MATRIX RETURN', title_fmt)
        matrix_ws.set_row(m_row, 38)
        m_row += 2
        matrix_ws.set_row(m_row, 20)
        matrix_ws.write(m_row, 0, 'Organisation :', info_label_fmt)
        matrix_ws.merge_range(m_row, 1, m_row, 7, company.name or 'N/A', info_val_fmt)
        m_row += 1
        matrix_ws.set_row(m_row, 20)
        matrix_ws.write(m_row, 0, 'Return Period :', info_label_fmt)
        matrix_ws.merge_range(m_row, 1, m_row, 7, f"{as_at_date.year - 1}/{as_at_date.year}", info_val_fmt)
        m_row += 1
        matrix_ws.set_row(m_row, 20)
        matrix_ws.write(m_row, 0, 'Generated Date :', info_label_fmt)
        matrix_ws.merge_range(m_row, 1, m_row, 7, as_at_date.strftime('%Y-%m-%d'), info_val_fmt)
        m_row += 2
        total_pairs = len(self.line_ids)
        gap_pairs = len(self.line_ids.filtered(lambda l: l.is_data_gap))
        ok_pairs = total_pairs - gap_pairs
        matrix_ws.merge_range(m_row, 0, m_row, 2, 'Total Building x Discipline Pairs', card_lbl_fmt)
        matrix_ws.merge_range(m_row, 3, m_row, 5, 'Configured Combinations', card_lbl_fmt)
        matrix_ws.merge_range(m_row, 6, m_row, 7, 'Data Gaps Flagged', card_lbl_fmt)
        m_row += 1
        matrix_ws.set_row(m_row, 26)
        matrix_ws.merge_range(m_row, 0, m_row, 2, total_pairs, card_val_fmt)
        matrix_ws.merge_range(m_row, 3, m_row, 5, ok_pairs, card_val_fmt)
        matrix_ws.merge_range(m_row, 6, m_row, 7, gap_pairs, card_gap_val_fmt)
        m_row += 2
        headers = ['Site', 'Building', 'Discipline', 'Total Items', 'Compliant', 'Overdue', 'Compliance %', 'Data Gap Status']
        matrix_ws.set_row(m_row, 26)
        for c_idx, h in enumerate(headers):
            matrix_ws.write(m_row, c_idx, h, hdr_fmt)
        m_row += 1
        for r_idx, line in enumerate(self.line_ids):
            bg = '#F8FAFC' if r_idx % 2 == 1 else '#FFFFFF'
            cell_left = workbook.add_format({
                'font_name': 'Segoe UI', 'font_size': 10, 'align': 'left', 'valign': 'vcenter',
                'bg_color': bg, 'border': 1, 'border_color': '#E2E8F0', 'indent': 1
            })
            cell_center = workbook.add_format({
                'font_name': 'Segoe UI', 'font_size': 10, 'align': 'center', 'valign': 'vcenter',
                'bg_color': bg, 'border': 1, 'border_color': '#E2E8F0'
            })
            cell_right = workbook.add_format({
                'font_name': 'Segoe UI', 'font_size': 10, 'align': 'right', 'valign': 'vcenter',
                'bg_color': bg, 'border': 1, 'border_color': '#E2E8F0'
            })
            gap_status_fmt = workbook.add_format({
                'font_name': 'Segoe UI', 'font_size': 10, 'bold': True, 'align': 'left', 'valign': 'vcenter',
                'bg_color': bg, 'border': 1, 'border_color': '#E2E8F0', 'indent': 1,
                'font_color': '#B45309' if line.is_data_gap else '#15803D'
            })
            matrix_ws.set_row(m_row, 22)
            matrix_ws.write(m_row, 0, line.site_id.name or '', cell_left)
            matrix_ws.write(m_row, 1, line.building_id.name or '', cell_left)
            matrix_ws.write(m_row, 2, line.discipline_id.name or '', cell_left)
            matrix_ws.write(m_row, 3, line.total_items, cell_right)
            matrix_ws.write(m_row, 4, line.compliant_items, cell_right)
            matrix_ws.write(m_row, 5, line.overdue_items, cell_right)
            matrix_ws.write(m_row, 6, f"{line.compliance_rate:.1f}%", cell_right)
            status_text = f"⚠️ {line.data_gap_warning}" if line.is_data_gap else "✔ Configured"
            matrix_ws.write(m_row, 7, status_text, gap_status_fmt)
            m_row += 1
        workbook.close()
        output.seek(0)
        self.data = base64.b64encode(output.getvalue())
        self.filename = f"eric_building_compliance_matrix_{fields.Date.today()}.xlsx"
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/nhs.compliance.eric.export.wizard/{self.id}/data/{self.filename}?download=true",
            'target': 'self',
        }
