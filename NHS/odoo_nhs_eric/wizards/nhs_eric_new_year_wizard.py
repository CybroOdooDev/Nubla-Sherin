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


class NhsEricNewYearWizard(models.TransientModel):
    """
    Wizard for cloning an ERIC data set to a new year.

    This wizard allows users to clone an existing data set to a new
    financial year, copying all sections and item definitions.
    """
    _name = 'nhs.eric.new.year.wizard'
    _description = 'ERIC New Year Wizard'

    dataset_id = fields.Many2one(
        'nhs.eric.dataset',
        string='Source Data Set',
        required=True,
        help='The existing data set to clone from.'
    )
    new_name = fields.Char(
        string='New Name',
        required=True,
        help='The name for the new data set, e.g. "ERIC 2026/27".'
    )
    new_year = fields.Char(
        string='New Year',
        required=True,
        help='The financial year for the new data set, e.g. "2026/27".'
    )
    new_dataset_id = fields.Many2one(
        'nhs.eric.dataset',
        string='New Data Set',
        readonly=True,
        help='The newly created data set.'
    )
    copy_sections = fields.Boolean(
        string='Copy Sections',
        default=True,
        help='If checked, copies all sections from the source data set.'
    )
    copy_items = fields.Boolean(
        string='Copy Items',
        default=True,
        help='If checked, copies all items from the source data set.'
    )
    copy_mappings = fields.Boolean(
        string='Copy Mappings',
        default=True,
        help='If checked, copies all source key mappings.'
    )
    set_change_flags = fields.Boolean(
        string='Set Change Flags',
        default=True,
        help='If checked, sets initial change flags to unchanged.'
    )

    def action_clone(self):
        """
        Execute the clone operation.

        Creates a new data set for the new year and copies all sections and
        items from the source data set. Updates change flags based on
        differences between the two years.

        Returns:
            dict: Action to open the newly created data set
        """
        self.ensure_one()
        existing = self.env['nhs.eric.dataset'].search([
            ('year', '=', self.new_year)
        ])
        if existing:
            raise UserError(f'A data set for year {self.new_year} already exists!')
        new_dataset = self.env['nhs.eric.dataset'].create({
            'name': self.new_name,
            'year': self.new_year,
            'state': 'draft',
            'prior_dataset_id': self.dataset_id.id,
            'notes': f'Cloned from {self.dataset_id.name} on {fields.Date.today()}'
        })
        if self.copy_sections:
            for section in self.dataset_id.section_ids:
                new_section = self.env['nhs.eric.section'].create({
                    'name': section.name,
                    'dataset_id': new_dataset.id,
                    'sequence': section.sequence,
                    'code': section.code,
                })
                if self.copy_items:
                    for item_def in section.item_def_ids:
                        if item_def.change_flag == 'removed':
                            continue
                        self.env['nhs.eric.item.def'].create({
                            'name': item_def.name,
                            'code': item_def.code,
                            'section_id': new_section.id,
                            'sequence': item_def.sequence,
                            'data_type': item_def.data_type,
                            'reporting_level': item_def.reporting_level,
                            'unit': item_def.unit,
                            'source_type': item_def.source_type,
                            'source_key': item_def.source_key if self.copy_mappings else False,
                            'required': item_def.required,
                            'min_value': item_def.min_value,
                            'max_value': item_def.max_value,
                            'allowed_values': item_def.allowed_values,
                            'help_text': item_def.help_text,
                            'change_flag': 'unchanged' if self.set_change_flags else 'new',
                        })
        self.write({'new_dataset_id': new_dataset.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.eric.dataset',
            'res_id': new_dataset.id,
            'view_mode': 'form',
        }