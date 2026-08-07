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
import csv
import io
from collections import defaultdict
from odoo import api, fields, models
from odoo.exceptions import UserError


class NhsKo41aExportWizard(models.TransientModel):
    """Wizard to generate and export the annual KO41a complaints return as a CSV summary grouped by subject."""
    _name = 'nhs.ko41a.export.wizard'
    _description = 'KO41a Annual Return Export Wizard'

    financial_year = fields.Selection([
        ('2021-22', '2021/22  (Apr 2021 – Mar 2022)'),
        ('2022-23', '2022/23  (Apr 2022 – Mar 2023)'),
        ('2023-24', '2023/24  (Apr 2023 – Mar 2024)'),
        ('2024-25', '2024/25  (Apr 2024 – Mar 2025)'),
        ('2025-26', '2025/26  (Apr 2025 – Mar 2026)'),
        ('2026-27', '2026/27  (Apr 2026 – Mar 2027)'),
        ('2027-28', '2027/28  (Apr 2027 – Mar 2028)'),
    ], string='Financial Year',
       help='Select a financial year to auto-fill the date range, or enter dates manually.')

    date_from = fields.Date(string='From Date', required=True,
                            help='Financial year start (typically 1 April).')
    date_to = fields.Date(string='To Date', required=True,
                          help='Financial year end (typically 31 March).')
    company_id = fields.Many2one('res.company', string='Organisation',
                                 default=lambda self: self.env.company, required=True)
    include_pals = fields.Boolean(string='Include PALS Concerns',
                                  help='Include informal PALS concerns alongside formal complaints in the export.')
    summary_html = fields.Html(string='Summary', readonly=True)
    export_file = fields.Binary(string='Download CSV', readonly=True, attachment=False)
    export_filename = fields.Char(string='Filename', readonly=True)
    unmapped_count = fields.Integer(string='Unmapped Subjects', readonly=True)
    state = fields.Selection([
        ('draft', 'Configure'),
        ('done', 'Ready to Download'),
    ], default='draft')

    @api.onchange('financial_year')
    def _onchange_financial_year(self):
        """Derive the 1 April – 31 March date range from the selected financial year."""
        if self.financial_year:
            start_year = int(self.financial_year.split('-')[0])
            self.date_from = fields.Date.from_string(f'{start_year}-04-01')
            self.date_to = fields.Date.from_string(f'{start_year + 1}-03-31')

    def action_generate(self):
        """Aggregate complaints in the selected date range by KO41a subject code, build the CSV export and HTML summary, and flag unmapped subjects."""
        self.ensure_one()
        record_types = ['complaint', 'pals'] if self.include_pals else ['complaint']
        domain = [
            ('company_id', '=', self.company_id.id),
            ('record_type', 'in', record_types),
            ('received_at', '>=', fields.Datetime.from_string(str(self.date_from))),
            ('received_at', '<=', fields.Datetime.from_string(str(self.date_to) + ' 23:59:59')),
        ]
        complaints = self.env['nhs.complaint'].search(domain)

        record_label = 'complaints/PALS concerns' if self.include_pals else 'formal complaints'
        if not complaints:
            raise UserError(f'No {record_label} found for the selected date range and organisation.')

        aggregated = defaultdict(lambda: {'count': 0, 'complaints': []})
        unmapped = []

        for c in complaints:
            code = c.subject_id.ko41a_code if c.subject_id else None
            if not code:
                unmapped.append(c.name)
                code = 'UNMAPPED'
            subject_name = c.subject_id.complete_name if c.subject_id else 'No Subject'
            key = (code, subject_name, c.location_id.name if c.location_id else 'No Location')
            aggregated[key]['count'] += 1
            aggregated[key]['complaints'].append(c.name)

        # Build CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['KO41a Code', 'Subject', 'Service Area', 'Count', 'Complaint References'])
        rows = []
        for (code, subject, service), data in sorted(aggregated.items()):
            rows.append([code, subject, service, data['count'], '; '.join(data['complaints'])])
            writer.writerow(rows[-1])

        csv_content = output.getvalue()
        encoded = base64.b64encode(csv_content.encode('utf-8'))

        # Build summary HTML
        total = len(complaints)
        total_label = 'Total records (complaints + PALS)' if self.include_pals else 'Total formal complaints received'
        cell_style = 'padding: 6px 10px; border: 1px solid #dee2e6; vertical-align: top; word-break: break-word;'
        rows_html = ''.join(
            f'<tr>'
            f'<td style="{cell_style} width:10%;">{r[0]}</td>'
            f'<td style="{cell_style} width:40%;">{r[1]}</td>'
            f'<td style="{cell_style} width:40%;">{r[2]}</td>'
            f'<td style="{cell_style} width:10%; text-align:center;">{r[3]}</td>'
            f'</tr>'
            for r in rows
        )
        th_style = 'padding: 8px 10px; border: 1px solid #454d55; background-color: #343a40; color: #fff; font-weight: 600; white-space: nowrap;'
        warning_html = (
            f'<div style="padding:10px 14px; margin-bottom:12px; background:#fff3cd; border:1px solid #ffc107; border-radius:4px; color:#856404;">'
            f'&#9888; {len(unmapped)} complaint(s) have no KO41a subject code and are marked UNMAPPED. Correct these before submission.'
            f'</div>'
        ) if unmapped else ''
        summary = f"""
        <h4 style="font-size:18px; font-weight:700; color:#212529; margin:0 0 12px 0; padding:0; line-height:1.3;">KO41a Return Summary</h4>
        <p style="margin:4px 0;"><strong>Period:</strong> {self.date_from} to {self.date_to}</p>
        <p style="margin:4px 0 12px 0;"><strong>{total_label}:</strong> {total}</p>
        {warning_html}
        <table style="width:100%; border-collapse:collapse; table-layout:fixed; margin-top:8px;">
            <colgroup>
                <col style="width:10%;">
                <col style="width:40%;">
                <col style="width:40%;">
                <col style="width:10%;">
            </colgroup>
            <thead>
                <tr>
                    <th style="{th_style}">Code</th>
                    <th style="{th_style}">Subject</th>
                    <th style="{th_style}">Service Area</th>
                    <th style="{th_style} text-align:center;">Count</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        """

        filename = f'KO41a_{self.date_from}_{self.date_to}_{self.company_id.name.replace(" ", "_")}.csv'
        self.write({
            'export_file': encoded,
            'export_filename': filename,
            'summary_html': summary,
            'unmapped_count': len(unmapped),
            'state': 'done',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
