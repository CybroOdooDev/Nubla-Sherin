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
from odoo.exceptions import UserError

class NHSCertificatePackWizard(models.TransientModel):
    """Transient wizard for generating a certificate pack PDF report.
    Filters active compliance tests that have a certificate reference by site,
    building, discipline, and date range.  Triggers the QWeb certificate pack
    report action for the matching test records.
    """
    _name = 'nhs.certificate.pack.wizard'
    _description = 'Certificate Pack Wizard'

    site_id = fields.Many2one('nhs.estate.site', string='Site',
                        help='Filter certificates to tests performed at this site.  Leave blank to include all sites.')
    building_id = fields.Many2one('nhs.estate.building', string='Building',
            domain="[('site_id', '=', site_id)]" if 'site_id' else [],
            help='Filter certificates to tests at this building.  Only buildings in the selected site are available.')
    discipline_id = fields.Many2one('nhs.compliance.discipline', string='Discipline',
            help='Filter certificates to a specific compliance discipline.  Leave blank to include all disciplines.')
    date_from = fields.Date(string='Test Date From',
                            help='Include only tests performed on or after this date.')
    date_to = fields.Date(string='Test Date To',
                          help='Include only tests performed on or before this date.')

    @api.onchange('site_id')
    def _onchange_site_id(self):
        """Clear the building selection when the site changes to prevent stale selections."""
        if self.site_id and self.building_id.site_id != self.site_id:
            self.building_id = False

    def action_generate_pack(self):
        """Build a filtered domain and trigger the certificate pack PDF report.
        Applies the selected site, building, discipline, and date range filters
        to find matching active compliance tests that have a certificate
        reference.  Raises a UserError if no matching tests are found.
        """
        domain = [('active', '=', True), ('certificate_ref', '!=', False)]
        if self.site_id:
            domain.append(('item_id.site_id', '=', self.site_id.id))
        if self.building_id:
            domain.append(('item_id.building_id', '=', self.building_id.id))
        if self.discipline_id:
            domain.append(('item_id.discipline_id', '=', self.discipline_id.id))
        if self.date_from:
            domain.append(('test_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('test_date', '<=', self.date_to))
        tests = self.env['nhs.compliance.test'].search(domain)
        if not tests:
            raise UserError("No value")
        return self.env.ref('odoo_nhs_estate_compliance.report_nhs_certificate_pack').with_context(
            discard_logo_check=True).report_action(tests)
