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

class NHSCompliancePAMWizard(models.TransientModel):
    """Wizard to export compliance rates and latest test evidence in a format aligned with NHS Premises
    Assurance Model (PAM) Safety Domain."""
    _name = 'nhs.compliance.pam.wizard'
    _description = 'PAM Safety-Domain Evidence Extract Wizard'

    discipline_id = fields.Many2one('nhs.compliance.discipline', string='Discipline',
                                    help='Filter the PAM extract by a specific compliance discipline.')
    data = fields.Binary(string='Export File', readonly=True,
                         help='The generated Excel file containing the PAM Safety Domain extract.')
    filename = fields.Char(string='Filename', readonly=True,
                           help='The filename of the generated PAM Safety Domain extract.')
    statutory_filter = fields.Selection([
        ('all', 'All records '),
        ('statutory', 'Statutory records only'),
        ('non_statutory', 'Non-statutory (advisory/good-practice) records only')
    ], string='Statutory Filter', default='all', required=True,
       help='Toggle to filter the report records by their statutory classification.')

    def action_export_excel(self):
        """Generate a formatted Excel sheet with PAM safety-domain compliance rates and latest evidence reference."""
        as_at_date = fields.Date.today()
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
        worksheet = workbook.add_worksheet('PAM Safety Domain')
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
        pct_format = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#FFFFFF',
                                                'num_format': '0.0"%"'})
        pct_format_zebra = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#F1F5F9',
                                                'num_format': '0.0"%"'})
        green_format = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#C6EFCE',
                                                'font_color': '#006100', 'bold': True})
        amber_format = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#FFEB9C',
                                                'font_color': '#9C6500', 'bold': True})
        red_format = workbook.add_format({**cell_base, 'align': 'center', 'bg_color': '#FFC7CE',
                                                'font_color': '#9C0006', 'bold': True})
        worksheet.set_column(0, 0, 28)
        worksheet.set_column(1, 1, 24)
        worksheet.set_column(2, 5, 12)
        worksheet.set_column(6, 6, 16)
        worksheet.set_column(7, 7, 14)
        worksheet.set_column(8, 10, 24)
        if logo_path:
            worksheet.set_row(0, 50)
            worksheet.insert_image(0, 0, logo_path, {'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5, 'y_offset': 5})
            worksheet.merge_range(0, 1, 0, 10, 'NHS Estates Premises Assurance Model (PAM) - '
                                               'Safety Domain Evidence Extract', title_format)
        else:
            worksheet.merge_range(0, 0, 0, 10, 'NHS Estates Premises Assurance Model (PAM) - '
                                               'Safety Domain Evidence Extract', title_format)
            worksheet.set_row(0, 36)
        disc_name = 'All Disciplines'
        statutory_label = dict(self._fields['statutory_filter'].selection).get(self.statutory_filter, 'All Records')
        meta_text = (f"Till Date: {as_at_date.strftime('%Y-%m-%d')}  |  Discipline Filter: {disc_name} |"
                     f" Statutory Filter: {statutory_label}")
        worksheet.merge_range(1, 0, 1, 10, meta_text, meta_format)
        worksheet.set_row(1, 22)
        worksheet.set_row(2, 12)
        headers = [
            'Safety Domain / Discipline', 'HTM / Legislation Ref', 'Total Items', 'Compliant',
            'Overdue', 'Failed', 'Compliance Rate', 'RAG Status',
            'Latest Certificate Ref', 'Latest Test Date', 'Latest Test Outcome'
        ]
        for col, h in enumerate(headers):
            worksheet.write(3, col, h, header_format)
        worksheet.set_row(3, 28)
        disciplines = self.env['nhs.compliance.discipline'].search([])
        matching_items_domain = [
            ('discipline_id', 'in', disciplines.ids),
            ('active', '=', True)
        ]
        if self.statutory_filter == 'statutory':
            matching_items_domain.append(('compliance_type_id.is_statutory', '=', True))
        elif self.statutory_filter == 'non_statutory':
            matching_items_domain.append(('compliance_type_id.is_statutory', '=', False))
        matching_items = self.env['nhs.compliance.item'].search(matching_items_domain)
        matching_items = matching_items.filtered(lambda i: i.create_date.date() <= as_at_date)
        if not matching_items:
            raise UserError("No value")
        row = 4
        for d in disciplines:
            item_domain = [
                ('discipline_id', '=', d.id),
                ('active', '=', True)
            ]
            if self.statutory_filter == 'statutory':
                item_domain.append(('compliance_type_id.is_statutory', '=', True))
            elif self.statutory_filter == 'non_statutory':
                item_domain.append(('compliance_type_id.is_statutory', '=', False))
            items = self.env['nhs.compliance.item'].search(item_domain)
            items = items.filtered(lambda i: i.create_date.date() <= as_at_date)
            if not items:
                continue
            total = len(items)
            compliant = 0
            overdue = 0
            failed = 0
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
                    failed += 1
                elif not next_due_date:
                    pass
                elif next_due_date < as_at_date:
                    overdue += 1
                elif (next_due_date - as_at_date).days <= item.lead_days:
                    pass
                else:
                    compliant += 1
            rate = (compliant / total * 100.0) if total else 100.0
            if rate >= 95.0:
                rag = 'GREEN'
                fmt_rag = green_format
            elif rate >= 85.0:
                rag = 'AMBER'
                fmt_rag = amber_format
            else:
                rag = 'RED'
                fmt_rag = red_format
            latest_test_domain = [
                ('item_id.discipline_id', '=', d.id),
                ('certificate_ref', '!=', False),
                ('active', '=', True),
                ('test_date', '<=', as_at_date)
            ]
            if self.statutory_filter == 'statutory':
                latest_test_domain.append(('item_id.compliance_type_id.is_statutory', '=', True))
            elif self.statutory_filter == 'non_statutory':
                latest_test_domain.append(('item_id.compliance_type_id.is_statutory', '=', False))
            latest_test = self.env['nhs.compliance.test'].search(latest_test_domain, order='test_date desc', limit=1)
            cert_ref = latest_test.certificate_ref if latest_test else 'No Evidence'
            test_date = latest_test.test_date.strftime('%Y-%m-%d') if latest_test and latest_test.test_date else 'N/A'
            test_outcome = latest_test.outcome.upper().replace('_', ' ') if latest_test else 'N/A'
            use_zebra = (row % 2 == 1)
            fmt_l = cell_left_zebra if use_zebra else cell_left
            fmt_c = cell_center_zebra if use_zebra else cell_center
            fmt_pct = pct_format_zebra if use_zebra else pct_format
            worksheet.write(row, 0, d.name, fmt_l)
            ref_str = f"{d.htm_reference or ''} {d.legislation_reference or ''}".strip() or 'N/A'
            worksheet.write(row, 1, ref_str, fmt_l)
            worksheet.write(row, 2, total, fmt_c)
            worksheet.write(row, 3, compliant, fmt_c)
            worksheet.write(row, 4, overdue, fmt_c)
            worksheet.write(row, 5, failed, fmt_c)
            worksheet.write(row, 6, rate, fmt_pct)
            worksheet.write(row, 7, rag, fmt_rag)
            worksheet.write(row, 8, cert_ref, fmt_l)
            worksheet.write(row, 9, test_date, fmt_c)
            worksheet.write(row, 10, test_outcome, fmt_l)
            worksheet.set_row(row, 20)
            row += 1
        if row > 4:
            worksheet.autofilter(3, 0, row - 1, 10)
        workbook.close()
        output.seek(0)
        self.data = base64.b64encode(output.getvalue())
        self.filename = f"pam_safety_domain_extract_{fields.Date.today()}.xlsx"
        if logo_path:
            try:
                os.unlink(logo_path)
            except Exception:
                pass
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/nhs.compliance.pam.wizard/{self.id}/data/{self.filename}?download=true",
            'target': 'self',
        }
