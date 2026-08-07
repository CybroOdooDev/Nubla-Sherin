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
from odoo.exceptions import UserError, ValidationError

class NHSDevicePassportWizard(models.TransientModel):
    """
    Device Passport Report Wizard
    =============================
    Allows users to generate and download a PDF Device Passport report
    with filters for device type (All Devices, Medical Devices Only,
    or Non-Medical Devices Only) and category selections.
    """
    _name = 'nhs.device.passport.wizard'
    _description = 'Device Passport Report Wizard'

    device_type = fields.Selection(
        selection=[
            ('all', 'All Devices'),
            ('medical', 'Medical Devices Only'),
            ('non_medical', 'Non-Medical Devices Only'),
        ],
        string='Device Scope',
        default='all',
        required=True,
        help='Select whether to fetch all devices, medical devices only, or non-medical devices only.'
    )
    mode = fields.Selection(
        selection=[
            ('all', 'All Categories'),
            ('category', 'Category-Based Devices'),
        ],
        string='Category Selection',
        default='all',
        required=True,
        help='Select whether to generate device passport PDF for all categories or specific categories.'
    )
    category_ids = fields.Many2many(
        'nhs.device.category',
        string='Device Categories',
        help='Select one or more device categories to include in the report.'
    )

    def action_generate_pdf(self):
        """
        Generate and download the Device Passport PDF report matching selected criteria.
        """
        self.ensure_one()
        domain = []
        if self.device_type == 'medical':
            domain.append(('is_medical_device', '=', True))
        elif self.device_type == 'non_medical':
            domain.append(('is_medical_device', '=', False))
        if self.mode == 'category':
            if not self.category_ids:
                raise ValidationError('Please select at least one device category.')
            domain.append(('category_id', 'in', self.category_ids.ids))
        devices = self.env['nhs.device'].search(domain)
        if not devices:
            raise UserError('No devices found matching the selected criteria.')
        return self.env.ref('odoo_nhs_estate_assets.action_report_nhs_device_passport').report_action(devices)
