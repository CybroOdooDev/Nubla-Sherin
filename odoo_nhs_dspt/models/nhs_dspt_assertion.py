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
from odoo import _, api, fields, models

ASSERTION_STATUSES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('met', 'Met'),
    ('not_met', 'Not Met'),
    ('not_applicable', 'Not Applicable'),
]


class NhsDsptAssertion(models.Model):
    """Represents a specific assertion on a DSPT assessment."""
    _name = 'nhs.dspt.assertion'
    _inherit = ['mail.thread']
    _description = 'DSPT Assertion Line (on an assessment)'
    _order = 'standard_id, reference'

    name = fields.Char(
        string='Assertion',
        related='assertion_def_id.name',
        store=True,
    )
    reference = fields.Char(
        string='Reference',
        related='assertion_def_id.reference',
        store=True,
    )
    assessment_id = fields.Many2one(
        'nhs.dspt.assessment',
        string='Assessment',
        required=True,
        ondelete='cascade',
        index=True,
        help="Owning assessment."
    )
    assertion_def_id = fields.Many2one(
        'nhs.dspt.assertion.def',
        string='Assertion Definition',
        required=True,
        ondelete='restrict',
        index=True,
        help="The assertion definition."
    )
    standard_id = fields.Many2one(
        'nhs.dspt.standard',
        string='Standard',
        related='assertion_def_id.standard_id',
        store=True,
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        tracking=True,
        help="Responsible owner."
    )
    status = fields.Selection(
        ASSERTION_STATUSES,
        string='Status',
        compute='_compute_status',
        store=True,
        tracking=True,
        help="Derived from its evidence lines: all mandatory evidence 'met'"
             " (not-applicable excluded) → 'met'; any mandatory 'not met' →"
             " 'not met'; otherwise 'in progress' once something has started."
    )
    evidence_ids = fields.One2many(
        'nhs.dspt.evidence',
        'assertion_id',
        string='Evidence Items',
        help="Evidence lines under this assertion."
    )
    evidence_count = fields.Integer(
        string='Evidence Count',
        compute='_compute_evidence_count',
    )
    mandatory_met_count = fields.Integer(
        string='Mandatory Met',
        compute='_compute_evidence_count',
    )
    mandatory_total_count = fields.Integer(
        string='Mandatory Total',
        compute='_compute_evidence_count',
    )
    note = fields.Text(
        string='Notes',
        help="Assertion-level commentary."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='assessment_id.company_id',
        store=True,
    )

    @api.depends('evidence_ids')
    def _compute_evidence_count(self):
        """Computes total, mandatory, and met evidence item counts for this assertion."""
        for assertion in self:
            assertion.evidence_count = len(assertion.evidence_ids)
            mandatory = assertion.evidence_ids.filtered(lambda e: e.is_mandatory and e.status != 'not_applicable')
            assertion.mandatory_total_count = len(mandatory)
            assertion.mandatory_met_count = len(mandatory.filtered(lambda e: e.status == 'met'))

    @api.depends('evidence_ids.status', 'evidence_ids.is_mandatory')
    def _compute_status(self):
        """Computes the overall compliance status of the assertion based on its evidence items."""
        for assertion in self:
            evidence = assertion.evidence_ids
            applicable = evidence.filtered(lambda e: e.status != 'not_applicable')
            if not applicable:
                assertion.status = 'not_applicable' if evidence else 'not_started'
                continue
            mandatory = applicable.filtered('is_mandatory')
            if mandatory and any(e.status == 'not_met' for e in mandatory):
                assertion.status = 'not_met'
            elif mandatory and all(e.status == 'met' for e in mandatory):
                assertion.status = 'met'
            elif not mandatory and all(e.status == 'met' for e in applicable):
                assertion.status = 'met'
            elif any(e.status in ('in_progress', 'met', 'not_met') for e in applicable):
                assertion.status = 'in_progress'
            else:
                assertion.status = 'not_started'

    def action_view_evidence(self):
        """Returns an action to open the evidence items related to this assertion."""
        self.ensure_one()
        return {
            'name': _('Evidence Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.evidence',
            'view_mode': 'list,form',
            'domain': [('assertion_id', '=', self.id)],
            'context': {'default_assertion_id': self.id, 'default_assessment_id': self.assessment_id.id},
        }
