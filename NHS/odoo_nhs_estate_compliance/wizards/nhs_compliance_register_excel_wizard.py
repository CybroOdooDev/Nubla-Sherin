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
from odoo import fields, models
from odoo.exceptions import UserError
from io import BytesIO
import base64
import xlsxwriter
import tempfile
import os
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class NHSComplianceRegisterExcelWizard(models.TransientModel):
    """Wizard to export the full compliance register including items,schedules, and statuses to a styled Excel sheet."""
    _name = 'nhs.compliance.register.excel.wizard'
    _description = 'Full Compliance Register Excel Export Wizard'

    date = fields.Date(string='As At Date', default=fields.Date.today,
                       help='Specify the point-in-time reference date for the compliance register export.')
    data = fields.Binary(string='Export File', readonly=True,
                         help='The generated Excel file containing the Compliance Register.')
    filename = fields.Char(string='Filename', readonly=True,
                           help='The filename of the generated compliance register Excel sheet.')
    statutory_filter = fields.Selection([
        ('all', 'All records '),
        ('statutory', 'Statutory records only'),
        ('non_statutory', 'Non-statutory (advisory/good-practice) records only')
    ], string='Statutory Filter', default='all', required=True,
       help='Toggle to filter the report records by their statutory classification.')

    def action_export_excel(self):
        """Generate a styled Excel workbook showing all compliance item details, scheduled dates, and statuses."""
        as_at_date = self.date or fields.Date.today()
        domain = [('active', '=', True)]
        if self.statutory_filter == 'statutory':
            domain.append(('compliance_type_id.is_statutory', '=', True))
        elif self.statutory_filter == 'non_statutory':
            domain.append(('compliance_type_id.is_statutory', '=', False))
        items = self.env['nhs.compliance.item'].search(domain)
        items = items.filtered(lambda i: i.create_date.date() <= as_at_date)
        if not items:
            raise UserError("No value")
        # Handle Logo Extraction
        company = self.env.company
        logo_path = False
        if company.logo:
            try:
                logo_data = base64.b64decode(company.logo)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                temp_file.write(logo_data)
                temp_file.close()
                logo_path = temp_file.name
            except Exception:
                pass
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Compliance Register')
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_name': 'Segoe UI',
            'font_color': '#FFFFFF',
            'bg_color': '#005EB8',
            'align': 'center',
            'valign': 'vcenter'
        })
        meta_format = workbook.add_format({
            'font_size': 10,
            'font_name': 'Segoe UI',
            'font_color': '#475569',
            'italic': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F8FAFC'
        })
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'font_name': 'Segoe UI',
            'font_color': '#FFFFFF',
            'bg_color': '#0A2240',
            'border': 1,
            'border_color': '#E2E8F0',
            'align': 'center',
            'valign': 'vcenter'
        })
        cell_base = {
            'font_name': 'Segoe UI',
            'font_size': 10,
            'border': 1,
            'border_color': '#E2E8F0',
            'valign': 'vcenter'
        }
        cell_left = workbook.add_format({**cell_base, 'align': 'left', 'bg_color': '#FFFFFF'})
        cell_left_zebra = workbook.add_format({**cell_base, 'align': 'left', 'bg_color': '#F1F5F9'})
        cell_center = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#FFFFFF'})
        cell_center_zebra = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#F1F5F9'})
        status_compliant = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#C6EFCE',
                                                  'font_color': '#006100', 'bold': True})
        status_due_soon = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#FFEB9C',
                                                  'font_color': '#9C6500', 'bold': True})
        status_overdue = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#FFC7CE',
                                                  'font_color': '#9C0006', 'bold': True})
        worksheet.set_column(0, 0, 14)
        worksheet.set_column(1, 1, 38)
        worksheet.set_column(2, 2, 22)
        worksheet.set_column(3, 3, 22)
        worksheet.set_column(4, 6, 18)
        worksheet.set_column(7, 7, 18)
        worksheet.set_column(8, 8, 24)
        worksheet.set_column(9, 9, 15)
        worksheet.set_column(10, 11, 15)
        worksheet.set_column(12, 12, 16)
        worksheet.set_column(13, 13, 24)
        worksheet.set_column(14, 14, 15)
        if logo_path:
            worksheet.set_row(0, 50)
            worksheet.insert_image(0, 0, logo_path, {'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5, 'y_offset': 5})
            worksheet.merge_range(0, 1, 0, 14, 'NHS Estates Compliance Register', title_format)
        else:
            worksheet.merge_range(0, 0, 0, 14, 'NHS Estates Compliance Register', title_format)
            worksheet.set_row(0, 36)
        export_date = as_at_date.strftime('%Y-%m-%d')
        meta_text = f"Export Date: {export_date}  |  Total Active Compliance Obligations: {len(items)}"
        worksheet.merge_range(1, 0, 1, 14, meta_text, meta_format)
        worksheet.set_row(1, 22)
        worksheet.set_row(2, 12)
        headers = [
            'Reference', 'Obligation Name', 'Discipline', 'Compliance Type',
            'Site', 'Building', 'Space', 'Delivery Method', 'Contractor',
            'Frequency', 'Last Completed', 'Next Due Date', 'Status',
            'Responsible Person', 'Open Remedials'
        ]
        for col, h in enumerate(headers):
            worksheet.write(3, col, h, header_format)
        worksheet.set_row(3, 28)
        row = 4
        for item in items:
            tests = item.test_ids.filtered(lambda t: t.active and t.test_date and
                                                     t.test_date <= as_at_date)
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
                next_due_date = item._adjust_to_working_day(raw_due_date)
            else:
                if item.next_due_date and item.create_date.date() <= as_at_date:
                    next_due_date = item.next_due_date
            if latest_test and latest_test.outcome in ['fail', 'remedial_required']:
                status = 'failed'
            elif not next_due_date:
                status = 'not_applicable'
            elif next_due_date < as_at_date:
                status = 'overdue'
            elif (next_due_date - as_at_date).days <= item.lead_days:
                status = 'due_soon'
            else:
                status = 'compliant'
            open_remedial_count = 0
            for r in item.remedial_ids:
                if r.create_date.date() <= as_at_date:
                    if r.state not in ['completed', 'verified']:
                        open_remedial_count += 1
                    elif r.verified_at and r.verified_at.date() > as_at_date:
                        open_remedial_count += 1
            use_zebra = (row % 2 == 1)
            fmt_l = cell_left_zebra if use_zebra else cell_left
            fmt_c = cell_center_zebra if use_zebra else cell_center
            worksheet.write(row, 0, item.reference or '', fmt_c)
            worksheet.write(row, 1, item.name or '', fmt_l)
            worksheet.write(row, 2, item.discipline_id.name or '', fmt_l)
            worksheet.write(row, 3, item.compliance_type_id.name or '', fmt_l)
            worksheet.write(row, 4, item.site_id.name or '', fmt_l)
            worksheet.write(row, 5, item.building_id.name or '', fmt_l)
            worksheet.write(row, 6, item.space_id.name or '', fmt_l)
            worksheet.write(row, 7, dict(item._fields['delivery_method'].selection).get(
                item.delivery_method, ''), fmt_l)
            worksheet.write(row, 8, item.contractor_id.name or '', fmt_l)
            worksheet.write(row, 9, f"{item.frequency_value} {item.frequency_unit}", fmt_c)
            worksheet.write(row, 10, last_completed.strftime('%Y-%m-%d') if last_completed else '', fmt_c)
            worksheet.write(row, 11, next_due_date.strftime('%Y-%m-%d') if next_due_date else '', fmt_c)
            if status == 'compliant':
                fmt_status = status_compliant
            elif status == 'due_soon':
                fmt_status = status_due_soon
            elif status in ('overdue', 'failed'):
                fmt_status = status_overdue
            else:
                fmt_status = fmt_c
            worksheet.write(row, 12, status.upper().replace('_', ' '), fmt_status)
            worksheet.write(row, 13, item.responsible_person_id.name or '', fmt_l)
            worksheet.write(row, 14, open_remedial_count, fmt_c)
            worksheet.set_row(row, 20)
            row += 1
        if row > 4:
            worksheet.autofilter(3, 0, row - 1, 14)
        workbook.close()
        output.seek(0)
        self.data = base64.b64encode(output.getvalue())
        self.filename = f"compliance_register_export_{as_at_date}.xlsx"
        if logo_path:
            try:
                os.unlink(logo_path)
            except Exception:
                pass
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/nhs.compliance.register.excel.wizard/{self.id}/data/{self.filename}?download=true",
            'target': 'self',
        }
