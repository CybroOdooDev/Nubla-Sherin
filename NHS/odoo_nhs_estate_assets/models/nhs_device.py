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
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta

class NHSDevice(models.Model):
    _name = 'nhs.device'
    _description = 'NHS Medical Device / Equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Device Name',
        compute='_compute_name',
        store=True,
        help='Display name of the device, automatically generated from '
             'category, model, and serial number.'
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='User-friendly display name for the device.'
    )
    asset_tag = fields.Char(
        string='Asset Tag',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help='Unique asset identification number. Auto-sequenced on creation. '
             'Can be encoded as barcode/QR for scanning.'
    )
    barcode = fields.Char(
        string='Barcode / QR Code',
        compute='_compute_barcode',
        store=True,
        readonly=False,
        copy=False,
        help='Barcode or QR code value for scanning device asset tags.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help='Owning organisation. Used for multi-company record isolation.'
    )
    category_id = fields.Many2one(
        'nhs.device.category',
        string='Category',
        required=True,
        help='Device category which groups similar devices and provides '
             'default values for life expectancy and maintenance schedules.'
    )
    is_medical_device = fields.Boolean(
        string='Is Medical Device',
        default=True,
        help='Check if this is a regulated medical device (requires UKCA/CE marking). '
             'Uncheck for general equipment that doesn\'t require regulatory oversight.'
    )
    create_maintenance_equipment = fields.Boolean(
        string='Create Maintenance Equipment',
        default=False,
        help='If checked, automatically creates and links a corresponding Odoo Maintenance Equipment '
             'record for this device.'
    )
    manufacturer = fields.Char(
        string='Manufacturer',
        help='Name of the device manufacturer.'
    )
    model = fields.Char(
        string='Model',
        help='Device model number or name.'
    )
    serial_number = fields.Char(
        string='Serial Number',
        help='Unique serial number from the manufacturer.'
    )
    device_class = fields.Selection(
        selection=[
            ('I', 'Class I'),
            ('IIa', 'Class IIa'),
            ('IIb', 'Class IIb'),
            ('III', 'Class III'),
        ],
        string='Device Class',
        help='Regulatory classification of the medical device according to UK/MDR. '
             'Class I is lowest risk, Class III is highest risk.'
    )
    marking = fields.Selection(
        selection=[
            ('ukca', 'UKCA'),
            ('ce', 'CE'),
            ('other', 'Other'),
        ],
        string='Conformity Marking',
        help='Regulatory conformity marking applied to the device. '
             'UKCA for UK market, CE for EU/European market.'
    )
    site_id = fields.Many2one(
        'nhs.estate.site',
        string='Site',
        help='Primary site where the device is located. '
             'Linked from the Estate Register module.'
    )
    building_id = fields.Many2one(
        'nhs.estate.building',
        string='Building',
        domain="[('site_id', '=', site_id)]" if site_id else [],
        help='Building where the device is located. '
             'Should be under the selected site.'
    )
    space_id = fields.Many2one(
        'nhs.estate.space',
        string='Space',
        domain="[('building_id', '=', building_id)]" if building_id else [],
        help='Specific room or space where the device is located.'
    )
    department = fields.Char(
        string='Department',
        help='Owning department or service area.'
    )
    cost_centre = fields.Char(
        string='Cost Centre',
        help='Financial cost centre for the device.'
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Responsible User',
        help='Person responsible for the device (usually EBME/Clinical Engineering staff).'
    )
    status = fields.Selection(
        selection=[
            ('in_service', 'In Service'),
            ('awaiting_repair', 'Awaiting Repair'),
            ('out_of_service', 'Out of Service'),
            ('decommissioned', 'Decommissioned'),
            ('disposed', 'Disposed'),
        ],
        string='Status',
        required=True,
        default='in_service',
        tracking=True,
        help='Current lifecycle status of the device.\n'
             '- In Service: Normal operational use\n'
             '- Awaiting Repair: Removed from use awaiting repair\n'
             '- Out of Service: Temporarily unavailable\n'
             '- Decommissioned: Removed from service, not yet disposed\n'
             '- Disposed: Permanently removed and disposed'
    )
    image = fields.Binary(
        string='Photo',
        attachment=True,
        help='Photo of the device for visual identification.'
    )
    acquisition_date = fields.Date(
        string='Acquisition Date',
        help='Date the device was purchased or acquired.'
    )
    in_service_date = fields.Date(
        string='In Service Date',
        help='Date the device was first put into operational service.'
    )
    acquisition_cost = fields.Monetary(
        string='Acquisition Cost',
        currency_field='currency_id',
        help='Purchase cost of the device.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency of the acquisition cost and indicative value.'
    )
    funding_source = fields.Selection(
        selection=[
            ('capital', 'Capital'),
            ('charitable', 'Charitable'),
            ('grant', 'Grant'),
            ('leased', 'Leased'),
            ('donated', 'Donated'),
        ],
        string='Funding Source',
        help='How the device was funded. Used for capital planning and reporting.'
    )
    expected_life_years = fields.Integer(
        string='Expected Life (Years)',
        help='Expected economic/service life in years. '
             'Defaults from the device category. '
             'Used to compute the replacement year and indicative value.'
    )
    expected_replacement_date = fields.Date(
        string='Expected Replacement Date',
        compute='_compute_expected_replacement_date',
        store=True,
        readonly=False,
        help='Date when the device is due for replacement based on acquisition date and expected life.'
    )
    estimated_replacement_cost = fields.Monetary(
        string='Estimated Replacement Cost',
        currency_field='currency_id',
        compute='_compute_estimated_replacement_cost',
        store=True,
        readonly=False,
        help='Estimated cost to replace this device at the end of its life.'
    )
    replacement_year = fields.Integer(
        string='Replacement Year',
        compute='_compute_replacement_year',
        store=True,
        readonly=False,
        help='Year when the device is due for replacement. '
    )
    is_end_of_life = fields.Boolean(
        string='End of Life',
        compute='_compute_is_end_of_life',
        store=True,
        help='True when the replacement year has been reached or passed. '
             'Indicates the device should be considered for replacement.'
    )
    indicative_value = fields.Monetary(
        string='Indicative Value',
        currency_field='currency_id',
        compute='_compute_indicative_value',
        store=True,
        help='A simple straight-line indicative figure (cost reduced over expected life) — for replacement planning '
             'and reporting,'
    )
    condition = fields.Selection(
        selection=[
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
        ],
        string='Condition',
        tracking=True,
        help='Physical and operational condition of the device. '
             'Good: Fully functional, well maintained\n'
             'Fair: Functional with minor issues\n'
             'Poor: Significant issues, priority for replacement'
    )
    decommission_date = fields.Date(
        string='Decommission Date',
        help='Date the device was decommissioned from service.'
    )
    disposal_method = fields.Selection(
        selection=[
            ('sold', 'Sold'),
            ('donated', 'Donated'),
            ('scrapped', 'Scrapped'),
            ('returned', 'Returned to Manufacturer'),
        ],
        string='Disposal Method',
        help='Method by which the device was disposed of.'
    )
    disposal_value = fields.Monetary(
        string='Disposal Value',
        currency_field='currency_id',
        help='Value recovered from disposal (if any).'
    )
    account_asset_id = fields.Integer(
        string='Enterprise Asset ID Hook',
        copy=False,
        help='Hook/placeholder field to hold the linked account.asset ID when the optional Enterprise bridge '
             'module is present.'
    )
    schedule_ids = fields.One2many(
        'nhs.device.schedule',
        'device_id',
        string='Maintenance Schedules',
        help='Maintenance and calibration schedules for this device.'
    )
    service_ids = fields.One2many(
        'nhs.device.service',
        'device_id',
        string='Service History',
        help='Complete history of maintenance, repairs, and calibrations performed.'
    )
    alert_line_ids = fields.One2many(
        'nhs.device.alert.line',
        'device_id',
        string='Safety Alert Actions',
        help='Safety alerts affecting this device and actions taken.'
    )
    warranty_ids = fields.One2many(
        'nhs.device.warranty',
        'device_id',
        string='Warranties & Contracts',
        help='Warranty and service contract records for this device.'
    )
    next_due_date = fields.Date(
        string='Next Due Date',
        compute='_compute_next_due_date',
        store=True,
        help='Earliest upcoming maintenance/calibration due date across all schedules for this device.'
    )
    maintenance_status = fields.Selection(
        selection=[
            ('ok', 'OK'),
            ('due_soon', 'Due Soon'),
            ('overdue', 'Overdue'),
        ],
        string='Maintenance Status',
        compute='_compute_maintenance_status',
        store=True,
        help='Overall maintenance status based on all schedules:\n'
             '- OK: All schedules up to date\n'
             '- Due Soon: Schedules approaching their due date\n'
             '- Overdue: Schedules past their due date'
    )
    open_alert_count = fields.Integer(
        string='Open Alerts',
        compute='_compute_open_alert_count',
        store=True,
        help='Number of unactioned safety alerts affecting this device.'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Archiving flag. Decommissioned/disposed devices are archived '
             'to hide them from most views while retaining full history.'
    )

    @api.depends('category_id', 'model', 'serial_number')
    def _compute_name(self):
        """
        Compute the device name from category, model, and serial number.
        """
        for record in self:
            parts = []
            if record.category_id:
                parts.append(record.category_id.name)
            if record.model:
                parts.append(record.model)
            if record.serial_number:
                parts.append('SN' + record.serial_number)
            record.name = ' - '.join(parts) if parts else 'New Device'

    @api.depends('name', 'asset_tag')
    def _compute_display_name(self):
        """
        Compute the display name including asset tag.
        """
        for record in self:
            if record.asset_tag and record.asset_tag != 'New':
                record.display_name = record.asset_tag
            else:
                record.display_name = record.name or ''

    @api.depends('asset_tag')
    def _compute_barcode(self):
        """
        Compute default barcode / QR value from asset tag if unset.
        """
        for record in self:
            if not record.barcode:
                record.barcode = record.asset_tag if record.asset_tag and record.asset_tag != 'New' else False

    @api.depends('acquisition_date', 'expected_life_years')
    def _compute_expected_replacement_date(self):
        """
        Compute expected replacement date from acquisition date and expected life years.
        """
        for record in self:
            if record.acquisition_date and record.expected_life_years:
                try:
                    record.expected_replacement_date = (record.acquisition_date +
                                                        relativedelta(years=record.expected_life_years))
                except Exception:
                    record.expected_replacement_date = False
            elif not record.expected_replacement_date:
                record.expected_replacement_date = False

    @api.depends('acquisition_cost')
    def _compute_estimated_replacement_cost(self):
        """
        Compute estimated replacement cost defaulting to acquisition cost if not set.
        """
        for record in self:
            if not record.estimated_replacement_cost and record.acquisition_cost:
                record.estimated_replacement_cost = record.acquisition_cost
            elif not record.estimated_replacement_cost:
                record.estimated_replacement_cost = 0.0

    @api.depends('acquisition_date', 'expected_life_years', 'expected_replacement_date')
    def _compute_replacement_year(self):
        """
        Compute the replacement year from expected replacement date or acquisition date and expected life.
        """
        for record in self:
            if record.expected_replacement_date:
                record.replacement_year = record.expected_replacement_date.year
            elif record.acquisition_date and record.expected_life_years:
                record.replacement_year = record.acquisition_date.year + record.expected_life_years
            elif not record.replacement_year:
                record.replacement_year = False

    @api.depends('replacement_year')
    def _compute_is_end_of_life(self):
        """
        Determine if the device is at end of life based on replacement year.
        End of life is reached when replacement_year <= current year.
        """
        current_year = date.today().year
        for record in self:
            record.is_end_of_life = bool(record.replacement_year and record.replacement_year <= current_year)

    @api.depends('acquisition_cost', 'acquisition_date', 'expected_life_years')
    def _compute_indicative_value(self):
        """
        Compute the indicative current value using the configured depreciation method.
        Reads 'odoo_nhs_estate_assets.indicative_depreciation_method' setting via ir.config_parameter.
        - Straight-Line Depreciation ('straight_line'):
            indicative_value = acquisition_cost * (remaining_life / expected_life)
        - No Depreciation (Cost Only) ('none' or 'cost_only'): indicative_value = acquisition_cost
        """
        today = date.today()
        method = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_estate_assets.indicative_depreciation_method',
            default='straight_line'
        )

        for record in self:
            if not record.acquisition_cost:
                record.indicative_value = 0.0
                continue
            if method in ['none']:
                record.indicative_value = record.acquisition_cost
            else:
                if not record.acquisition_date or not record.expected_life_years:
                    record.indicative_value = 0.0
                    continue
                years_in_service = (today.year - record.acquisition_date.year) + \
                                   (today.month - record.acquisition_date.month) / 12.0
                remaining_life = max(0, record.expected_life_years - years_in_service)
                if record.expected_life_years > 0:
                    value = record.acquisition_cost * (remaining_life / record.expected_life_years)
                    record.indicative_value = max(0, value)
                else:
                    record.indicative_value = 0.0

    @api.depends('schedule_ids.next_due_date', 'schedule_ids.status')
    def _compute_next_due_date(self):
        """
        Compute the earliest next due date across all schedules.
        """
        for record in self:
            due_dates = [d for d in record.schedule_ids.mapped('next_due_date') if d]
            record.next_due_date = min(due_dates) if due_dates else False

    @api.depends('schedule_ids.status')
    def _compute_maintenance_status(self):
        """
        Compute the overall maintenance status from all schedules.
        Status is determined by the worst-case schedule status.
        """
        for record in self:
            if not record.schedule_ids:
                record.maintenance_status = 'ok'
                continue
            statuses = record.schedule_ids.mapped('status')
            if 'overdue' in statuses:
                record.maintenance_status = 'overdue'
            elif 'due_soon' in statuses:
                record.maintenance_status = 'due_soon'
            else:
                record.maintenance_status = 'ok'

    @api.depends('alert_line_ids.action_status')
    def _compute_open_alert_count(self):
        """
        Count safety alerts that are pending or quarantined for this device.
        """
        for record in self:
            record.open_alert_count = len(
                record.alert_line_ids.filtered(
                    lambda l: l.action_status in ['pending', 'quarantined']
                )
            )

    def action_log_service(self):
        """
        Open the service logging wizard for the selected device(s).
        """
        return {
            'name': 'Log Service',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.service.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_device_id': [(6, 0, self.id)],
            }
        }

    def action_view_schedules(self):
        """
        Open the schedules view for the selected device.
        """
        return {
            'name': 'Schedules',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.schedule',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
        }

    def action_view_services(self):
        """
        Open the service history for the selected device.
        """
        return {
            'name': 'Service History',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.service',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
        }

    def action_view_alerts(self):
        """
        Open the safety alerts affecting the selected device.
        """
        return {
            'name': 'Safety Alerts',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.alert',
            'view_mode': 'list,form',
            'domain': [('line_ids.device_id', '=', self.id)],
        }

    def action_view_warranties(self):
        """
        Open the warranties/contracts for the selected device.
        """
        return {
            'name': 'Warranties & Contracts',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.warranty',
            'view_mode': 'list,form',
            'domain': [('device_id', 'in', self.ids)],
        }

    def action_decommission(self):
        """
        Decommission the selected device(s).
        """
        today = date.today()
        return {
            'name': 'Decommission Device',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.decommission.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_device_id': self.id ,
                'default_decommission_date': today,
            }
        }

    def action_export_all_register_excel(self):
        """
        Wrapper method to export all active devices in the register.
        Called from Reporting -> Device Register (Excel) menu action.
        """
        all_devices = self.env['nhs.device'].search([('active', '=', True)])
        return all_devices.action_export_register_excel()

    def action_export_register_excel(self):
        """
        Export the selected or active device register as a formatted Excel (.xlsx) file.
        Uses an Odoo/NHS styled layout complete with company logo, formatted headers,
        dynamic column widths, gridlines, date/monetary formatting, and total summary row.
        """
        import io
        import base64
        import xlsxwriter
        devices = self if self else self.search([('active', '=', True)])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Device Register')
        worksheet.hide_gridlines(2)
        FONT_NAME = 'Calibri'
        COLOR_PRIMARY = '#005EB8'
        COLOR_BORDER = '#D3D3D3'
        COLOR_SUMMARY = '#E6F0FA'
        fmt_title = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_name': FONT_NAME,
            'font_color': COLOR_PRIMARY,
            'valign': 'vcenter',
        })
        fmt_subtitle = workbook.add_format({
            'italic': True,
            'font_size': 10,
            'font_name': FONT_NAME,
            'font_color': '#555555',
            'valign': 'vcenter',
        })
        fmt_header = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'font_name': FONT_NAME,
            'font_color': '#FFFFFF',
            'bg_color': COLOR_PRIMARY,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#003366',
            'text_wrap': True,
        })

        def get_data_formats(bg_color=None):
            base = {
                'font_name': FONT_NAME,
                'font_size': 10,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': COLOR_BORDER,
            }
            if bg_color:
                base['bg_color'] = bg_color

            return {
                'left': workbook.add_format(dict(base, align='center')),
                'center': workbook.add_format(dict(base, align='center')),
                'right': workbook.add_format(dict(base, align='center')),
                'date': workbook.add_format(dict(base, align='center', num_format='yyyy-mm-dd')),
                'currency': workbook.add_format(dict(base, align='center', num_format='£#,##0.00')),
                'number': workbook.add_format(dict(base, align='center', num_format='#,##0')),
            }

        fmt_odd = get_data_formats(None)
        fmt_even = get_data_formats('#F8FAFC')
        fmt_sum_label = workbook.add_format({
            'bold': True,
            'font_name': FONT_NAME,
            'font_size': 11,
            'bg_color': COLOR_SUMMARY,
            'top': 1,
            'top_color': COLOR_PRIMARY,
            'align': 'center',
            'valign': 'vcenter',
        })
        fmt_sum_fill = workbook.add_format({
            'bg_color': COLOR_SUMMARY,
            'top': 1,
            'top_color': COLOR_PRIMARY,
            'align': 'center',
            'valign': 'vcenter',
        })
        fmt_sum_curr = workbook.add_format({
            'bold': True,
            'font_name': FONT_NAME,
            'font_size': 11,
            'bg_color': COLOR_SUMMARY,
            'top': 1,
            'top_color': COLOR_PRIMARY,
            'align': 'center',
            'valign': 'vcenter',
            'num_format': '£#,##0.00',
        })
        company = self.env.company
        if company.logo:
            try:
                logo_data = base64.b64decode(company.logo)
                logo_stream = io.BytesIO(logo_data)
                scale = 0.5
                try:
                    from PIL import Image
                    img = Image.open(io.BytesIO(logo_data))
                    width, height = img.size
                    if height > 0:
                        scale = 45.0 / height
                except Exception:
                    pass
                worksheet.insert_image(0, 0, 'company_logo.png', {
                    'image_data': logo_stream,
                    'x_scale': scale,
                    'y_scale': scale,
                    'x_offset': 5,
                    'y_offset': 5,
                })
            except Exception:
                pass

        worksheet.set_row(0, 24)
        worksheet.write(0, 2, 'NHS MEDICAL DEVICE REGISTER', fmt_title)
        worksheet.set_row(1, 18)
        subtitle_str = f"Company: {company.name}  |  Export Date: {fields.Date.today()}  |  Total Records: {len(devices)}"
        worksheet.write(1, 2 , subtitle_str, fmt_subtitle)
        worksheet.set_row(2, 10)
        headers = [
            'Asset Tag', 'Barcode', 'Device Name', 'Category', 'Medical Device',
            'Manufacturer', 'Model', 'Serial Number', 'Site', 'Building', 'Space',
            'Department', 'Status', 'Condition', 'Acquisition Date', 'In-Service Date',
            'Expected Life (Yrs)', 'Replacement Year', 'End of Life', 'Acquisition Cost',
            'Indicative Value', 'Funding Source'
        ]
        header_row = 3
        worksheet.set_row(header_row, 28)
        for col_idx, header in enumerate(headers):
            worksheet.write(header_row, col_idx, header, fmt_header)
        col_widths = [len(h) for h in headers]
        start_row = 4
        total_acq_cost = 0.0
        total_ind_value = 0.0
        for idx, d in enumerate(devices):
            current_row = start_row + idx
            worksheet.set_row(current_row, 20)
            fmts = fmt_even if idx % 2 == 1 else fmt_odd
            status_label = dict(d._fields['status'].selection).get(d.status, d.status) if d.status else ''
            cond_label = dict(d._fields['condition'].selection).get(d.condition, d.condition) if d.condition else ''
            funding_label = dict(d._fields['funding_source'].selection).get(d.funding_source, d.funding_source) \
                if d.funding_source else ''
            acq_cost = d.acquisition_cost or 0.0
            ind_val = d.indicative_value or 0.0
            total_acq_cost += acq_cost
            total_ind_value += ind_val
            row_data = [
                (d.asset_tag or '', fmts['center'], 'text'),
                (d.barcode or '', fmts['center'], 'text'),
                (d.name or '', fmts['left'], 'text'),
                (d.category_id.name if d.category_id else '', fmts['left'], 'text'),
                ('Yes' if d.is_medical_device else 'No', fmts['center'], 'text'),
                (d.manufacturer or '', fmts['left'], 'text'),
                (d.model or '', fmts['left'], 'text'),
                (d.serial_number or '', fmts['left'], 'text'),
                (d.site_id.name if d.site_id else '', fmts['left'], 'text'),
                (d.building_id.name if d.building_id else '', fmts['left'], 'text'),
                (d.space_id.name if d.space_id else '', fmts['left'], 'text'),
                (d.department or '', fmts['left'], 'text'),
                (status_label, fmts['center'], 'text'),
                (cond_label, fmts['center'], 'text'),
                (d.acquisition_date.strftime('%Y-%m-%d') if d.acquisition_date else '', fmts['date'], 'date'),
                (d.in_service_date.strftime('%Y-%m-%d') if d.in_service_date else '', fmts['date'], 'date'),
                (d.expected_life_years or '', fmts['number'], 'number'),
                (d.replacement_year or '', fmts['number'], 'number'),
                ('Yes' if d.is_end_of_life else 'No', fmts['center'], 'text'),
                (acq_cost, fmts['currency'], 'currency'),
                (ind_val, fmts['currency'], 'currency'),
                (funding_label, fmts['left'], 'text'),
            ]
            for c_idx, (val, cell_fmt, val_type) in enumerate(row_data):
                if val_type == 'currency':
                    worksheet.write_number(current_row, c_idx, val, cell_fmt)
                    val_str = f"£{val:,.2f}"
                elif val_type == 'number' and isinstance(val, (int, float)):
                    worksheet.write_number(current_row, c_idx, val, cell_fmt)
                    val_str = str(val)
                else:
                    worksheet.write(current_row, c_idx, val, cell_fmt)
                    val_str = str(val)

                col_widths[c_idx] = max(col_widths[c_idx], len(val_str))
        summary_row = start_row + len(devices)
        worksheet.set_row(summary_row, 24)
        first_excel_row = start_row + 1
        last_excel_row = summary_row
        for c_idx in range(len(headers)):
            if c_idx == 0:
                worksheet.write(summary_row, c_idx, f"Total Devices: {len(devices)}", fmt_sum_label)
            elif c_idx == 19:
                if len(devices) > 0:
                    worksheet.write_formula(summary_row, c_idx, f"=SUM(T{first_excel_row}:T{last_excel_row})",
                                            fmt_sum_curr, total_acq_cost)
                else:
                    worksheet.write_number(summary_row, c_idx, 0.0, fmt_sum_curr)
            elif c_idx == 20:
                if len(devices) > 0:
                    worksheet.write_formula(summary_row, c_idx, f"=SUM(U{first_excel_row}:U{last_excel_row})",
                                            fmt_sum_curr, total_ind_value)
                else:
                    worksheet.write_number(summary_row, c_idx, 0.0, fmt_sum_curr)
            else:
                worksheet.write(summary_row, c_idx, '', fmt_sum_fill)
        for c_idx, width in enumerate(col_widths):
            min_w = 14 if c_idx in (14, 15, 19, 20) else 11
            worksheet.set_column(c_idx, c_idx, max(width + 3, min_w))
        workbook.close()
        output.seek(0)
        excel_data = output.getvalue()
        attachment = self.env['ir.attachment'].create({
            'name': 'NHS_Device_Register_Export.xlsx',
            'datas': base64.b64encode(excel_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    @api.onchange('site_id', 'building_id')
    def _onchange_location(self):
        """
        Location hierarchy filtering.
        """
        if not self.site_id:
            self.building_id = False
            self.space_id = False
        elif not self.building_id:
            self.space_id = False
        return {
            'domain': {
                'building_id': [('site_id', '=', self.site_id.id)] if self.site_id else [],
                'space_id': [('building_id', '=', self.building_id.id)] if self.building_id
                else [('site_id', '=', self.site_id.id)] if self.site_id
                else [],
            }
        }

    @api.onchange('acquisition_date')
    def _onchange_acquisition_date(self):
        """
        Set in_service_date to acquisition_date if not already set.
        """
        if self.acquisition_date and not self.in_service_date:
            self.in_service_date = self.acquisition_date

    def _sync_maintenance_equipment(self):
        """
        Automatically create linked maintenance.equipment record if create_maintenance_equipment
        is enabled (and is_medical_device is True).
        """
        Equipment = self.env['maintenance.equipment']
        Category = self.env['maintenance.equipment.category']
        Team = self.env['maintenance.team']
        for record in self:
            if record.create_maintenance_equipment and record.is_medical_device:
                existing = Equipment.search([('nhs_device_id', '=', record.id)], limit=1)
                if not existing:
                    category = Category.search([('name', '=', 'Medical Device')], limit=1)
                    if not category:
                        category = Category.create({'name': 'Medical Device'})
                    team = Team.search([('name', '=', 'NHS Technician Team')], limit=1)
                    if not team:
                        team = Team.create({'name': 'NHS Technician Team'})
                    Equipment.create({
                        'name': record.display_name or record.name or 'NHS Device',
                        'category_id': category.id,
                        'maintenance_team_id': team.id,
                        'nhs_device_id': record.id,
                        'owner_user_id': record.responsible_user_id.id if record.responsible_user_id else False,
                        'serial_no': record.serial_number or False,
                        'model': record.model or False,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create device records with:
        1. Auto-sequenced asset tags
        2. Default schedules copied from category (without initial dates)
        3. Automatic active/archived status for decommissioned assets
        4. Automatic maintenance equipment creation if explicitly enabled
        """
        for vals in vals_list:
            if 'asset_tag' not in vals or vals.get('asset_tag') == 'New':
                vals['asset_tag'] = self.env['ir.sequence'].next_by_code('nhs.device') or 'New'
        devices = super(NHSDevice, self).create(vals_list)
        for device in devices:
            if device.category_id:
                device.category_id._copy_default_schedules_to_device(device)
        devices._sync_maintenance_equipment()
        return devices

    def write(self, vals):
        """
        Handle device updates:
        1. Category changes: add missing schedules from new category
        2. Status changes: auto-toggle active archiving state
        3. Cascading active/archived state to device-specific related records
        4. Maintenance equipment sync if integration toggled
        """
        if 'active' in vals:
            target_active = vals['active']
            for device in self:
                if device.active != target_active:
                    if not target_active:
                        active_schedules = device.schedule_ids.filtered('active')
                        if active_schedules:
                            active_schedules.write({
                                'active': False,
                                'archived_by_device_id': device.id,
                            })
                        active_services = device.service_ids.filtered('active')
                        if active_services:
                            active_services.write({
                                'active': False,
                                'archived_by_device_id': device.id,
                            })
                        active_warranties = device.warranty_ids.filtered('active')
                        if active_warranties:
                            active_warranties.write({
                                'active': False,
                                'archived_by_device_id': device.id,
                            })
                        active_alert_lines = device.alert_line_ids.filtered('active')
                        if active_alert_lines:
                            active_alert_lines.write({
                                'active': False,
                                'archived_by_device_id': device.id,
                            })
                    else:
                        self.env['nhs.device.schedule'].with_context(active_test=False).search([
                            ('device_id', '=', device.id),
                            ('archived_by_device_id', '=', device.id),
                        ]).write({
                            'active': True,
                            'archived_by_device_id': False,
                        })
                        self.env['nhs.device.service'].with_context(active_test=False).search([
                            ('device_id', '=', device.id),
                            ('archived_by_device_id', '=', device.id),
                        ]).write({
                            'active': True,
                            'archived_by_device_id': False,
                        })
                        self.env['nhs.device.warranty'].with_context(active_test=False).search([
                            ('device_id', '=', device.id),
                            ('archived_by_device_id', '=', device.id),
                        ]).write({
                            'active': True,
                            'archived_by_device_id': False,
                        })
                        self.env['nhs.device.alert.line'].with_context(active_test=False).search([
                            ('device_id', '=', device.id),
                            ('archived_by_device_id', '=', device.id),
                        ]).write({
                            'active': True,
                            'archived_by_device_id': False,
                        })
        if 'status' in vals and 'active' not in vals:
            if vals['status'] in ['decommissioned', 'disposed']:
                vals['active'] = False
            elif vals['status'] in ['in_service', 'awaiting_repair', 'out_of_service']:
                vals['active'] = True
        if 'category_id' in vals:
            for record in self:
                if record.category_id and record.category_id.id != vals.get('category_id'):
                    new_category = self.env['nhs.device.category'].browse(vals['category_id'])
                    if new_category and new_category.exists():
                        new_category._add_missing_schedules_to_device(record)
        res = super(NHSDevice, self).write(vals)
        if 'create_maintenance_equipment' in vals or 'is_medical_device' in vals:
            self._sync_maintenance_equipment()
        return res

    _asset_tag_unique_company = models.Constraint(
        'UNIQUE(asset_tag, company_id)',
        'Asset tag must be unique per company.',
    )

    _positive_acquisition_cost = models.Constraint(
        'CHECK(acquisition_cost >= 0)',
        'Acquisition cost must be a positive number.',
    )

    _positive_expected_life = models.Constraint(
        'CHECK(expected_life_years > 0)',
        'Expected life must be greater than 0 years.',
    )

    @api.constrains('acquisition_date', 'in_service_date')
    def _check_dates(self):
        """
        Validate that dates are in a logical order.
        """
        for record in self:
            if record.acquisition_date and record.in_service_date:
                if record.in_service_date < record.acquisition_date:
                    raise ValidationError('In service date cannot be before acquisition date.')

    @api.constrains('status', 'decommission_date')
    def _check_decommission_status(self):
        """
        Validate that decommissioned/disposed devices have a decommission date.
        """
        for record in self:
            if record.status in ['decommissioned', 'disposed'] and not record.decommission_date:
                raise ValidationError(
                    'Please set a decommission date before marking the device as decommissioned or disposed.'
                )

    def action_view_maintenance(self):
        """Open a list/form view of maintenance requests linked to this device."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance',
            'res_model': 'maintenance.request',
            'view_mode': 'list,form',
            'domain': [('nhs_device_id', '=', self.id)],
            'context': {'default_nhs_device_id': self.id},
        }

    @api.model
    def get_dashboard_metrics(self):
        """
        Compute aggregated metrics and statistics for the NHS Device Dashboard.
        Covers:
        1. Device Register: Total devices, breakdown by category, location, and status.
        2. Maintenance/Calibration Planner: Upcoming schedules by month & type (PPM vs Calibration).
        3. Overdue Register: Counts and detailed top overdue schedules.
        4. Safety Alert Exposure: Open alerts, affected devices, and source breakdown.
        5. End-of-Life Forecast: Replacement breakdown by year with indicative cost.
        6. Indicative Register Value: Total value, total acquisition cost, and breakdown by category.
        """
        today = date.today()
        current_year = today.year
        devices = self.search([('active', '=', True)])
        total_devices = len(devices)
        status_counts = {
            'in_service': 0,
            'awaiting_repair': 0,
            'out_of_service': 0,
            'decommissioned': 0,
            'disposed': 0,
        }
        for d in devices:
            if d.status in status_counts:
                status_counts[d.status] += 1
        category_data = {}
        for d in devices:
            cat_name = d.category_id.name if d.category_id else 'Uncategorized'
            cat_id = d.category_id.id if d.category_id else False
            if cat_name not in category_data:
                category_data[cat_name] = {
                    'id': cat_id,
                    'name': cat_name,
                    'count': 0,
                    'indicative_value': 0.0,
                    'acquisition_cost': 0.0,
                }
            category_data[cat_name]['count'] += 1
            category_data[cat_name]['indicative_value'] += d.indicative_value or 0.0
            category_data[cat_name]['acquisition_cost'] += d.acquisition_cost or 0.0
        devices_by_category = sorted(list(category_data.values()), key=lambda x: x['count'], reverse=True)
        location_counts = {}
        for d in devices:
            loc_name = d.site_id.name if d.site_id else 'Unassigned Site'
            location_counts[loc_name] = location_counts.get(loc_name, 0) + 1
        devices_by_location = sorted(
            [{'name': k, 'count': v} for k, v in location_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]
        schedules = self.env['nhs.device.schedule'].search([('active', '=', True)])
        overdue_schedules = schedules.filtered(lambda s: s.status == 'overdue')
        due_soon_schedules = schedules.filtered(lambda s: s.status == 'due_soon')
        overdue_escalation_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_estate_assets.overdue_escalation_days',
            default=7
        ))
        escalated_overdue_schedules = overdue_schedules.filtered(
            lambda s: s.next_due_date and (today - s.next_due_date).days >= overdue_escalation_days
        )
        overdue_ppm_count = len(overdue_schedules.filtered(lambda s: s.schedule_type_id.code == 'ppm'))
        overdue_calib_count = len(overdue_schedules.filtered(lambda s: s.schedule_type_id.code in
                                                                       ['calibration', 'electrical_safety']))
        due_soon_ppm_count = len(due_soon_schedules.filtered(lambda s:
                                                             s.schedule_type_id.code == 'ppm'))
        due_soon_calib_count = len(due_soon_schedules.filtered(lambda s: s.schedule_type_id.code in
                                                                         ['calibration', 'electrical_safety']))
        planner_timeline = []
        for i in range(6):
            month_date = today + relativedelta(months=i)
            start_m = month_date.replace(day=1)
            next_m = start_m + relativedelta(months=1)
            end_m = next_m - relativedelta(days=1)
            month_label = start_m.strftime('%b %Y')
            month_scheds = schedules.filtered(lambda s: s.next_due_date and
                                                        start_m <= s.next_due_date <= end_m)
            ppm_cnt = len(month_scheds.filtered(lambda s: s.schedule_type_id.code == 'ppm'))
            calib_cnt = len(month_scheds.filtered(lambda s: s.schedule_type_id.code in
                                                            ['calibration', 'electrical_safety']))
            other_cnt = len(month_scheds.filtered(lambda s: s.schedule_type_id.code not in
                                                            ['ppm', 'calibration', 'electrical_safety']))
            planner_timeline.append({
                'month': month_label,
                'ppm': ppm_cnt,
                'calibration': calib_cnt,
                'other': other_cnt,
                'total': len(month_scheds),
            })
        overdue_records = []
        delivery_dict = dict(self.env['nhs.device.schedule']._fields['delivery'].selection)
        for s in overdue_schedules[:15]:
            days_overdue = (today - s.next_due_date).days if s.next_due_date else 0
            type_label = s.schedule_type_id.name if s.schedule_type_id else ''
            type_code = s.schedule_type_id.code if s.schedule_type_id else ''
            delivery_label = delivery_dict.get(s.delivery, s.delivery)
            overdue_records.append({
                'id': s.id,
                'device_id': s.device_id.id,
                'device_name': s.device_id.display_name or s.device_id.name,
                'asset_tag': s.device_id.asset_tag,
                'schedule_type': type_label,
                'schedule_type_code': type_code,
                'next_due_date': s.next_due_date.strftime('%Y-%m-%d') if s.next_due_date else '',
                'days_overdue': days_overdue,
                'is_escalated': days_overdue >= overdue_escalation_days,
                'delivery': delivery_label,
                'site': s.device_id.site_id.name if s.device_id.site_id else 'N/A',
            })
        overdue_records.sort(key=lambda x: x['days_overdue'], reverse=True)
        open_alerts = self.env['nhs.device.alert'].search([('state', 'in', ['open', 'in_progress']),
                                                           ('active', '=', True)])
        open_alert_lines = self.env['nhs.device.alert.line'].search([
            ('alert_id.state', 'in', ['open', 'in_progress']),
            ('action_status', 'in', ['pending', 'quarantined'])
        ])
        source_exposure = {'mhra': 0, 'cas': 0, 'manufacturer_fsn': 0, 'other': 0}
        source_dict = dict(self.env['nhs.device.alert']._fields['source'].selection)
        for a in open_alerts:
            src = a.source or 'other'
            if src in source_exposure:
                source_exposure[src] += 1
            else:
                source_exposure['other'] += 1
        top_alerts_data = []
        for a in open_alerts[:6]:
            pending_lines = a.line_ids.filtered(lambda l: l.action_status in ['pending', 'quarantined'])
            top_alerts_data.append({
                'id': a.id,
                'reference': a.reference,
                'title': a.name,
                'source': source_dict.get(a.source, a.source),
                'affected_count': len(a.line_ids),
                'pending_count': len(pending_lines),
                'deadline': a.action_deadline.strftime('%Y-%m-%d') if a.action_deadline else 'No deadline',
                'is_overdue': a.is_overdue,
            })
        replacement_years = {}
        for y in range(current_year, current_year + 6):
            replacement_years[y] = {
                'year': str(y),
                'count': 0,
                'indicative_cost': 0.0,
                'acquisition_cost': 0.0,
            }
        eol_devices = devices.filtered(lambda d: d.is_end_of_life or (d.replacement_year
                                                                      and d.replacement_year <= current_year))
        eol_count = len(eol_devices)
        for d in devices:
            ry = d.replacement_year
            if ry:
                target_year = current_year if ry <= current_year else ry
                if target_year in replacement_years:
                    replacement_years[target_year]['count'] += 1
                    replacement_years[target_year]['indicative_cost'] += (d.estimated_replacement_cost or
                                                                          d.acquisition_cost or 0.0)
                    replacement_years[target_year]['acquisition_cost'] += d.acquisition_cost or 0.0
        replacement_by_year = list(replacement_years.values())
        total_forecast_cost = sum(item['indicative_cost'] for item in replacement_by_year)
        total_indicative_value = sum(d.indicative_value or 0.0 for d in devices)
        total_acquisition_cost = sum(d.acquisition_cost or 0.0 for d in devices)
        return {
            'total_devices': total_devices,
            'devices_by_status': status_counts,
            'devices_by_category': devices_by_category,
            'devices_by_location': devices_by_location,
            'maintenance_planner': {
                'total_schedules': len(schedules),
                'due_soon_count': len(due_soon_schedules),
                'due_soon_ppm': due_soon_ppm_count,
                'due_soon_calib': due_soon_calib_count,
                'timeline': planner_timeline,
            },
            'overdue_register': {
                'total_overdue': len(overdue_schedules),
                'escalated_overdue_count': len(escalated_overdue_schedules),
                'overdue_escalation_days': overdue_escalation_days,
                'overdue_ppm_count': overdue_ppm_count,
                'overdue_calib_count': overdue_calib_count,
                'records': overdue_records,
            },
            'safety_alerts': {
                'open_alerts_count': len(open_alerts),
                'affected_devices_count': len(open_alert_lines),
                'overdue_alerts_count': len(open_alerts.filtered(lambda a: a.is_overdue)),
                'source_exposure': source_exposure,
                'top_alerts': top_alerts_data,
            },
            'replacement_forecast': {
                'end_of_life_count': eol_count,
                'by_year': replacement_by_year,
                'total_forecast_cost': total_forecast_cost,
            },
            'register_value': {
                'total_indicative_value': total_indicative_value,
                'total_acquisition_cost': total_acquisition_cost,
                'by_category': devices_by_category,
            }
        }

    def _get_responsible_or_manager_user(self):
        """
        Get the assigned user for device notification activities.
        1. Returns responsible_user_id if set on the device.
        2. If responsible_user_id is not set, returns an active user from the Equipment Manager group
        (group_nhs_equipment_manager).
        3. Fallback to current user / admin.
        """
        self.ensure_one()
        if self.responsible_user_id and self.responsible_user_id.active:
            return self.responsible_user_id
        manager_group = self.env.ref('odoo_nhs_estate_assets.group_nhs_equipment_manager',
                                     raise_if_not_found=False)
        if manager_group:
            field_name = 'group_ids' if 'group_ids' in self.env['res.users']._fields else 'groups_id'
            manager_users = self.env['res.users'].search([
                (field_name, 'in', [manager_group.id]),
                ('active', '=', True)
            ], limit=1)
            if manager_users:
                return manager_users[0]
        return self.env.user

    @api.model
    def _cron_check_overdue(self):
        """
        Cron job to check overdue maintenance, due-soon maintenance, and end-of-life devices.
        Creates Odoo activities for responsible users so items appear in their To-Do list.
        If a responsible user is not assigned to the device, activities are assigned to the Equipment Manager.
        """
        today = date.today()
        todo_activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not todo_activity_type:
            return
        device_model_id = self.env['ir.model']._get_id('nhs.device')
        overdue_escalation_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_estate_assets.overdue_escalation_days',
            default=7
        ))
        overdue_schedules = self.env['nhs.device.schedule'].search([
            ('status', 'in', ['overdue', 'due_soon'])
        ])
        for sched in overdue_schedules:
            device = sched.device_id
            assignee = device._get_responsible_or_manager_user()
            days_overdue = (today - sched.next_due_date).days if (
                        sched.next_due_date and sched.status == 'overdue') else 0
            is_escalated = days_overdue >= overdue_escalation_days
            schedule_type_display = sched.schedule_type_id.display_name or sched.schedule_type_id.name or 'Unknown'
            status_display = dict(sched._fields.get('status', {}).selection or []).get(sched.status,
                                                    sched.status) if hasattr(sched,'status') else sched.status
            if is_escalated:
                summary = "[ESCALATED OVERDUE] %s Due - %s" % (schedule_type_display, device.display_name)
                note = ("Device asset tag %s has a %s schedule overdue by %s days (exceeds escalation "
                        "threshold of %s days).") % (
                    device.asset_tag, schedule_type_display, days_overdue, overdue_escalation_days
                )
            else:
                summary = "[%s] %s Due - %s" % (status_display, schedule_type_display, device.display_name)
                note = "Device asset tag %s has a %s schedule (%s) due on %s." % (
                    device.asset_tag, schedule_type_display, status_display, sched.next_due_date
                )
            existing_activity = self.env['mail.activity'].search([
                ('res_id', '=', device.id),
                ('res_model_id', '=', device_model_id),
                ('summary', '=', summary),
            ], limit=1)
            if not existing_activity:
                self.env['mail.activity'].create({
                    'activity_type_id': todo_activity_type.id,
                    'summary': summary,
                    'note': note,
                    'res_id': device.id,
                    'res_model_id': device_model_id,
                    'user_id': assignee.id,
                    'date_deadline': sched.next_due_date or today,
                })
        eol_devices = self.search([('is_end_of_life', '=', True)])
        for device in eol_devices:
            assignee = device._get_responsible_or_manager_user()
            summary = "[End of Life] Replacement Due - %s" % device.display_name
            note = ("Device asset tag %s reached replacement year (%s). Please review for replacement/decommissioning."
                    % (device.asset_tag, device.replacement_year
            ))
            existing_activity = self.env['mail.activity'].search([
                ('res_id', '=', device.id),
                ('res_model_id', '=', device_model_id),
                ('summary', '=', summary),
            ], limit=1)
            if not existing_activity:
                self.env['mail.activity'].create({
                    'activity_type_id': todo_activity_type.id,
                    'summary': summary,
                    'note': note,
                    'res_id': device.id,
                    'res_model_id': device_model_id,
                    'user_id': assignee.id,
                    'date_deadline': today,
                })

    @api.model
    def _cron_send_weekly_digest(self):
        """
        Weekly scheduled cron: Sends a summary email listing:
        1. Due maintenance (schedules due soon)
        2. Overdue maintenance
        3. Expiring warranties / contracts
        4. Overdue safety alerts
        5. End-of-life devices
        to Equipment Managers.
        """
        today = date.today()
        today_str = today.strftime('%d/%m/%Y')
        schedules = self.env['nhs.device.schedule'].search([('active', '=', True)])
        due_schedules = schedules.filtered(lambda s: s.status == 'due_soon')
        overdue_schedules = schedules.filtered(lambda s: s.status == 'overdue')
        expiring_warranties = self.env['nhs.device.warranty'].search([
            ('is_expiring', '=', True),
            ('active', '=', True)
        ])
        overdue_alerts = self.env['nhs.device.alert'].search([
            ('state', 'in', ['open', 'in_progress']),
            ('is_overdue', '=', True),
            ('active', '=', True)
        ])
        eol_devices = self.search([('is_end_of_life', '=', True), ('active', '=', True)])
        manager_group = self.env.ref('odoo_nhs_estate_assets.group_nhs_equipment_manager',
                                     raise_if_not_found=False)
        field_name = 'group_ids' if 'group_ids' in self.env['res.users']._fields else 'groups_id'
        manager_users = self.env['res.users'].search([
            (field_name, 'in', [manager_group.id]),
            ('active', '=', True),
            ('email', '!=', False)
        ]) if manager_group else self.env['res.users']
        recipient_emails = list(set([u.email for u in manager_users if u.email]))
        if not recipient_emails:
            company_email = self.env.company.email or self.env.user.email
            if company_email:
                recipient_emails = [company_email]
        subject = "Weekly NHS Asset & Equipment Management Summary Report - %s" % today_str
        due_rows = "".join([
        "<tr><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "%s</td><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "%s</td></tr>" % (
                s.device_id.display_name or 'N/A',
                s.schedule_type_id.display_name or s.schedule_type_id.name or 'N/A',
                s.next_due_date or 'N/A',
                s.device_id._get_responsible_or_manager_user().name or 'Unassigned'
            ) for s in due_schedules[:15]
        ]) or ("<tr><td colspan='4' style='padding:8px;border:1px solid #ddd;text-align:center;color:#777;'>"
               "No maintenance schedules currently due soon.</td></tr>")
        overdue_rows = "".join([
        "<tr><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "%s</td><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "%s</td></tr>" % (
                s.device_id.display_name or 'N/A',
                s.schedule_type_id.display_name or s.schedule_type_id.name or 'N/A',
                s.next_due_date or 'N/A',
                s.device_id._get_responsible_or_manager_user().name or 'Unassigned'
            ) for s in overdue_schedules[:15]
        ]) or ("<tr><td colspan='4' style='padding:8px;border:1px solid #ddd;text-align:center;color:#777;'>"
               "No maintenance schedules currently overdue.</td></tr>")
        warranty_rows = "".join([
        "<tr><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "%s</td><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "%s</td></tr>" % (
                w.device_id.display_name or 'N/A',
                w.get_cover_type_display(),
                w.provider or 'N/A',
                w.expiry_date or 'N/A'
            ) for w in expiring_warranties[:15]
        ]) or ("<tr><td colspan='4' style='padding:8px;border:1px solid #ddd;text-align:center;color:#777;'>"
               "No warranties or service contracts expiring soon.</td></tr>")
        alert_rows = "".join([
        "<tr><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "%s</td><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "%s</td></tr>" % (
                a.reference or 'N/A',
                a.name or 'N/A',
                a.action_deadline or 'N/A',
                "%s / %s" % (a.actioned_count, a.affected_count)
            ) for a in overdue_alerts[:15]
        ]) or ("<tr><td colspan='4' style='padding:8px;border:1px solid #ddd;text-align:center;color:#777;'>"
               "No safety alerts currently overdue.</td></tr>")
        eol_rows = "".join([
        "<tr><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "%s</td><td style='padding:8px;border:1px solid #ddd;'>%s</td><td style='padding:8px;border:1px solid #ddd;'>"
        "£%.2f</td></tr>" % (
                d.display_name or 'N/A',
                d.category_id.display_name or d.category_id.name or 'N/A',
                d.replacement_year or 'N/A',
                d.estimated_replacement_cost or 0.0
            ) for d in eol_devices[:15]
        ]) or ("<tr><td colspan='4' style='padding:8px;border:1px solid #ddd;text-align:center;color:#777;'>"
               "No devices currently due for end-of-life replacement.</td></tr>")
        body_html = f"""
        <div style="font-family: Arial, sans-serif; color: #2c3e50; line-height: 1.6; max-width: 850px; margin: 0 auto;
         background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
            <div style="background-color: #005EB8; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                <h2 style="color: #ffffff; margin: 0; font-size: 22px;">NHS Estate &amp; Asset Management</h2>
                <p style="color: #e0f0ff; margin: 4px 0 0 0; font-size: 14px;">
                Weekly Manager Summary Report — {today_str}</p>
            </div>
            <div style="padding: 20px; background-color: #ffffff; border-radius: 0 0 8px 8px; border: 1px solid #e9ecef;">
                <p>Dear Equipment Manager,</p>
                <p>Here is your weekly summary report listing equipment maintenance, expiring contracts/warranties, 
                overdue safety alerts, and replacement forecast status:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr>
                        <td style="padding: 10px; background-color: #fff3cd; border: 1px solid #ffeeba; 
                        text-align: center; width: 20%;">
                            <div style="font-size: 20px; font-weight: bold; color: #856404;">{len(due_schedules)}</div>
                            <div style="font-size: 11px; color: #856404; font-weight: 600;">DUE MAINTENANCE</div>
                        </td>
                        <td style="padding: 10px; background-color: #f8d7da; border: 1px solid #f5c6cb; 
                        text-align: center; width: 20%;">
                            <div style="font-size: 20px; font-weight: bold; color: #721c24;">{len(overdue_schedules)}</div>
                            <div style="font-size: 11px; color: #721c24; font-weight: 600;">OVERDUE MAINT.</div>
                        </td>
                        <td style="padding: 10px; background-color: #d1ecf1; border: 1px solid #bee5eb; 
                        text-align: center; width: 20%;">
                            <div style="font-size: 20px; font-weight: bold; color: #0c5460;">{len(expiring_warranties)}</div>
                            <div style="font-size: 11px; color: #0c5460; font-weight: 600;">EXPIRING COVER</div>
                        </td>
                        <td style="padding: 10px; background-color: #f8d7da; border: 1px solid #f5c6cb; 
                        text-align: center; width: 20%;">
                            <div style="font-size: 20px; font-weight: bold; color: #721c24;">{len(overdue_alerts)}</div>
                            <div style="font-size: 11px; color: #721c24; font-weight: 600;">OVERDUE ALERTS</div>
                        </td>
                        <td style="padding: 10px; background-color: #e2e3e5; border: 1px solid #d6d8db; 
                        text-align: center; width: 20%;">
                            <div style="font-size: 20px; font-weight: bold; color: #383d41;">{len(eol_devices)}</div>
                            <div style="font-size: 11px; color: #383d41; font-weight: 600;">END OF LIFE</div>
                        </td>
                    </tr>
                </table>
                <h3 style="color: #005EB8; margin-top: 20px;">1. Due Maintenance ({len(due_schedules)})</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Device</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Schedule Type</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Next Due Date</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Assignee</th>
                    </tr>
                    {due_rows}
                </table>
                <h3 style="color: #d9534f; margin-top: 20px;">2. Overdue Maintenance ({len(overdue_schedules)})</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Device</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Schedule Type</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Due Date</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Assignee</th>
                    </tr>
                    {overdue_rows}
                </table>
                <h3 style="color: #17a2b8; margin-top: 20px;">
                3. Expiring Warranties &amp; Contracts ({len(expiring_warranties)})</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Device</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Cover Type</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Provider</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Expiry Date</th>
                    </tr>
                    {warranty_rows}
                </table>
                <h3 style="color: #d9534f; margin-top: 20px;">4. Overdue Safety Alerts ({len(overdue_alerts)})</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Reference</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Alert Name</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Deadline</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Action Progress</th>
                    </tr>
                    {alert_rows}
                </table>
                <h3 style="color: #6c757d; margin-top: 20px;">5. End of Life / Replacement Due ({len(eol_devices)})</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Device</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Category</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Replacement Year</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Est. Replacement Cost</th>
                    </tr>
                    {eol_rows}
                </table>
                <p style="margin-top: 25px; font-size: 12px; color: #7f8c8d;">This summary report is automatically sent
                 weekly by the NHS Estate Assets Management system.</p>
            </div>
        </div>
        """
        if recipient_emails:
            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_to': ','.join(recipient_emails),
                'email_from': self.env.company.email or self.env.user.email,
            }
            self.env['mail.mail'].create(mail_values).send()
        self.env.company.message_post(body=body_html, subtype_xmlid='mail.mt_note')

    def unlink(self):
        """
        Archive devices instead of permanently deleting them.
        Displays a notification informing the user that nothing was permanently deleted
        and that the record was archived to preserve the safety & maintenance audit trail.
        """
        self.action_archive()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Device Archived',
                'message': 'Nothing was permanently deleted. The record was archived to preserve the safety '
                           'and maintenance audit trail.',
                'type': 'warning',
                'sticky': False,
            }
        }

    @api.model
    def get_import_templates(self):
        """Provide standard templates available for importing devices.
        Returns a list of dicts specifying labels and template asset file paths.
        """
        return [{
            'label': 'Import Template for Devices',
            'template': '/odoo_nhs_estate_assets/static/import_templates/devices.xlsx',
        }]
