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

class NHSComplianceERICExportWizard(models.TransientModel):
    """Transient wizard for exporting compliance data to a formatted ERIC Excel workbook."""
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

    def _get_filtered_items(self, as_at_date):
        """Get filtered compliance items based on wizard criteria."""
        domain = [('active', '=', True)]
        if self.discipline_id:
            domain.append(('discipline_id', '=', self.discipline_id.id))
        if self.site_id:
            domain.append(('site_id', '=', self.site_id.id))
        if self.compliance_type_id:
            domain.append(('compliance_type_id', '=', self.compliance_type_id.id))
        if self.statutory_filter == 'statutory':
            domain.append(('compliance_type_id.is_statutory', '=', True))
        elif self.statutory_filter == 'non_statutory':
            domain.append(('compliance_type_id.is_statutory', '=', False))
        items = self.env['nhs.compliance.item'].sudo().search(domain)
        items = items.filtered(lambda i: i.create_date.date() <= as_at_date)
        return items

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

    def _get_site_data(self, as_at_date):
        """Get comprehensive site data."""
        site_domain = []
        if self.site_id:
            site_domain.append(('id', '=', self.site_id.id))
        sites = self.env['nhs.estate.site'].sudo().search(site_domain)
        if not sites and not self.site_id:
            sites = self.env['nhs.estate.site'].sudo().search([])
        site_data = []
        for site in sites:
            buildings = self.env['nhs.estate.building'].sudo().search([('site_id', '=', site.id)])
            spaces = self.env['nhs.estate.space'].sudo().search([('site_id', '=', site.id)])
            item_domain = [
                ('site_id', '=', site.id),
                ('active', '=', True)
            ]
            if self.discipline_id:
                item_domain.append(('discipline_id', '=', self.discipline_id.id))
            if self.compliance_type_id:
                item_domain.append(('compliance_type_id', '=', self.compliance_type_id.id))
            if self.statutory_filter == 'statutory':
                item_domain.append(('compliance_type_id.is_statutory', '=', True))
            elif self.statutory_filter == 'non_statutory':
                item_domain.append(('compliance_type_id.is_statutory', '=', False))

            items = self.env['nhs.compliance.item'].sudo().search(item_domain)
            items = items.filtered(lambda i: i.create_date.date() <= as_at_date)

            tests = self.env['nhs.compliance.test'].sudo().search([
                ('item_site_id', '=', site.id),
                ('active', '=', True)
            ])
            remedials = self.env['nhs.compliance.remedial'].sudo().search([
                ('item_id.site_id', '=', site.id)
            ])
            equipment_ids = items.mapped('equipment_id').ids
            equipments = self.env['maintenance.equipment'].sudo().search([
                ('id', 'in', equipment_ids)
            ]) if equipment_ids else self.env['maintenance.equipment']
            maintenance_requests = 0
            try:
                maintenance_requests = self.env['maintenance.request'].sudo().search_count([
                    ('equipment_id', 'in', equipment_ids)
                ]) if equipment_ids else 0
            except:
                maintenance_requests = 0

            stats = self._get_compliance_stats(items, as_at_date)
            overdue_items = len(items.filtered(lambda i: self._get_item_status(i, as_at_date) == 'overdue'))
            failed_items = len(items.filtered(lambda i: self._get_item_status(i, as_at_date) == 'failed'))
            due_soon_items = len(items.filtered(lambda i: self._get_item_status(i, as_at_date) == 'due_soon'))
            survey_count = len(tests)
            backlog_count = len(
                items.filtered(lambda i: self._get_item_status(i, as_at_date) not in ['compliant', 'due_soon']))
            site_data.append({
                'site': site,
                'building_count': len(buildings),
                'space_count': len(spaces),
                'item_count': len(items),
                'test_count': len(tests),
                'remedial_count': len(remedials),
                'equipment_count': len(equipments),
                'survey_count': survey_count,
                'backlog_count': backlog_count,
                'overdue_items': overdue_items,
                'failed_items': failed_items,
                'due_soon_items': due_soon_items,
                'maintenance_requests': maintenance_requests,
                'compliance_rate': stats['compliance_rate'],
                'compliant_items': stats['compliant'],
                'items': items,
            })
        return site_data

    def _write_site_section(self, worksheet, row, formats, workbook,
                            site_info, site_index, as_at_date):
        """Write a complete site section with all details - clean one column layout."""
        site = site_info['site']
        site_title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'font_name': 'Segoe UI',
            'font_color': '#FFFFFF',
            'bg_color': '#005EB8',
            'align': 'center',
            'valign': 'vcenter'
        })
        if site_index > 0:
            row += 2
        worksheet.merge_range(row, 0, row, 2, f'SITE: {site.name or "N/A"}', site_title_format)
        worksheet.set_row(row, 30)
        row += 2
        worksheet.merge_range(row, 0, row, 2, 'SITE OVERVIEW', formats['section_header'])
        row += 1
        address = site.street if hasattr(site, 'street') and site.street else 'N/A'
        postcode = site.zip if hasattr(site, 'zip') and site.zip else 'N/A'
        city = site.city if hasattr(site, 'city') and site.city else 'N/A'
        site_data = [
            ('Site Code', site.code or 'N/A'),
            ('Site Name', site.name or 'N/A'),
            ('Address', address),
            ('Postcode', postcode),
            ('City', city),
        ]
        for label, value in site_data:
            label_format = workbook.add_format({
                'font_name': 'Segoe UI',
                'font_size': 10,
                'align': 'left',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#E2E8F0',
                'bold': True
            })
            value_format = workbook.add_format({
                'font_name': 'Segoe UI',
                'font_size': 10,
                'align': 'left',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#E2E8F0'
            })
            worksheet.write(row, 0, label, label_format)
            worksheet.write(row, 1, str(value), value_format)
            row += 1
        row += 1
        worksheet.merge_range(row, 0, row, 2, 'SITE STATISTICS', formats['section_header'])
        row += 1
        stats_data = [
            ('Buildings', site_info['building_count']),
            ('Spaces', site_info['space_count']),
            ('Compliance Items', site_info['item_count']),
            ('Surveys/Tests', site_info['survey_count']),
            ('Remedial Actions', site_info['remedial_count']),
            ('Equipment', site_info['equipment_count']),
        ]
        for label, value in stats_data:
            label_format = workbook.add_format({
                'font_name': 'Segoe UI',
                'font_size': 10,
                'align': 'left',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#E2E8F0',
                'bold': True
            })
            value_format = workbook.add_format({
                'font_name': 'Segoe UI',
                'font_size': 10,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#E2E8F0'
            })
            worksheet.write(row, 0, label, label_format)
            worksheet.write(row, 1, value, value_format)
            row += 1
        row += 1
        worksheet.merge_range(row, 0, row, 2, 'COMPLIANCE STATUS', formats['section_header'])
        row += 1
        compliance_data = [
            ('Total Items', site_info['item_count']),
            ('Compliant Items', site_info['compliant_items']),
            ('Compliance Rate', f"{site_info['compliance_rate']:.1f}%"),
            ('Overdue Items', site_info['overdue_items']),
            ('Failed Items', site_info['failed_items']),
            ('Due Soon Items', site_info['due_soon_items']),
            ('Backlog Items', site_info['backlog_count']),
            ('Maintenance Requests', site_info['maintenance_requests']),
        ]
        for label, value in compliance_data:
            label_format = workbook.add_format({
                'font_name': 'Segoe UI',
                'font_size': 10,
                'align': 'left',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#E2E8F0',
                'bold': True
            })
            value_format = workbook.add_format({
                'font_name': 'Segoe UI',
                'font_size': 10,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#E2E8F0'
            })
            worksheet.write(row, 0, label, label_format)
            worksheet.write(row, 1, str(value), value_format)
            row += 1
        row += 1
        if site_info['items']:
            worksheet.merge_range(row, 0, row, 4, 'DISCIPLINE BREAKDOWN', formats['section_header'])
            row += 1
            header_format = workbook.add_format({
                'bold': True,
                'font_size': 10,
                'font_name': 'Segoe UI',
                'font_color': '#FFFFFF',
                'bg_color': '#0A2240',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#E2E8F0'
            })
            worksheet.write(row, 0, 'Discipline', header_format)
            worksheet.write(row, 1, 'Total', header_format)
            worksheet.write(row, 2, 'Compliant', header_format)
            worksheet.write(row, 3, 'Non-Compliant', header_format)
            worksheet.write(row, 4, 'Compliance %', header_format)
            row += 1
            discipline_groups = {}
            for item in site_info['items']:
                disc = item.discipline_id
                if disc:
                    if disc.id not in discipline_groups:
                        discipline_groups[disc.id] = {
                            'name': disc.name,
                            'total': 0,
                            'compliant': 0,
                            'non_compliant': 0
                        }
                    discipline_groups[disc.id]['total'] += 1
                    status = self._get_item_status(item, as_at_date)
                    if status in ['compliant', 'due_soon']:
                        discipline_groups[disc.id]['compliant'] += 1
                    else:
                        discipline_groups[disc.id]['non_compliant'] += 1
            for disc_id, disc_info in discipline_groups.items():
                cell_format = workbook.add_format({
                    'font_name': 'Segoe UI',
                    'font_size': 10,
                    'align': 'left',
                    'valign': 'vcenter',
                    'border': 1,
                    'border_color': '#E2E8F0'
                })
                cell_format_center = workbook.add_format({
                    'font_name': 'Segoe UI',
                    'font_size': 10,
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 1,
                    'border_color': '#E2E8F0'
                })
                compliance_pct = (disc_info['compliant'] / disc_info['total'] * 100) if disc_info['total'] > 0 else 0
                worksheet.write(row, 0, disc_info['name'], cell_format)
                worksheet.write(row, 1, disc_info['total'], cell_format_center)
                worksheet.write(row, 2, disc_info['compliant'], cell_format_center)
                worksheet.write(row, 3, disc_info['non_compliant'], cell_format_center)
                worksheet.write(row, 4, f"{compliance_pct:.1f}%", cell_format_center)
                row += 1
        return row

    def action_export_excel(self):
        """Generate the complete ERIC Excel workbook with site-by-site sections."""
        as_at_date = fields.Date.today()
        company = self.env.company
        site_data = self._get_site_data(as_at_date)
        if not site_data:
            raise UserError("No sites or compliance records found matching your criteria.")
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
        worksheet = workbook.add_worksheet('ERIC Compliance Report')
        formats = {}
        formats['title'] = workbook.add_format({
            'bold': True,
            'font_size': 18,
            'font_name': 'Segoe UI',
            'font_color': '#FFFFFF',
            'bg_color': '#005EB8',
            'align': 'center',
            'valign': 'vcenter'
        })
        formats['section_header'] = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'font_name': 'Segoe UI',
            'font_color': '#005EB8',
            'bg_color': '#E1EDF7',
            'align': 'left',
            'valign': 'vcenter',
            'bottom': 2,
            'bottom_color': '#005EB8'
        })
        worksheet.set_column(0, 0, 30)
        worksheet.set_column(1, 1, 35)
        worksheet.set_column(2, 2, 30)
        worksheet.set_column(3, 3, 30)
        worksheet.set_column(4, 4, 30)
        row = 0
        if logo_path:
            worksheet.set_row(row, 60)
            worksheet.insert_image(row, 0, logo_path, {'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5, 'y_offset': 5})
            worksheet.merge_range(row, 1, row, 4, 'ERIC DATA EXTRACT', formats['title'])
        else:
            worksheet.merge_range(row, 0, row, 4, 'ERIC DATA EXTRACT', formats['title'])
            worksheet.set_row(row, 40)
        row += 2
        trust_info_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 11,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#F8FAFC',
            'border': 1,
            'border_color': '#E2E8F0'
        })
        worksheet.write(row, 0, 'Organisation :', trust_info_format)
        worksheet.merge_range(row, 1, row, 2, company.name or 'N/A', trust_info_format)
        row += 1
        worksheet.write(row, 0, 'Return Period :', trust_info_format)
        worksheet.merge_range(row, 1, row, 2, f"{as_at_date.year - 1}/{as_at_date.year}", trust_info_format)
        row += 1
        worksheet.write(row, 0, 'Generated :', trust_info_format)
        worksheet.merge_range(row, 1, row, 2, as_at_date.strftime('%Y-%m-%d'), trust_info_format)
        row += 2
        for idx, site_info in enumerate(site_data):
            row = self._write_site_section(worksheet, row, formats, workbook, site_info, idx, as_at_date)
            row += 1
        workbook.close()
        output.seek(0)
        self.data = base64.b64encode(output.getvalue())
        self.filename = f"eric_compliance_export_{fields.Date.today()}.xlsx"
        if logo_path:
            try:
                os.unlink(logo_path)
            except Exception:
                pass
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/nhs.compliance.eric.export.wizard/{self.id}/data/{self.filename}?download=true",
            'target': 'self',
        }
