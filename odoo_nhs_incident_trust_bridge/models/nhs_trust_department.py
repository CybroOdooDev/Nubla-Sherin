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


class NhsTrustDepartment(models.Model):
    """Extends nhs.trust.department to maintain a mirrored nhs.location record.

    Every Trust Department automatically gets a corresponding unit-level
    nhs.location nested under the site's location so incident reporters can
    select it directly from the Locations list.
    """
    _inherit = 'nhs.trust.department'

    location_id = fields.Many2one(
        'nhs.location',
        string='Incident Location',
        ondelete='set null',
        copy=False,
        readonly=True,
        help='Auto-created nhs.location (type=Unit/Ward) for use in Incident & Risk reporting.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for dept in records:
            parent_loc = dept.site_id.location_id if dept.site_id else False
            loc = self.env['nhs.location'].create({
                'name': dept.name,
                'location_type': 'unit',
                'trust_id': dept.trust_id.id,
                'parent_id': parent_loc.id if parent_loc else False,
                'trust_department_id': dept.id,
            })
            dept.with_context(no_location_sync=True).location_id = loc
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('no_location_sync'):
            return res
        for dept in self:
            if not dept.location_id:
                continue
            loc_vals = {}
            if 'name' in vals:
                loc_vals['name'] = vals['name']
            if 'site_id' in vals:
                parent_loc = dept.site_id.location_id if dept.site_id else False
                loc_vals['parent_id'] = parent_loc.id if parent_loc else False
                loc_vals['trust_id'] = dept.trust_id.id if dept.trust_id else False
            if 'active' in vals:
                loc_vals['active'] = vals['active']
            if loc_vals:
                dept.location_id.write(loc_vals)
        return res

    def unlink(self):
        locations = self.mapped('location_id').filtered(lambda l: l.exists())
        res = super().unlink()
        locations.unlink()
        return res
