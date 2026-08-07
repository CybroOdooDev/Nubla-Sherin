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

class NHSESFunction(models.Model):
    _name = 'nhs.estate.function'
    _description = 'Estate function / use (ERIC-aligned)'
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(
        string='Function Name',
        required=True,
        help="Name of the building function or use type (e.g., 'Clinical Ward', 'Outpatient', 'Administration')"
    )
    parent_id = fields.Many2one(
        'nhs.estate.function',
        string='Parent Function',
        ondelete='restrict',
        help="Parent function category for hierarchical classification of building functions"
    )
    parent_path = fields.Char(
        string='Parent Path',
        index=True,
        help="Hierarchical path of parent functions for efficient tree structure navigation"
    )
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        recursive=True,
        store=True,
        help="Full hierarchical name showing the complete function path (e.g., 'Clinical > Ward > Surgical')"
    )
    is_clinical = fields.Boolean(
        string='Clinical',
        default=False,
        help="Indicates whether this function is clinical/patient-facing (true) or non-clinical (false)"
    )
    eric_category = fields.Char(
        string='ERIC Category',
        help="ERIC (Estates Returns Information Collection) category classification code for NHS reporting"
    )
    active = fields.Boolean(
        default=True,
        help="Whether this function record is active and available for selection"
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """Compute the full hierarchical name path for the function.
        Recursively prepends the complete name of the parent function, if one
        exists, to the name of the current function, separated by ' / '.
        """
        for record in self:
            if record.parent_id and record.parent_id.complete_name:
                record.complete_name = f"{record.parent_id.complete_name} / {record.name}"
            else:
                record.complete_name = record.name

    def _compute_display_name(self):
        """Compute the display name for the function.
        Sets the display name to the full hierarchical name (`complete_name`)
        or falls back to the local `name` if `complete_name` is not set.
        """
        for record in self:
            record.display_name = record.complete_name or record.name
