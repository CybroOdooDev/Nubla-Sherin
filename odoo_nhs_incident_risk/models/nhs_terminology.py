from odoo import api, fields, models


class NhsTerminology(models.Model):
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
    ], string='Provider Type', required=True)
    logical_key = fields.Char(string='Logical Key', required=True,
                              help='e.g. person_affected, location_unit, incident_word')
    label = fields.Char(string='Display Label', required=True)

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
