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
import re

class NhsEricDataset(models.Model):
    _name = 'nhs.eric.dataset'
    _description = 'A versioned ERIC data-set definition for a collection year'
    _order = 'year desc'

    name = fields.Char(
        string='Name',
        required=True,
        help='Display, e.g. "ERIC 2025/26".'
    )
    year = fields.Char(
        string='Financial Year',
        required=True,
        help='Financial year of the collection (e.g. "2025/26").'
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('archived', 'Archived')
        ],
        string='Status',
        required=True,
        default='draft',
        help='Only one active per year.'
    )
    section_ids = fields.One2many(
        'nhs.eric.section',
        'dataset_id',
        string='Sections',
        help='Sections in this year\'s return.'
    )
    item_count = fields.Integer(
        string='Total Items',
        compute='_compute_item_count',
        store=True,
        help='Total item definitions across sections.'
    )
    prior_dataset_id = fields.Many2one(
        'nhs.eric.dataset',
        string='Prior Year Data Set',
        help='The data-set version of the prior year, for tracking changes.'
    )
    notes = fields.Text(
        string='Notes',
        help='Notes on what changed this year.'
    )

    def action_view_items(self):
        """Return an action displaying all items associated with this dataset.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Items',
            'res_model': 'nhs.eric.item.def',
            'view_mode': 'list,form',
            'domain': [('section_id', 'in', self.section_ids.ids)],
        }

    @api.depends('section_ids.item_def_ids', 'section_ids.item_def_ids.change_flag')
    def _compute_item_count(self):
        """Compute total item definitions across all sections, excluding removed ones."""
        for record in self:
            count = 0
            for section in record.section_ids:
                count += len(section.item_def_ids.filtered(lambda i: i.change_flag != 'removed'))
            record.item_count = count

    def action_compare_with_prior(self):
        """
        Compare the current dataset's item definitions against the prior dataset's
        item definitions by item code. Marks items as new, changed, or unchanged.
        Re-creates removed items as placeholder definitions with change_flag = 'removed'.
        """
        self.ensure_one()
        if not self.prior_dataset_id:
            return True

        # Map prior items by code
        prior_items = {}
        for section in self.prior_dataset_id.section_ids:
            for item in section.item_def_ids:
                if item.code:
                    prior_items[item.code] = item

        # Map current items by code
        current_items = {}
        for section in self.section_ids:
            for item in section.item_def_ids:
                if item.code:
                    current_items[item.code] = item

        # Fields to compare to detect "changed" items
        fields_to_compare = [
            'name', 'data_type', 'unit', 'source_type', 'source_key',
            'required', 'min_value', 'max_value', 'allowed_values'
        ]

        # 1. Update current items (new, changed, unchanged)
        for code, item in current_items.items():
            if item.change_flag == 'removed':
                continue

            if code not in prior_items:
                item.write({'change_flag': 'new'})
            else:
                prior_item = prior_items[code]
                changed = False
                for field in fields_to_compare:
                    if getattr(item, field) != getattr(prior_item, field):
                        changed = True
                        break
                
                # Also check section code
                if item.section_id.code != prior_item.section_id.code:
                    changed = True

                if changed:
                    item.write({'change_flag': 'changed'})
                else:
                    item.write({'change_flag': 'unchanged'})

        # 2. Identify removed items and create/update placeholder records with change_flag = 'removed'
        for code, prior_item in prior_items.items():
            if code not in current_items:
                # Need to find or create the matching section in the current dataset
                prior_section = prior_item.section_id
                current_section = self.section_ids.filtered(lambda s: s.code == prior_section.code)
                if not current_section:
                    current_section = self.section_ids.filtered(lambda s: s.name == prior_section.name)
                
                if not current_section:
                    # Create the section in current dataset
                    current_section = self.env['nhs.eric.section'].create({
                        'name': prior_section.name,
                        'code': prior_section.code,
                        'sequence': prior_section.sequence,
                        'dataset_id': self.id
                    })
                
                # Check if we already have a record for this code marked as removed
                existing_removed = self.env['nhs.eric.item.def'].search([
                    ('section_id', 'in', self.section_ids.ids),
                    ('code', '=', code),
                    ('change_flag', '=', 'removed')
                ])

                if not existing_removed:
                    self.env['nhs.eric.item.def'].create({
                        'name': prior_item.name,
                        'code': prior_item.code,
                        'section_id': current_section.id,
                        'sequence': prior_item.sequence,
                        'data_type': prior_item.data_type,
                        'unit': prior_item.unit,
                        'source_type': prior_item.source_type,
                        'source_key': prior_item.source_key,
                        'required': prior_item.required,
                        'min_value': prior_item.min_value,
                        'max_value': prior_item.max_value,
                        'allowed_values': prior_item.allowed_values,
                        'help_text': prior_item.help_text,
                        'change_flag': 'removed'
                    })

        return True

    @api.constrains('year')
    def _check_year_format(self):
        """Validate year format is YYYY/YY."""
        for record in self:
            if record.year:
                # Pattern: 1-4 digits before '/', 2 digits after
                pattern = r'^\d{1,4}/\d{2}$'
                if not re.match(pattern, record.year):
                    raise ValidationError(
                        'Year must be in format YYYY/YY, e.g. 2025/26 or 25/26'
                    )

    @api.constrains('year')
    def _check_unique_year(self):
        """Ensure only one dataset per year exists."""
        for record in self:
            if record.year:
                existing = self.search([
                    ('year', '=', record.year),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(
                        'A dataset for year %s already exists!' % record.year
                    )

    def action_activate(self):
        """Set dataset status to active."""
        self.write({'state': 'active'})
        return True

    def action_archive(self):
        """Set dataset status to archived."""
        self.write({'state': 'archived'})
        return True

    def action_draft(self):
        """Set dataset status to draft."""
        self.write({'state': 'draft'})
        return True

    def action_clone_year(self):
        """Open wizard to clone this dataset to a new year."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Year',
            'res_model': 'nhs.eric.new.year.wizard',
            'view_mode': 'form',
            'context': {
                'default_dataset_id': self.id,
            },
            'target': 'new',
        }