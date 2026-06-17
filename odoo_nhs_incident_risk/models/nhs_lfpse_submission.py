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
import json
import csv
import io
import base64


class NhsLfpseSubmission(models.Model):
    _name = 'nhs.lfpse.submission'
    _description = 'LFPSE Export Batch'
    _order = 'id desc'

    name = fields.Char(string='Batch Reference', required=True, readonly=True,
                       default='New', copy=False,
                       help='Auto-generated unique reference for this LFPSE export batch.')
    incident_ids = fields.Many2many('nhs.incident', string='Incidents',
                                    domain=[('lfpse_state', 'in', ['pending', 'exported'])],
                                    help='The incidents included in this export batch. '
                                         'Only incidents with LFPSE status "Pending" or "Exported" are eligible.')
    export_format = fields.Selection([
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ], string='Export Format', required=True, default='csv',
       help='The file format for the LFPSE export. CSV for spreadsheet upload; '
            'JSON for API-compatible submissions to the NHS England LFPSE portal.')
    file_attachment_id = fields.Many2one('ir.attachment', string='Export File',
                                         help='The generated export file attached to this batch record for download.')
    submitted = fields.Boolean(string='Submitted to LFPSE',
                               help='Tick once the export file has been uploaded to the NHS England LFPSE portal.')
    submitted_at = fields.Datetime(string='Submitted At',
                                   help='The date and time this batch was formally submitted to the LFPSE portal.')
    taxonomy_version = fields.Char(string='Taxonomy Version', default='LFPSE-2023-v1',
                                   help='The LFPSE taxonomy version used to format the export. '
                                        'Update if NHS England releases a new taxonomy version.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('exported', 'Exported'),
        ('submitted', 'Submitted'),
    ], default='draft',
       help='The current status of this export batch: Draft while being prepared, '
            'Exported once the file has been generated, Submitted once uploaded to LFPSE.')

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('nhs.lfpse.submission') or 'New'
        return super().create(vals_list)

    def action_export(self):
        self.ensure_one()
        data = self._build_export_data()
        if self.export_format == 'json':
            content = json.dumps(data, indent=2).encode('utf-8')
            filename = f'{self.name}.json'
            mimetype = 'application/json'
        else:
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            content = output.getvalue().encode('utf-8')
            filename = f'{self.name}.csv'
            mimetype = 'text/csv'

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(content),
            'mimetype': mimetype,
            'res_model': self._name,
            'res_id': self.id,
        })
        self.write({'file_attachment_id': attachment.id, 'state': 'exported'})
        for incident in self.incident_ids:
            incident.with_context(nhs_workflow=True).write({'lfpse_state': 'exported'})
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _build_export_data(self):
        rows = []
        for inc in self.incident_ids:
            rows.append({
                'batch_ref': self.name,
                'taxonomy_version': self.taxonomy_version,
                'incident_ref': inc.name,
                'event_type': inc.incident_kind,
                'occurred_at': str(inc.occurred_at) if inc.occurred_at else '',
                'location': inc.location_id.complete_name if inc.location_id else '',
                'category': inc.category_id.complete_name if inc.category_id else '',
                'physical_harm': inc.physical_harm or '',
                'psychological_harm': inc.psychological_harm or '',
                'harm_grade': inc.harm_grade or '',
                'description': inc.description or '',
            })
        return rows

    def action_mark_submitted(self):
        self.ensure_one()
        self.write({'submitted': True, 'submitted_at': fields.Datetime.now(),
                    'state': 'submitted'})
        for incident in self.incident_ids:
            incident.with_context(nhs_workflow=True).write({'lfpse_state': 'submitted'})
