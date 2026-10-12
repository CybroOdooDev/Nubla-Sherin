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
    """
        Model for ERIC Item Definitions. Tracks individual data fields within
        ERIC sections, including data types, validation rules, source mappings,
        and change flags for version comparison across financial years.
    """
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
    dataset_id = fields.Many2one(
        'nhs.eric.dataset',
        related='section_id.dataset_id',
        store=True,
        string='Dataset',
        index=True,
        help="Dataset owning this item."
    )
    computation_operator = fields.Selection([
        ('sum', 'Sum (+)'),
        ('avg', 'Average'),
        ('pct', 'Percentage (%)'),
        ('sub', 'Subtraction (-)'),
        ('mul', 'Multiplication (*)'),
        ('div', 'Division (/)'),
    ], string='Computation Operator', help='Operator used for calculation')
    computed_input_ids = fields.Many2many(
        'nhs.eric.item.def',
        'nhs_eric_item_def_computed_rel',
        'item_def_id',
        'input_id',
        string='Computation Inputs',
        domain="[('id', '!=', id), ('data_type', 'in', ['integer', 'float', 'currency', 'percent']), "
               "('dataset_id', '=', dataset_id), ('dataset_id', '!=', False)]",
        help='Numeric items used as inputs for calculation from the same dataset'
    )

    @api.onchange('source_type', 'dataset_id')
    def _onchange_computed_source_type(self):
        """
        Validate that computed source type is only allowed when at least 2 numeric
        items exist in the dataset. Ensures sufficient data is available for
        computed field calculations before allowing this source type selection.

        Raises:
            ValidationError: If dataset is not saved or doesn't have at least
                             2 numeric items (integer, float, currency, percent).
        """
        if self.source_type != 'computed':
            return
        if not self.dataset_id:
            raise ValidationError(
                "Computed Source Unavailable\n\n"
                "Please save the dataset first. "
                "At least 2 saved numeric items must exist in the dataset "
                "before you can use the Computed source type."
            )
        numeric_items = self.env['nhs.eric.item.def'].search([
            ('dataset_id', '=', self.dataset_id.id),
            ('id', '!=', self.id),
            ('data_type', 'in', ['integer', 'float', 'currency', 'percent']),
        ])
        if len(numeric_items) < 2:
            raise ValidationError(
                "Computed Source Unavailable\n\n"
                "At least 2 saved numeric items must exist in this dataset "
                "before you can use the Computed source type."
            )

    def _get_computed_inputs_domain(self):
        """Return dynamic domain for computed_input_ids field."""
        if self and hasattr(self, 'id') and self.id and self.dataset_id:
            return [
                ('id', '!=', self.id),
                ('data_type', 'in', ['integer', 'float', 'currency', 'percent']),
                ('dataset_id', '=', self.dataset_id.id)
            ]
        return [('id', '=', False)]

    @api.constrains('computed_input_ids', 'source_type')
    def _check_computed_input_manual_required(self):
        """Ensure any manual item referenced by a computed item is automatically marked as required."""
        for record in self:
            if record.source_type == 'computed':
                manual_inputs = record.computed_input_ids.filtered(
                    lambda i: i.source_type == 'manual' and not i.required
                )
                if manual_inputs:
                    manual_inputs.sudo().write({'required': True})

    @api.constrains('required', 'source_type')
    def _check_manual_item_referenced_required(self):
        """Prevent unchecking required on a manual item referenced by a computed item."""
        for record in self:
            if record.source_type == 'manual' and not record.required:
                referencing_computed = self.search([
                    ('source_type', '=', 'computed'),
                    ('computed_input_ids', 'in', record.id)
                ])
                if referencing_computed:
                    raise ValidationError(
                        f"Manual item '{record.name}' is referenced as an input by computed item(s) "
                        f"({', '.join(referencing_computed.mapped('name'))}) and must be marked as Required."
                    )

    def _selection_source_key(self):
        """ Return available source keys for dropdown selection. """
        resolver = self.env['nhs.eric.source.resolver']
        keys = resolver.available_keys()
        return [(k, resolver.get_key_description(k)) for k in keys]

    @api.depends('source_key', 'source_type')
    def _compute_selection_source_key(self):
        """ Compute the selection source key, only valid for 'auto' type. """
        resolver = self.env['nhs.eric.source.resolver']
        available_keys = resolver.available_keys()
        for record in self:
            if record.source_type == 'auto' and record.source_key in available_keys:
                record.selection_source_key = record.source_key
            else:
                record.selection_source_key = False

    def _inverse_selection_source_key(self):
        """ Inverse method to save selected source key back to source_key field. """
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
        """
        Prevent self-referential and circular dependencies among computed items.
        Uses recursive DFS to detect dependency cycles that would cause infinite
        loops in computed field calculations.
        Raises:
            ValidationError: On self-reference or any circular dependency.
        """
        for record in self:
            if record in record.computed_input_ids:
                raise ValidationError("A computed item cannot have itself as an input.")
            visited = set()

            def check_recursion(node):
                """Check recursion """
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
