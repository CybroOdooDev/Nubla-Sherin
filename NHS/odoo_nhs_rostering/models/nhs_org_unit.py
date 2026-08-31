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
from odoo import fields, models


class NhsOrgUnit(models.Model):
    """Extends the Establishment org unit with the (at most one) rostered
    unit built on top of it, so rostering can be reached from the org
    structure and record rules can scope leave/swaps by org unit."""
    _inherit = 'nhs.org.unit'

    roster_unit_ids = fields.One2many(
        'nhs.roster.unit', 'org_unit_id', string='Rostered Unit',
        help="The rostered unit built on this org unit, if e-Rostering is configured"
             " for it. At most one - enforced by a unique constraint on nhs.roster.unit."
    )
    is_rostered = fields.Boolean(
        string='Rostered',
        compute='_compute_is_rostered',
        help="This org unit has an e-Rostering unit configured for it."
    )

    def _compute_is_rostered(self):
        """ Method for compute is rostered """
        for unit in self:
            unit.is_rostered = bool(unit.roster_unit_ids)

    def action_view_roster_unit(self):
        """Open (or offer to create) the rostered unit for this org unit."""
        self.ensure_one()
        if self.roster_unit_ids:
            return {
                'name': 'Rostered Unit',
                'type': 'ir.actions.act_window',
                'res_model': 'nhs.roster.unit',
                'view_mode': 'form',
                'res_id': self.roster_unit_ids[0].id,
            }
        return {
            'name': 'Set Up Rostered Unit',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.roster.unit',
            'view_mode': 'form',
            'context': {'default_org_unit_id': self.id},
        }
