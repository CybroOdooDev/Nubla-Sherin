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


class NhsDsptAssertionDef(models.Model):
    _name = 'nhs.dspt.assertion.def'
    _description = 'DSPT Assertion Definition'
    _order = 'standard_id, sequence, reference'

    name = fields.Char(
        string='Assertion',
        required=True,
        help="Assertion text/title, e.g. 'There is senior ownership of data"
             " security and protection'."
    )
    reference = fields.Char(
        string='Reference',
        required=True,
        help="Assertion reference, e.g. '1.1'."
    )
    standard_id = fields.Many2one(
        'nhs.dspt.standard',
        string='Standard',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning standard."
    )
    edition_id = fields.Many2one(
        'nhs.dspt.edition',
        string='Edition',
        related='standard_id.edition_id',
        store=True,
        index=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    applies_to_profile_ids = fields.Many2many(
        'nhs.dspt.org.profile',
        string='Applies To',
        help="Organisation types this assertion applies to. Leave blank to"
             " apply to every organisation type."
    )
    evidence_def_ids = fields.One2many(
        'nhs.dspt.evidence.def',
        'assertion_def_id',
        string='Evidence Items',
        help="Evidence items under this assertion."
    )
    evidence_count = fields.Integer(
        string='Evidence Count',
        compute='_compute_evidence_count',
    )
    change_flag = fields.Selection([
        ('new', 'New'),
        ('changed', 'Changed'),
        ('removed', 'Removed'),
    ], string='Change vs Prior Edition',
        help="Flags this assertion as new/changed/removed compared to the"
             " prior edition, for reviewer awareness.")

    @api.depends('evidence_def_ids')
    def _compute_evidence_count(self):
        for assertion_def in self:
            assertion_def.evidence_count = len(assertion_def.evidence_def_ids)

    def applies_to(self, org_profile):
        """True if this assertion definition is applicable to `org_profile`
        (a single nhs.dspt.org.profile record). Blank applicability = applies
        to every organisation type."""
        self.ensure_one()
        return not self.applies_to_profile_ids or org_profile in self.applies_to_profile_ids
