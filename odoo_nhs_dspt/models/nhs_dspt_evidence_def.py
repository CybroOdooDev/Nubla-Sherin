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


class NhsDsptEvidenceDef(models.Model):
    """Represents a standard NHS DSPT evidence item definition."""
    _name = 'nhs.dspt.evidence.def'
    _description = 'DSPT Evidence-Item Definition'
    _order = 'assertion_def_id, sequence, reference'

    name = fields.Char(
        string='Evidence Item',
        required=True,
        help="Evidence-item text/question."
    )
    reference = fields.Char(
        string='Reference',
        required=True,
        help="Evidence reference, e.g. '1.1.1'."
    )
    assertion_def_id = fields.Many2one(
        'nhs.dspt.assertion.def',
        string='Assertion',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning assertion."
    )
    standard_id = fields.Many2one(
        'nhs.dspt.standard',
        string='Standard',
        related='assertion_def_id.standard_id',
        store=True,
    )
    edition_id = fields.Many2one(
        'nhs.dspt.edition',
        string='Edition',
        related='assertion_def_id.edition_id',
        store=True,
        index=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    is_mandatory = fields.Boolean(
        string='Mandatory',
        required=True,
        default=True,
        help="Mandatory to meet the standard (vs supporting/higher-level evidence)."
    )
    applies_to_profile_ids = fields.Many2many(
        'nhs.dspt.org.profile',
        string='Applies To',
        help="Organisation-type applicability. Leave blank to apply to every"
             " organisation type."
    )
    guidance = fields.Text(
        string='Guidance',
        help="NHS guidance for the evidence item."
    )
    evidence_type_hint = fields.Char(
        string='Evidence Type Hint',
        help="What sort of evidence satisfies it (policy, training record,"
             " certificate…)."
    )
    change_flag = fields.Selection([
        ('new', 'New'),
        ('changed', 'Changed'),
        ('removed', 'Removed'),
    ], string='Change vs Prior Edition',
        help="Flags this evidence item as new/changed/removed compared to the"
             " prior edition, for reviewer awareness.")

    def applies_to(self, org_profile):
        """True if this evidence definition is applicable to `org_profile`
        (a single nhs.dspt.org.profile record). Blank applicability = applies
        to every organisation type."""
        self.ensure_one()
        return not self.applies_to_profile_ids or org_profile in self.applies_to_profile_ids

    def action_open_def(self):
        """Returns an action to open the form view of this evidence definition."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.evidence.def',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

