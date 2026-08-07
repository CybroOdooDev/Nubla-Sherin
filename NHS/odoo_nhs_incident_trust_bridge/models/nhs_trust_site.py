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


class NhsTrustSite(models.Model):
    """Extends nhs.trust.site to maintain a mirrored nhs.location record.

    Every Trust Site automatically gets a corresponding site-level nhs.location
    so that incident reporters can select it from the Locations menu without
    manual duplication.
    """
    _inherit = 'nhs.trust.site'

    location_id = fields.Many2one(
        'nhs.location',
        string='Incident Location',
        ondelete='set null',
        copy=False,
        readonly=True,
        help='Auto-created nhs.location (type=Site) for use in Incident & Risk reporting.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for site in records:
            loc = self.env['nhs.location'].create({
                'name': site.name,
                'location_type': 'site',
                'trust_id': site.trust_id.id,
                'ods_site_code': site.code or False,
                'trust_site_id': site.id,
            })
            site.with_context(no_location_sync=True).location_id = loc
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('no_location_sync'):
            return res
        for site in self:
            if not site.location_id:
                continue
            loc_vals = {}
            if 'name' in vals:
                loc_vals['name'] = vals['name']
            if 'trust_id' in vals:
                loc_vals['trust_id'] = vals['trust_id']
            if 'code' in vals:
                loc_vals['ods_site_code'] = vals.get('code') or False
            if 'active' in vals:
                loc_vals['active'] = vals['active']
            if loc_vals:
                site.location_id.write(loc_vals)
        return res

    def unlink(self):
        locations = self.mapped('location_id').filtered(lambda l: l.exists())
        res = super().unlink()
        locations.unlink()
        return res
