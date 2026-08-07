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
#############################################################################
from odoo import api, fields, models


class NhsTrust(models.Model):
    """Extends nhs.trust with a location reverse-relation and a stat button
    so trust managers can navigate to sites/departments from the trust form."""
    _inherit = 'nhs.trust'

    location_ids = fields.One2many(
        'nhs.location',
        'trust_id',
        string='Locations',
        help='Sites, wards, and departments registered under this trust.',
    )
    location_count = fields.Integer(
        string='Locations',
        compute='_compute_location_count',
        help='Number of locations linked to this trust.',
    )

    @api.depends('location_ids')
    def _compute_location_count(self):
        Location = self.env['nhs.location']
        for trust in self:
            trust.location_count = Location.search_count(
                [('trust_id', '=', trust.id)])

    def action_view_locations(self):
        self.ensure_one()
        return {
            'name': f'Locations — {self.short_name or self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.location',
            'view_mode': 'list,form',
            'domain': [('trust_id', '=', self.id)],
            'context': {'default_trust_id': self.id},
        }

    def action_open_location_setup_wizard(self):
        self.ensure_one()
        wizard = self.env['nhs.trust.location.setup.wizard'].create({
            'trust_id': self.id,
            'site_name': self.short_name or self.name,
            'company_id': self.company_id.id,
        })
        return {
            'name': 'Setup Location Hierarchy',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.trust.location.setup.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
