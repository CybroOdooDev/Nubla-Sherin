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
#############################################################################
import base64
import csv
import io
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError


class NhsKo41aExportWizard(models.TransientModel):
    _name = 'nhs.ko41a.export.wizard'
    _description = 'KO41a Annual Return Export Wizard'

    date_from = fields.Date(string='From Date', required=True,
                            help='Financial year start (typically 1 April).')
    date_to = fields.Date(string='To Date', required=True,
                          help='Financial year end (typically 31 March).')
    company_id = fields.Many2one('res.company', string='Organisation',
                                 default=lambda self: self.env.company, required=True)
    include_pals = fields.Boolean(string='Include PALS Concerns',
                                  help='Include informal PALS concerns in the export (separate from formal complaints).')

    # Result fields
    summary_html = fields.Html(string='Summary', readonly=True)
    export_file = fields.Binary(string='Download CSV', readonly=True, attachment=False)
    export_filename = fields.Char(string='Filename', readonly=True)
    unmapped_count = fields.Integer(string='Unmapped Subjects', readonly=True)
    state = fields.Selection([
        ('draft', 'Configure'),
        ('done', 'Ready to Download'),
    ], default='draft')

    def action_generate(self):
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('record_type', '=', 'complaint'),
            ('received_at', '>=', fields.Datetime.from_string(str(self.date_from))),
            ('received_at', '<=', fields.Datetime.from_string(str(self.date_to) + ' 23:59:59')),
        ]
        complaints = self.env['nhs.complaint'].search(domain)

        if not complaints:
            raise UserError('No formal complaints found for the selected date range and organisation.')

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
        rows_html = ''.join(
            f'<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td class="text-end">{r[3]}</td></tr>'
            for r in rows
        )
        summary = f"""
        <h4>KO41a Return Summary</h4>
        <p><strong>Period:</strong> {self.date_from} to {self.date_to}</p>
        <p><strong>Total formal complaints received:</strong> {total}</p>
        {'<div class="alert alert-warning">⚠️ ' + str(len(unmapped)) + ' complaint(s) have no KO41a subject code and are marked UNMAPPED. Correct these before submission.</div>' if unmapped else ''}
        <table class="table table-sm table-bordered mt-3">
            <thead class="table-dark"><tr><th>Code</th><th>Subject</th><th>Service Area</th><th>Count</th></tr></thead>
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
