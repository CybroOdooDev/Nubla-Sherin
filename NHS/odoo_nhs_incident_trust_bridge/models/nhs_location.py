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


class NhsLocation(models.Model):
    """Extends nhs.location with a Trust link and ODS site code.

    trust_id is set directly on site-level locations and inherited by
    child wards/rooms via _onchange_parent_id so the full hierarchy is
    trust-scoped without requiring manual entry on every child record.
    """
    _inherit = 'nhs.location'

    trust_id = fields.Many2one(
        'nhs.trust',
        string='NHS Trust',
        ondelete='set null',
        index=True,
        help='The NHS Trust that owns this site, ward, or department. '
             'Set this on site-level records; child wards/rooms inherit '
             'the trust automatically when a parent is selected.',
    )
    ods_site_code = fields.Char(
        string='ODS Site Code',
        help='The NHS Digital ODS code for this specific site, if registered '
             'separately from the trust (e.g. RJ112 for a hospital site within '
             'a trust). Used in LFPSE export.',
    )
    trust_site_id = fields.Many2one(
        'nhs.trust.site',
        string='Trust Site',
        ondelete='set null',
        index=True,
        help='The nhs.trust.site record that auto-created this location. '
             'Read-only — managed by the bridge module.',
    )
    trust_department_id = fields.Many2one(
        'nhs.trust.department',
        string='Trust Department',
        ondelete='set null',
        index=True,
        help='The nhs.trust.department record that auto-created this location. '
             'Read-only — managed by the bridge module.',
    )
    trust_complete_name = fields.Char(
        string='Trust / Location',
        compute='_compute_trust_complete_name',
        help='Display name prefixed with the trust short name for '
             'disambiguation in multi-trust location pickers.',
    )

    @api.depends('trust_id', 'complete_name')
    def _compute_trust_complete_name(self):
        for rec in self:
            if rec.trust_id:
                prefix = rec.trust_id.short_name or rec.trust_id.name
                rec.trust_complete_name = f'[{prefix}] {rec.complete_name}'
            else:
                rec.trust_complete_name = rec.complete_name

    def _compute_display_name(self):
        """Show [TrustShortName] prefix in all Many2one pickers when a trust
        is linked, so users can distinguish same-named wards across trusts.
        Locations with no trust show the plain hierarchical complete_name."""
        super()._compute_display_name()
        for rec in self:
            if rec.trust_id:
                prefix = rec.trust_id.short_name or rec.trust_id.name
                rec.display_name = f'[{prefix}] {rec.complete_name}'

    @api.onchange('parent_id')
    def _onchange_parent_trust(self):
        """Inherit the parent location's trust when a parent is selected,
        so wards/rooms created under a site auto-fill the trust field."""
        if self.parent_id and self.parent_id.trust_id and not self.trust_id:
            self.trust_id = self.parent_id.trust_id
