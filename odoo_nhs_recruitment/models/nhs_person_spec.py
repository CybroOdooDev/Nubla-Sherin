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


class NhsPersonSpecCriterion(models.Model):
    """One essential/desirable criterion within a person specification."""
    _name = 'nhs.person.spec.criterion'
    _description = 'Person specification criterion'
    _order = 'sequence, id'

    spec_id = fields.Many2one(
        'nhs.person.spec',
        string='Person Specification',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(
        string='Criterion',
        required=True,
        help="e.g. 'NMC registration', 'Two years' acute ward experience'."
    )
    category = fields.Selection([
        ('qualification', 'Qualification'),
        ('experience', 'Experience'),
        ('skill', 'Skill'),
        ('values', 'Values'),
    ], string='Category', required=True, default='experience')
    essential = fields.Selection([
        ('essential', 'Essential'),
        ('desirable', 'Desirable'),
    ], string='Essential / Desirable', required=True, default='essential')
    assessment_method = fields.Selection([
        ('application', 'Application'),
        ('interview', 'Interview'),
        ('test', 'Test'),
    ], string='Assessed At', required=True, default='application',
        help="Stage at which this criterion is scored."
    )
    weight = fields.Float(
        string='Weight',
        default=1.0,
        help="Relative weight applied when aggregating scores against this criterion."
    )


class NhsPersonSpec(models.Model):
    """A person specification: essential/desirable criteria that shortlisting
    and interview scoring are assessed against, for fairness and auditability."""
    _name = 'nhs.person.spec'
    _description = 'Person specification'
    _order = 'name'

    name = fields.Char(
        string='Title',
        required=True,
        help="Spec title, often reusable across vacancies for the same role."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Leave blank to make the spec available to all companies."
    )
    job_description = fields.Binary(string='Job Description', attachment=True)
    job_description_filename = fields.Char(string='Job Description Filename')
    criterion_ids = fields.One2many(
        'nhs.person.spec.criterion',
        'spec_id',
        string='Criteria',
    )
    vacancy_count = fields.Integer(
        string='Vacancies Using This Spec',
        compute='_compute_vacancy_count',
    )
    active = fields.Boolean(string='Active', default=True)

    def _compute_vacancy_count(self):
        counts = self.env['nhs.vacancy']._read_group(
            [('person_spec_id', 'in', self.ids)],
            ['person_spec_id'], ['__count'],
        )
        by_spec = {spec.id: count for spec, count in counts}
        for spec in self:
            spec.vacancy_count = by_spec.get(spec.id, 0)
