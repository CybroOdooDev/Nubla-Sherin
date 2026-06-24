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

STANDARD_WARDS = [
    ('Emergency Department', 'unit'),
    ('Medical Ward', 'unit'),
    ('Surgical Ward', 'unit'),
    ('Critical Care / ICU', 'unit'),
    ('Maternity Unit', 'unit'),
    ('Outpatients', 'unit'),
    ('Pharmacy', 'unit'),
    ('Radiology', 'unit'),
    ('Theatres', 'unit'),
]


class NhsTrustLocationSetupWizard(models.TransientModel):
    """Quick-setup wizard that creates a site location for the trust and
    optionally populates it with standard NHS ward/department locations."""
    _name = 'nhs.trust.location.setup.wizard'
    _description = 'Trust Location Hierarchy Setup'

    trust_id = fields.Many2one(
        'nhs.trust',
        string='NHS Trust',
        required=True,
        readonly=True,
    )
    site_name = fields.Char(
        string='Site Name',
        required=True,
        help='Name of the top-level site location (e.g. "Main Hospital Site", '
             '"North Campus"). This becomes the root of the hierarchy.',
    )
    ods_site_code = fields.Char(
        string='ODS Site Code',
        help='Optional NHS Digital ODS code for this specific site.',
    )
    create_standard_wards = fields.Boolean(
        string='Create Standard NHS Ward/Department Locations',
        default=True,
        help='Automatically creates common NHS ward and department locations '
             '(Emergency, Medical Ward, Surgical Ward, ICU, etc.) under the site.',
    )
    custom_ward_ids = fields.One2many(
        'nhs.trust.location.setup.ward.line',
        'wizard_id',
        string='Custom Locations',
        help='Add additional ward or department locations to create under this site.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.onchange('trust_id')
    def _onchange_trust_id(self):
        if self.trust_id and not self.site_name:
            self.site_name = self.trust_id.short_name or self.trust_id.name

    def action_create_locations(self):
        self.ensure_one()
        Location = self.env['nhs.location']

        # Create the top-level site
        site = Location.create({
            'name': self.site_name,
            'location_type': 'site',
            'trust_id': self.trust_id.id,
            'ods_site_code': self.ods_site_code or False,
            'company_id': self.company_id.id,
        })

        wards_to_create = []
        if self.create_standard_wards:
            wards_to_create += STANDARD_WARDS
        for line in self.custom_ward_ids:
            wards_to_create.append((line.name, line.location_type))

        for ward_name, ward_type in wards_to_create:
            Location.create({
                'name': ward_name,
                'location_type': ward_type,
                'parent_id': site.id,
                'trust_id': self.trust_id.id,
                'company_id': self.company_id.id,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': f'Locations — {self.trust_id.short_name or self.trust_id.name}',
            'res_model': 'nhs.location',
            'view_mode': 'list,form',
            'domain': [('trust_id', '=', self.trust_id.id)],
        }


class NhsTrustLocationSetupWardLine(models.TransientModel):
    """Inline line for custom ward/department entries in the setup wizard."""
    _name = 'nhs.trust.location.setup.ward.line'
    _description = 'Custom Location Line'

    wizard_id = fields.Many2one(
        'nhs.trust.location.setup.wizard',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Location Name', required=True)
    location_type = fields.Selection([
        ('unit', 'Ward / Unit'),
        ('room', 'Room'),
    ], string='Type', required=True, default='unit')
