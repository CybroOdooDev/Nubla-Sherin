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
       default=lambda self: self.env.company.provider_type or 'nhs_trust')

    category_preview = fields.Text(string='Categories that will be activated',
                                   compute='_compute_preview', readonly=True)

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
