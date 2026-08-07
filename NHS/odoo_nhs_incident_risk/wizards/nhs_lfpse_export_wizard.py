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


class NhsLfpseExportWizard(models.TransientModel):
    """Wizard to select a date range and generate an LFPSE export batch."""
    _name = 'nhs.lfpse.export.wizard'
    _description = 'LFPSE Export Wizard'

    date_from = fields.Date(string='From', required=True,
                            help='Start date of the incident date range to include in this export batch.')
    date_to = fields.Date(string='To', required=True, default=fields.Date.today,
                          help='End date of the incident date range to include in this export batch.')
    export_format = fields.Selection([
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ], string='Format', required=True, default='csv',
       help='File format for the LFPSE export. '
            'CSV for manual spreadsheet upload to the LFPSE portal; '
            'JSON for API-compatible submission.')
    incident_ids = fields.Many2many('nhs.incident', string='Incidents to Export',
                                    compute='_compute_incidents',
                                    help='Incidents with LFPSE status "Pending" that fall within the selected date range. '
                                         'These will be included in the generated export file.')
    incident_count = fields.Integer(compute='_compute_incidents',
                                    help='Number of eligible incidents found in the selected date range.')

    @api.depends('date_from', 'date_to')
    def _compute_incidents(self):
        """Find pending LFPSE incidents within the selected date range."""
        for rec in self:
            if rec.date_from and rec.date_to:
                incidents = self.env['nhs.incident'].search([
                    ('lfpse_state', '=', 'pending'),
                    ('occurred_at', '>=', fields.Datetime.from_string(
                        str(rec.date_from) + ' 00:00:00')),
                    ('occurred_at', '<=', fields.Datetime.from_string(
                        str(rec.date_to) + ' 23:59:59')),
                ])
                rec.incident_ids = incidents
                rec.incident_count = len(incidents)
            else:
                rec.incident_ids = False
                rec.incident_count = 0

    def action_export(self):
        """Create an LFPSE submission batch for the eligible incidents and export it."""
        self.ensure_one()
        if not self.incident_ids:
            from odoo.exceptions import UserError
            raise UserError('No pending incidents found in the selected date range.')
        batch = self.env['nhs.lfpse.submission'].create({
            'export_format': self.export_format,
            'incident_ids': [(6, 0, self.incident_ids.ids)],
        })
        return batch.action_export()
