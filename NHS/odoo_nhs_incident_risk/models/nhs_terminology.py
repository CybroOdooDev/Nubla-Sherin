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


class NhsTerminology(models.Model):
    """A provider-type-specific label override for a logical terminology key."""
    _name = 'nhs.terminology'
    _description = 'Terminology Pack (provider-type labels)'
    _order = 'provider_type, logical_key'

    provider_type = fields.Selection([
        ('nhs_trust', 'NHS Trust'),
        ('gp_practice', 'GP Practice / PCN'),
        ('care_home', 'Care Home'),
        ('domiciliary_care', 'Domiciliary Care'),
        ('independent_hospital', 'Independent Hospital'),
        ('hospice', 'Hospice'),
        ('pharmacy', 'Pharmacy'),
        ('dental', 'Dental Practice'),
    ], string='Provider Type', required=True,
       help='The provider type this terminology entry applies to. '
            'Each provider type can have its own preferred wording for common terms.')
    logical_key = fields.Char(string='Logical Key', required=True,
                              help='e.g. person_affected, location_unit, incident_word')
    label = fields.Char(string='Display Label', required=True,
                        help='The label shown to users of this provider type in place of the default term '
                             '(e.g. "Resident" instead of "Patient" for a care home).')

    @api.model
    def t(self, key, provider_type=None):
        """Return the display label for the given logical key."""
        if not provider_type:
            provider_type = self.env.company.provider_type or 'nhs_trust'
        rec = self.search([
            ('provider_type', '=', provider_type),
            ('logical_key', '=', key),
        ], limit=1)
        return rec.label if rec else key.replace('_', ' ').title()
