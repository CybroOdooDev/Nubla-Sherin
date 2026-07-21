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
from odoo.exceptions import ValidationError


class NhsDsptStandard(models.Model):
    """Represents a DSPT Standard or theme within a toolkit edition."""
    _name = 'nhs.dspt.standard'
    _description = 'DSPT Standard / Theme within an edition'
    _order = 'edition_id, sequence, name'

    name = fields.Char(
        string='Standard',
        required=True,
        help="Standard/theme name (National Data Guardian theme)."
    )
    edition_id = fields.Many2one(
        'nhs.dspt.edition',
        string='Edition',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning edition."
    )
    code = fields.Char(
        string='Reference',
        help="Standard reference."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    assertion_def_ids = fields.One2many(
        'nhs.dspt.assertion.def',
        'standard_id',
        string='Assertions',
        help="Assertions under this standard."
    )
    assertion_count = fields.Integer(
        string='Assertion Count',
        compute='_compute_assertion_count',
    )

    @api.depends('assertion_def_ids')
    def _compute_assertion_count(self):
        """Computes the number of assertion definitions under this standard."""
        for standard in self:
            standard.assertion_count = len(standard.assertion_def_ids)

    @api.constrains('code', 'edition_id')
    def _check_code_unique_per_edition(self):
        """Validates that the standard reference is unique within its edition."""
        for standard in self:
            if not standard.code:
                continue
            duplicate = self.search([
                ('edition_id', '=', standard.edition_id.id),
                ('code', '=', standard.code),
                ('id', '!=', standard.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    "Standard reference '%(code)s' is already used by '%(name)s'"
                    " in edition %(edition)s. References must be unique within an edition." % {
                        'code': standard.code,
                        'name': duplicate.name,
                        'edition': standard.edition_id.name,
                    }
                )

    def action_open_standard(self):
        """Returns an action to open the form view of this standard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.standard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def get_import_templates(self):
        """Import template offered on the Standards import wizard."""
        return [{
            'label': 'Import Template for DSPT Standards',
            'template': '/odoo_nhs_dspt/static/import_templates/dspt_standards_import_template.xlsx',
        }]
