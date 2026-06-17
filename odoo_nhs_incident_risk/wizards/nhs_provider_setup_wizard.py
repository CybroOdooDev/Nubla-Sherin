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


class NhsProviderSetupWizard(models.TransientModel):
    _name = 'nhs.provider.setup.wizard'
    _description = 'Provider Setup Wizard (first-run preset activation)'

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
       default=lambda self: self.env.company.provider_type or 'nhs_trust',
       help='Select the type of CQC-registered provider that best describes your organisation. '
            'This setting activates the appropriate incident categories, terminology pack, '
            'and notification rules for your provider type. It also configures the public '
            'reporting form and generates a unique access token.')

    category_preview = fields.Text(string='Categories that will be activated',
                                   compute='_compute_preview', readonly=True,
                                   help='Preview of the top-level incident categories that will be made available '
                                        'for the selected provider type. Categories not applicable to your provider '
                                        'type will be archived.')

    @api.depends('provider_type')
    def _compute_preview(self):
        for rec in self:
            cats = self.env['nhs.incident.category'].search([
                '|',
                ('provider_types', '=', False),
                ('provider_types', 'like', rec.provider_type),
                ('parent_id', '=', False),
                ('active', 'in', [True, False]),
            ])
            rec.category_preview = ', '.join(cats.mapped('name')) or '(all universal categories)'

    def action_apply(self):
        self.ensure_one()
        company = self.env.company

        # Set provider type on company
        company.sudo().write({'provider_type': self.provider_type})

        # Ensure public form token exists
        company._get_public_form_token()

        # Archive categories not for this provider type
        all_cats = self.env['nhs.incident.category'].with_context(
            active_test=False).search([('provider_types', '!=', False)])
        for cat in all_cats:
            applicable = not cat.provider_types or \
                         self.provider_type in cat.provider_types.split(',')
            cat.write({'active': applicable})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Provider Setup Complete',
                'message': f'System configured for: {dict(self._fields["provider_type"].selection).get(self.provider_type)}.\n'
                           f'Public form token: {company.public_form_token}',
                'type': 'success',
                'sticky': True,
            }
        }
