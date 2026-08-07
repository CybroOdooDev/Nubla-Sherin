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

class NHSCompliancePositionReportWizard(models.TransientModel):
    _name = 'nhs.compliance.position.report.wizard'
    _description = 'Compliance Position Report Wizard'

    scope = fields.Selection([
        ('whole', 'Whole Estate'),
        ('site', 'Per Site'),
        ('discipline', 'Per Discipline')
    ], string='Scope', required=True, default='whole')
    site_id = fields.Many2one('nhs.estate.site', string='Site')
    discipline_id = fields.Many2one('nhs.compliance.discipline', string='Discipline')
    statutory_filter = fields.Selection([
        ('all', 'All Records'),
        ('statutory', 'Statutory Only'),
        ('non_statutory', 'Non-Statutory Only')
    ], string='Statutory Filter', default='all', required=True)

    @api.onchange('scope')
    def _onchange_scope(self):
        if self.scope == 'whole':
            self.site_id = False
            self.discipline_id = False
        elif self.scope == 'site':
            self.discipline_id = False
        elif self.scope == 'discipline':
            self.site_id = False

    def action_print_pdf(self):
        domain = [('active', '=', True)]
        if self.scope == 'site':
            if not self.site_id:
                raise UserError("Please select a Site.")
            domain.append(('site_id', '=', self.site_id.id))
        elif self.scope == 'discipline':
            if not self.discipline_id:
                raise UserError("Please select a Discipline.")
            domain.append(('discipline_id', '=', self.discipline_id.id))
        if self.statutory_filter == 'statutory':
            domain.append(('compliance_type_id.is_statutory', '=', True))
        elif self.statutory_filter == 'non_statutory':
            domain.append(('compliance_type_id.is_statutory', '=', False))
        as_at_date = fields.Date.today()
        items = self.env['nhs.compliance.item'].search(domain)
        items = items.filtered(lambda i: i.create_date.date() <= as_at_date)
        if not items:
            raise UserError("No compliance records found matching your criteria.")
        return self.env.ref('odoo_nhs_estate_compliance.report_nhs_compliance_position').with_context(
            discard_logo_check=True,
            till_date=as_at_date
        ).report_action(items)
