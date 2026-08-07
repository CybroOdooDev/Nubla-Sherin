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

class NhsEricItemDef(models.Model):
    _name = 'nhs.eric.item.def'
    _description = 'Definition of a single ERIC data item (field), incl. source mapping & rules'
    _order = 'section_id, sequence'

    name = fields.Char(
        string='Item Name',
        required=True,
        help='Item label as ERIC states it.'
    )
    code = fields.Char(
        string='Item Code',
        required=True,
        help='ERIC item code/reference.'
    )
    section_id = fields.Many2one(
        'nhs.eric.section',
        string='Section',
        required=True,
        ondelete='cascade',
        help='Owning section.'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order.'
    )
    data_type = fields.Selection(
        selection=[
            ('integer', 'Integer'),
            ('float', 'Float'),
            ('currency', 'Currency'),
            ('percent', 'Percent'),
            ('text', 'Text'),
            ('boolean', 'Boolean')
        ],
        string='Data Type',
        required=True,
        default='float',
        help='Data type of the item.'
    )
    reporting_level = fields.Selection(
        selection=[
            ('organisational', 'Organisational Level'),
            ('site', 'Site Level')
        ],
        string='Reporting Level',
        required=True,
        default='organisational',
        help='Whether the item is collected at the Organisation level or the individual Site level.'
    )
    site_id = fields.Many2one(
        'nhs.estate.site',
        string='Site',
        help='Specific site for site-level items.'
    )
    unit = fields.Char(
        string='Unit',
        help='Unit (m², £, kWh, count, %).'
    )
    source_type = fields.Selection(
        selection=[
            ('auto', 'Auto (from estate/compliance)'),
            ('manual', 'Manual Entry'),
            ('computed', 'Computed from other items')
        ],
        string='Source Type',
        required=True,
        default='manual',
        help='How the value is populated. Auto from estate/compliance, manual entry, or computed.'
    )
    source_key = fields.Char(
        string='Source Key Value',
        help='For auto: the resolver key identifying which estate/compliance figure feeds this item '
             '(e.g. "estate.total_gia", "estate.backlog.high", "compliance.pct.fire"). '
    )
    selection_source_key = fields.Selection(
        selection='_selection_source_key',
        string='Source Key',
        compute='_compute_selection_source_key',
        inverse='_inverse_selection_source_key',
        help='Dropdown selection of available resolver keys for auto source type'
    )
    required = fields.Boolean(
        string='Required',
        help='Whether ERIC requires this item (drives validation/gap).'
    )
    min_value = fields.Float(
        string='Minimum Value',
        help='Validation minimum range.'
    )
    max_value = fields.Float(
        string='Maximum Value',
        help='Validation maximum range.'
    )
    allowed_values = fields.Char(
        string='Allowed Values',
        help='For constrained items (comma list).'
    )
    help_text = fields.Text(
        string='Help Text',
        help='ERIC guidance note for the item.'
    )
    change_flag = fields.Selection(
        selection=[
            ('new', 'New'),
            ('changed', 'Changed'),
            ('removed', 'Removed'),
            ('unchanged', 'Unchanged')
        ],
        string='Change Flag',
        default='unchanged',
        help='New/changed/removed vs prior year — reviewer awareness.'
    )
    computed_input_ids = fields.Many2many(
        'nhs.eric.item.def',
        'nhs_eric_item_def_computed_rel',
        'item_def_id',
        'input_id',
        string='Computation Inputs',
        help='Items used as inputs for calculation'
    )
    computation_operator = fields.Selection([
        ('sum', 'Sum (+)'),
        ('avg', 'Average'),
        ('pct', 'Percentage (%)'),
        ('sub', 'Subtraction (-)'),
        ('mul', 'Multiplication (*)'),
        ('div', 'Division (/)'),
    ], string='Computation Operator', help='Operator used for calculation')

    def _selection_source_key(self):
        resolver = self.env['nhs.eric.source.resolver']
        keys = resolver.available_keys()
        return [(k, resolver.get_key_description(k)) for k in keys]

    @api.depends('source_key', 'source_type')
    def _compute_selection_source_key(self):
        resolver = self.env['nhs.eric.source.resolver']
        available_keys = resolver.available_keys()
        for record in self:
            if record.source_type == 'auto' and record.source_key in available_keys:
                record.selection_source_key = record.source_key
            else:
                record.selection_source_key = False

    def _inverse_selection_source_key(self):
        for record in self:
            if record.source_type == 'auto':
                record.source_key = record.selection_source_key

    @api.constrains('code', 'section_id')
    def _check_unique_code_in_section(self):
        """Ensure item code is unique within a section."""
        for record in self:
            existing = self.search([
                ('code', '=', record.code),
                ('section_id', '=', record.section_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(
                    'Item code must be unique within a section!'
                )

    @api.constrains('computed_input_ids')
    def _check_circular_dependencies(self):
        for record in self:
            if record in record.computed_input_ids:
                raise ValidationError("A computed item cannot have itself as an input.")

            # Recursive check for circular dependencies
            visited = set()
            def check_recursion(node):
                if node.id in visited:
                    return
                visited.add(node.id)
                for parent in node.computed_input_ids:
                    if parent.id == record.id:
                        raise ValidationError(f"Circular dependency detected involving item '{parent.name}'.")
                    check_recursion(parent)

            check_recursion(record)

    def name_get(self):
        """Return display name as [code] Item Name."""
        result = []
        for item in self:
            name = f"[{item.code}] {item.name}"
            result.append((item.id, name))
        return result