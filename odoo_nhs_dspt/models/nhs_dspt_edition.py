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
from odoo.exceptions import UserError


class NhsDsptEdition(models.Model):
    """Represents a version/edition of the NHS DSPT toolkit framework."""
    _name = 'nhs.dspt.edition'
    _inherit = ['mail.thread']
    _description = 'A versioned DSPT edition (toolkit year)'
    _order = 'year desc'

    name = fields.Char(
        string='Name',
        required=True,
        help="Display, e.g. 'DSPT 2025/26'."
    )
    year = fields.Char(
        string='Year',
        required=True,
        help="Toolkit year/edition, e.g. '2025/26'. Must be unique."
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', required=True, default='draft', tracking=True,
        help="Only one edition is normally 'active' at a time; assessments are"
             " created against it. Draft editions are still being configured;"
             " archived editions are kept for history.")
    deadline = fields.Date(
        string='Publication Deadline',
        help="Publication deadline for this edition."
    )
    standard_ids = fields.One2many(
        'nhs.dspt.standard',
        'edition_id',
        string='Standards',
        help="Standards/themes in this edition."
    )
    assertion_count = fields.Integer(
        string='Assertions',
        compute='_compute_counts',
    )
    evidence_count = fields.Integer(
        string='Evidence Items',
        compute='_compute_counts',
    )
    assessment_count = fields.Integer(
        string='Assessments',
        compute='_compute_counts',
    )
    standard_count = fields.Integer(
        string='Standards Count',
        compute='_compute_standard_count',
    )
    notes = fields.Text(
        string='Notes',
        help="What changed this edition."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _year_uniq = models.Constraint(
        'unique(year)',
        'A DSPT edition for this year already exists.',
    )

    @api.depends('standard_ids')
    def _compute_standard_count(self):
        """Computes the total number of standards defined in this edition."""
        for edition in self:
            edition.standard_count = len(edition.standard_ids)

    @api.depends('standard_ids.assertion_def_ids', 'standard_ids.assertion_def_ids.evidence_def_ids')
    def _compute_counts(self):
        """Computes assertion, evidence, and assessment counts linked to this edition."""
        Assessment = self.env['nhs.dspt.assessment']
        for edition in self:
            assertions = edition.standard_ids.assertion_def_ids
            edition.assertion_count = len(assertions)
            edition.evidence_count = len(assertions.evidence_def_ids)
            edition.assessment_count = Assessment.search_count([('edition_id', '=', edition.id)])

    def action_view_assessments(self):
        """Returns an action to view assessments for this edition."""
        self.ensure_one()
        return {
            'name': ('Assessments'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.dspt.assessment',
            'view_mode': 'list,form',
            'domain': [('edition_id', '=', self.id)],
            'context': {'default_edition_id': self.id},
        }

    def action_activate(self):
        """Activates the edition by changing its state to 'active'."""
        for edition in self:
            edition.state = 'active'

    def action_archive_edition(self):
        """Archives the edition by changing its state to 'archived'."""
        for edition in self:
            edition.state = 'archived'

    def copy_edition(self, new_year, new_name=False, new_deadline=False):
        """Deep-clones this edition's standards/assertions/evidence into a new
        edition, marking every copied item 'new' by default so a reviewer can
        mark individual items 'changed'/'removed' as they adjust the clone."""
        self.ensure_one()
        if self.env['nhs.dspt.edition'].search_count([('year', '=', new_year)]):
            raise UserError(('An edition for year %s already exists.') % new_year)
        new_edition = self.copy({
            'name': new_name or ('DSPT %s') % new_year,
            'year': new_year,
            'state': 'draft',
            'deadline': new_deadline,
            'standard_ids': [],
        })
        for standard in self.standard_ids:
            new_standard = standard.copy({
                'edition_id': new_edition.id,
                'assertion_def_ids': [],
            })
            for assertion_def in standard.assertion_def_ids:
                new_assertion = assertion_def.copy({
                    'standard_id': new_standard.id,
                    'change_flag': 'new',
                    'evidence_def_ids': [],
                })
                for evidence_def in assertion_def.evidence_def_ids:
                    evidence_def.copy({
                        'assertion_def_id': new_assertion.id,
                        'change_flag': 'new',
                    })
        return new_edition
