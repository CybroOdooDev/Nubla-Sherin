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
from odoo.exceptions import ValidationError, UserError

class NhsEricValue(models.Model):
    _name = 'nhs.eric.value'
    _description = 'ERIC Value (a populated item on a return)'
    _inherit = ['mail.thread']
    _order = 'return_id, section_id, item_def_id'

    return_id = fields.Many2one(
        'nhs.eric.return',
        string='Return',
        required=True,
        ondelete='cascade',
        help='Owning return.'
    )
    item_def_id = fields.Many2one(
        'nhs.eric.item.def',
        string='Item Definition',
        required=True,
        ondelete='restrict',
        help='Which ERIC item this is a value for.'
    )
    site_id = fields.Many2one(
        'nhs.estate.site',
        string='Site',
        ondelete='cascade',
        help='The site this value belongs to, if this is a site-level reporting item.'
    )
    section_id = fields.Many2one(
        'nhs.eric.section',
        string='Section',
        related='item_def_id.section_id',
        store=True,
        help='Convenience from the item def, for grouping/search.'
    )
    item_code = fields.Char(
        string='Item Code',
        related='item_def_id.code',
        help='Convenience from the item def.'
    )
    source_type = fields.Selection(
        related='item_def_id.source_type',
        string='Source Type',
        readonly=True
    )
    data_type = fields.Selection(
        related='item_def_id.data_type',
        string='Data Type',
        readonly=True,
        store=True
    )
    value_number = fields.Float(
        string='Value (Number)',
        digits='Account',
        tracking=True,
        help='Numeric value (integer/float/currency/percent).'
    )
    value_text = fields.Char(
        string='Value (Text)',
        tracking=True,
        help='Text value.'
    )
    value_bool = fields.Boolean(
        string='Value (Boolean)',
        tracking=True,
        help='Boolean value.'
    )
    auto_value = fields.Float(
        string='Auto Value',
        help='The value the resolver derived from source data (kept even when overridden).'
    )
    auto_value_text = fields.Char(
        string='Auto Value (Text)',
        help='The text value derived from source data.'
    )
    auto_value_bool = fields.Boolean(
        string='Auto Value (Boolean)',
        help='The boolean value derived from source data.'
    )
    auto_value_populated = fields.Boolean(
        string='Auto Value Populated',
        default=False,
        help='True when the auto-populate resolver has successfully run and populated this record.'
    )
    is_overridden = fields.Boolean(
        string='Is Overridden',
        default=False,
        tracking=True,
        help='True when a manual value replaces the auto value.'
    )
    override_reason = fields.Char(
        string='Override Reason',
        help='Why the auto value was overridden (audit).'
    )
    source_note = fields.Char(
        string='Source Note',
        compute='_compute_source_note',
        store=True,
        help='Human-readable source (e.g. "Estate Register — total GIA").'
    )
    status = fields.Selection(
        selection=[
            ('populated', 'Populated'),
            ('gap', 'Gap'),
            ('invalid', 'Invalid')
        ],
        string='Status',
        default='gap',
        help='Drives the gap/validation views.'
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        tracking=True,
        help='Section owner responsible for this item (review workflow).'
    )
    signed_off = fields.Boolean(
        string='Signed Off',
        tracking=True,
        help='Reviewer sign-off on this value.'
    )
    signed_off_by_id = fields.Many2one(
        'res.users',
        string='Signed Off By',
        tracking=True,
        help='User who signed off this value.'
    )
    signed_off_at = fields.Datetime(
        string='Signed Off At',
        tracking=True,
        help='When this value was signed off.'
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Supporting Evidence',
        help='Attach supporting evidence/working papers for this item.'
    )
    is_anomaly = fields.Boolean(
        string='Is Anomaly',
        default=False,
        help='Flagged if this value differs wildly from last year.'
    )
    anomaly_reason = fields.Char(
        string='Anomaly Reason',
        help='Details on why this is flagged as an anomaly.'
    )

    @api.constrains('return_id', 'item_def_id', 'site_id')
    def _check_unique_return_item(self):
        """Ensure only one value per item per return (and per site if site-level)."""
        for record in self:
            existing = self.search([
                ('return_id', '=', record.return_id.id),
                ('item_def_id', '=', record.item_def_id.id),
                ('site_id', '=', record.site_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(
                    'A value for this item and site already exists on this return!'
                )

    @api.constrains('is_overridden', 'override_reason')
    def _check_override_reason(self):
        """Enforce that overridden values must have an override reason."""
        for record in self:
            # Only enforce if the item is actually an auto item
            if record.is_overridden and record.item_def_id.source_type == 'auto' and not record.override_reason:
                raise ValidationError(
                    'An override reason must be provided when overriding an auto-populated value.'
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'item_def_id' in vals:
                item_def = self.env['nhs.eric.item.def'].sudo().browse(vals['item_def_id'])
                if item_def:
                    dt = item_def.data_type
                    source_type = item_def.source_type

                    if source_type == 'computed' and not self.env.context.get('bypass_is_overridden_set'):
                        has_value_write = any(f in vals for f in ['value_number', 'value_text', 'value_bool'])
                        if has_value_write:
                            raise UserError("Computed items are read-only and automatically calculated.")

                    # For AUTO items: clear typed fields, only auto_value should be set
                    if source_type == 'auto':
                        vals['value_number'] = False
                        vals['value_text'] = False
                        vals['value_bool'] = False
                        # Set default status to gap until populated
                        if 'status' not in vals:
                            vals['status'] = 'gap'
                    else:
                        # For MANUAL/COMPUTED items: clear only non-matching typed fields
                        has_value_write = any(f in vals for f in ['value_number', 'value_text', 'value_bool'])
                        if has_value_write:
                            if dt in ('integer', 'float', 'currency', 'percent'):
                                vals['value_text'] = False
                                vals['value_bool'] = False
                            elif dt == 'text':
                                vals['value_number'] = False
                                vals['value_bool'] = False
                            elif dt == 'boolean':
                                vals['value_number'] = False
                                vals['value_text'] = False

                        # Check if any value was actually set
                        has_value = False
                        if dt in ('integer', 'float', 'currency', 'percent'):
                            has_value = vals.get('value_number') is not None
                        elif dt == 'text':
                            has_value = bool(vals.get('value_text'))
                        elif dt == 'boolean':
                            has_value = vals.get('value_bool') is not None

                        if 'status' not in vals:
                            vals['status'] = 'populated' if has_value else 'gap'

        records = super(NhsEricValue, self).create(vals_list)
        if not self.env.context.get('bypass_status_update'):
            records.with_context(bypass_status_update=True)._update_status()

        # Trigger dependents recalculation if value changed
        any_val = False
        for vals in vals_list:
            if any(f in vals for f in ['value_number', 'value_text', 'value_bool', 'auto_value', 'auto_value_text', 'auto_value_bool', 'auto_value_populated']):
                any_val = True
                break
        if any_val:
            records._recalculate_dependents()

        return records

    def write(self, vals):
        if not self.env.context.get('bypass_owner_check') and self.env.uid != 1:
            for record in self:
                # Find if there is an owner assigned on the return section
                sec_line = record.return_id.section_line_ids.filtered(lambda s: s.section_id == record.section_id)
                if sec_line and sec_line.owner_id and self.env.user != sec_line.owner_id and not self.env.user.has_group(
                        'odoo_nhs_eric.group_nhs_eric_manager'):
                    raise UserError(
                        f"Only the assigned owner ({sec_line.owner_id.name}) or an Estates Manager can modify values in the section '{record.section_id.name}'.")

        for record in self:
            if record.return_id.state in ('finalised', 'submitted'):
                raise UserError('This return has been finalised/submitted and is locked for editing.')

            source_type = record.item_def_id.source_type
            if source_type == 'computed' and not self.env.context.get('bypass_is_overridden_set'):
                has_value_write = any(f in vals for f in ['value_number', 'value_text', 'value_bool'])
                if has_value_write:
                    raise UserError("Computed items are read-only and automatically calculated.")

        for record in self:
            dt = record.item_def_id.data_type
            source_type = record.item_def_id.source_type
            record_vals = vals.copy()

            # For AUTO items: ONLY update auto_value, not typed fields
            if source_type == 'auto':
                # Check if user is trying to write to typed fields (this would be an override)
                has_value_write = any(f in vals for f in ['value_number', 'value_text', 'value_bool'])

                if has_value_write and not self.env.context.get('bypass_is_overridden_set'):
                    # This is an override - mark it as overridden
                    if 'is_overridden' not in record_vals:
                        record_vals['is_overridden'] = True
                    if not record_vals.get('override_reason') and not record.override_reason:
                        record_vals['override_reason'] = 'Manual override applied'

                    # Only keep the matching typed field, clear others
                    if dt in ('integer', 'float', 'currency', 'percent'):
                        # Keep value_number, clear others
                        if 'value_number' in vals:
                            # Keep the value as is
                            pass
                        record_vals['value_text'] = False
                        record_vals['value_bool'] = False
                    elif dt == 'text':
                        # Keep value_text, clear others
                        if 'value_text' in vals:
                            # Keep the value as is
                            pass
                        record_vals['value_number'] = False
                        record_vals['value_bool'] = False
                    elif dt == 'boolean':
                        # Keep value_bool, clear others
                        if 'value_bool' in vals:
                            # Keep the value as is
                            pass
                        record_vals['value_number'] = False
                        record_vals['value_text'] = False

                # If auto fields are being written, keep them
                if 'auto_value' in vals:
                    pass

            else:
                # For MANUAL/COMPUTED items: clear only non-matching typed fields
                has_value_write = any(f in vals for f in ['value_number', 'value_text', 'value_bool'])
                if has_value_write:
                    if dt in ('integer', 'float', 'currency', 'percent'):
                        if 'value_number' in vals:
                            # Keep the value as is
                            pass
                        record_vals['value_text'] = False
                        record_vals['value_bool'] = False
                    elif dt == 'text':
                        if 'value_text' in vals:
                            # Keep the value as is
                            pass
                        record_vals['value_number'] = False
                        record_vals['value_bool'] = False
                    elif dt == 'boolean':
                        if 'value_bool' in vals:
                            # Keep the value as is
                            pass
                        record_vals['value_number'] = False
                        record_vals['value_text'] = False

            super(NhsEricValue, record).write(record_vals)

        if not self.env.context.get('bypass_status_update'):
            self.with_context(bypass_status_update=True)._update_status()

        # Trigger dependents recalculation if value changed
        value_changed = any(f in vals for f in ['value_number', 'value_text', 'value_bool', 'auto_value', 'auto_value_text', 'auto_value_bool', 'auto_value_populated'])
        if value_changed:
            self._recalculate_dependents()

        return True

    def _update_status(self):
        """Validate and update the status of this value record."""
        # Pre-fetch min/max values from DB
        item_def_ids = self.mapped('item_def_id').ids
        db_min_max = {}
        if item_def_ids:
            self.env.cr.execute(
                "SELECT id, min_value, max_value FROM nhs_eric_item_def WHERE id = ANY(%s)",
                (item_def_ids,)
            )
            db_min_max = {row[0]: (row[1], row[2]) for row in self.env.cr.fetchall()}

        for record in self:
            if not record.item_def_id or record.item_def_id.change_flag == 'removed':
                continue

            # Get the active value based on source type
            source_type = record.item_def_id.source_type
            data_type = record.item_def_id.data_type

            # Determine the value to validate
            val = None
            has_value = record._has_value()

            if has_value:
                if source_type == 'auto':
                    # For AUTO: use auto fields (or typed fields if overridden)
                    if record.is_overridden:
                        if data_type in ('integer', 'float', 'currency', 'percent'):
                            val = record.value_number
                        elif data_type == 'text':
                            val = record.value_text
                        elif data_type == 'boolean':
                            val = record.value_bool
                    else:
                        if data_type in ('integer', 'float', 'currency', 'percent'):
                            val = record.auto_value
                        elif data_type == 'text':
                            val = record.auto_value_text
                        elif data_type == 'boolean':
                            val = record.auto_value_bool
                else:
                    # For MANUAL/COMPUTED: use the typed field
                    if data_type in ('integer', 'float', 'currency', 'percent'):
                        val = record.value_number
                    elif data_type == 'text':
                        val = record.value_text
                    elif data_type == 'boolean':
                        val = record.value_bool

            # Check required fields - if required and no value, mark as gap
            if record.item_def_id.required and not has_value:
                record.status = 'gap'
                continue

            # If the item has no value, mark as gap (regardless of required or not)
            if not has_value:
                record.status = 'gap'
                continue

            # At this point, we have a value. Check validation rules.

            # Check range for numeric types - ONLY if min_value or max_value are explicitly set
            if data_type in ('integer', 'float', 'currency', 'percent'):
                if val is not None:
                    # Check integer type constraint
                    if data_type == 'integer' and val % 1 != 0:
                        record.status = 'invalid'
                        continue
                    db_min, db_max = db_min_max.get(record.item_def_id.id, (None, None))
                    # Clean up database float defaults (False/None/0.0)
                    has_min = db_min is not None and db_min is not False and (db_min != 0.0 or (db_max and db_max > 0.0))
                    has_max = db_max is not None and db_max is not False and db_max != 0.0
                    
                    if has_min:
                        if val < db_min:
                            record.status = 'invalid'
                            continue
                    if has_max:
                        if val > db_max:
                            record.status = 'invalid'
                            continue

            # Check allowed values - ONLY if allowed_values is set
            if record.item_def_id.allowed_values:
                allowed_vals = [v.strip().lower() for v in record.item_def_id.allowed_values.split(',') if v.strip()]
                if allowed_vals:
                    val_str = ''
                    if data_type == 'text':
                        val_str = str(val or '').strip().lower()
                    elif data_type in ('integer', 'float', 'currency', 'percent'):
                        if val is not None:
                            if isinstance(val, (int, float)) and hasattr(val, 'is_integer') and val.is_integer():
                                val_str = str(int(val))
                            else:
                                val_str = str(val)
                            val_str = val_str.lower()
                    elif data_type == 'boolean':
                        val_str = str(val).lower()

                    if val_str not in allowed_vals:
                        record.status = 'invalid'
                        continue

            # Check data type consistency - text fields are special
            if data_type == 'text':
                # For text fields, we already validated has_value above
                # If we got here, there is a value, so it's valid
                # No additional validation needed for text
                pass
            elif data_type == 'boolean' and val is None:
                record.status = 'invalid'
                continue

            # Check cross-field errors
            if record.return_id:
                cross_errors = record.return_id._perform_cross_field_checks()
                if any(err[0] == record or err[0].id == record.id for err in cross_errors):
                    record.status = 'invalid'
                    continue

            # Mark as valid
            record.status = 'populated'

    def unlink(self):
        for record in self:
            if record.return_id.state in ('finalised', 'submitted'):
                raise UserError('This return has been finalised/submitted and is locked for editing.')
        return super(NhsEricValue, self).unlink()

    @api.depends('item_def_id', 'auto_value', 'auto_value_text', 'auto_value_bool', 'auto_value_populated', 'return_id.company_id', 'return_id.dataset_id.year', 'site_id', 'item_def_id.site_id')
    def _compute_source_note(self):
        """Compute human-readable source note with traceability details."""
        resolver = self.env['nhs.eric.source.resolver'].sudo()
        for record in self:
            if record.item_def_id.source_type == 'auto' and record.auto_value_populated:
                site = record.item_def_id.site_id or record.site_id if record.item_def_id.reporting_level == 'site' else None
                record.source_note = resolver.get_traceability_note(
                    record.item_def_id.source_key,
                    record.return_id.company_id,
                    record.return_id.dataset_id.year,
                    site
                )
            else:
                record.source_note = "Manual entry"

    def _set_typed_value(self, value):
        """
        Set the value in the appropriate typed field based on data type.
        """
        self.ensure_one()
        if not self.item_def_id:
            return

        self = self.with_context(bypass_is_overridden_set=True)
        data_type = self.item_def_id.data_type
        source_type = self.item_def_id.source_type

        vals = {}
        if source_type == 'auto':
            if data_type in ('integer', 'float', 'currency', 'percent'):
                try:
                    vals['auto_value'] = float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    vals['auto_value'] = 0.0
            elif data_type == 'text':
                vals['auto_value_text'] = str(value) if value is not None else False
                vals['auto_value'] = 0.0
            elif data_type == 'boolean':
                vals['auto_value_bool'] = bool(value) if value is not None else False
                vals['auto_value'] = 1.0 if vals['auto_value_bool'] else 0.0

        if data_type in ('integer', 'float', 'currency', 'percent'):
            try:
                vals['value_number'] = float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                vals['value_number'] = 0.0
            vals['value_text'] = False
            vals['value_bool'] = False
        elif data_type == 'text':
            vals['value_text'] = str(value) if value is not None else False
            vals['value_number'] = False
            vals['value_bool'] = False
        elif data_type == 'boolean':
            vals['value_bool'] = bool(value) if value is not None else False
            vals['value_number'] = False
            vals['value_text'] = False

        self.write(vals)

    def _get_value_display(self):
        """Get display string for the value based on its data type."""
        self.ensure_one()
        if not self.item_def_id:
            return ''

        data_type = self.item_def_id.data_type
        source_type = self.item_def_id.source_type

        # For AUTO items: show auto fields (or typed fields if overridden)
        if source_type == 'auto':
            if self.is_overridden:
                if data_type in ('integer', 'float', 'currency', 'percent'):
                    return str(self.value_number) if self.value_number is not None else ''
                elif data_type == 'text':
                    return self.value_text or ''
                elif data_type == 'boolean':
                    return 'Yes' if self.value_bool else 'No'
            else:
                if data_type in ('integer', 'float', 'currency', 'percent'):
                    return str(self.auto_value) if self.auto_value is not None else ''
                elif data_type == 'text':
                    return self.auto_value_text or ''
                elif data_type == 'boolean':
                    return 'Yes' if self.auto_value_bool else 'No'

        # For MANUAL/COMPUTED items: show the typed field
        if data_type in ('integer', 'float', 'currency', 'percent'):
            return str(self.value_number) if self.value_number is not None else ''
        elif data_type == 'text':
            return self.value_text or ''
        elif data_type == 'boolean':
            return 'Yes' if self.value_bool else 'No'
        return ''

    def _has_value(self):
        """
        Check if the value has a valid value based on its data type and source type.
        """
        self.ensure_one()
        if not self.item_def_id:
            return False

        data_type = self.item_def_id.data_type
        source_type = self.item_def_id.source_type

        # For AUTO items not overridden, we rely on auto_value_populated
        if source_type == 'auto' and not self.is_overridden:
            return self.auto_value_populated

        # For MANUAL/COMPUTED items or overridden AUTO items: check the typed field in the database
        if self.id and isinstance(self.id, int):
            self.flush_recordset(['value_number', 'value_text', 'value_bool'])
            self.env.cr.execute(
                "SELECT value_number, value_text, value_bool FROM nhs_eric_value WHERE id = %s",
                (self.id,)
            )
            row = self.env.cr.fetchone()
            if row:
                db_num, db_text, db_bool = row
                if data_type in ('integer', 'float', 'currency', 'percent'):
                    return db_num is not None
                elif data_type == 'text':
                    return bool(db_text)
                elif data_type == 'boolean':
                    return db_bool is not None
            return False

        # Fallback for new/unsaved records
        if data_type in ('integer', 'float', 'currency', 'percent'):
            return self.value_number is not None
        elif data_type == 'text':
            return bool(self.value_text)
        elif data_type == 'boolean':
            return self.value_bool is not None
        return False

    def action_override(self):
        """Override the auto value with a manual value."""
        self.ensure_one()
        if self.return_id.state in ('finalised', 'submitted'):
            raise UserError('Cannot override a finalised or submitted return.')

        # Only AUTO items can be overridden
        if self.item_def_id.source_type != 'auto':
            raise UserError('Only auto-populated items can be overridden.')

        self.is_overridden = True
        if not self.override_reason:
            self.override_reason = "Manual override applied"
        return True

    def action_clear_override(self):
        """Clear override and revert to auto value."""
        self.ensure_one()
        if self.return_id.state in ('finalised', 'submitted'):
            raise UserError('Cannot clear override on a finalised or submitted return.')

        # Only AUTO items can have override cleared
        if self.item_def_id.source_type != 'auto':
            raise UserError('Only auto-populated items can have override cleared.')

        self.is_overridden = False
        val_to_restore = None
        if self.auto_value_populated:
            dt = self.item_def_id.data_type
            if dt in ('integer', 'float', 'currency', 'percent'):
                val_to_restore = self.auto_value
            elif dt == 'text':
                val_to_restore = self.auto_value_text
            elif dt == 'boolean':
                val_to_restore = self.auto_value_bool
        self._set_typed_value(val_to_restore)
        self.override_reason = False
        return True

    def action_sign_off(self):
        """Sign off this value."""
        self.ensure_one()
        if self.return_id.state in ('finalised', 'submitted'):
            raise UserError('Cannot sign off a finalised or submitted return.')
        sec_line = self.return_id.section_line_ids.filtered(lambda s: s.section_id == self.section_id)
        if sec_line:
            if not sec_line.reviewer_id:
                raise UserError('Please assign a Section Reviewer on the section status before signing off.')
            if self.env.user != sec_line.reviewer_id:
                raise UserError('Only the assigned Section Reviewer is allowed to sign off.')
        self.write({
            'signed_off': True,
            'signed_off_by_id': self.env.user.id,
            'signed_off_at': fields.Datetime.now()
        })
        return True

    def action_unsign(self):
        """Remove sign-off from this value."""
        self.ensure_one()
        if self.return_id.state in ('finalised', 'submitted'):
            raise UserError('Cannot unsign a finalised or submitted return.')
        self.write({
            'signed_off': False,
            'signed_off_by_id': False,
            'signed_off_at': False
        })
        return True

    def _calculate_computed_value(self, visited=None):
        self.ensure_one()
        input_defs = self.item_def_id.computed_input_ids
        op = self.item_def_id.computation_operator
        if not input_defs or not op:
            return

        def get_value_number_from_record(val_rec):
            if not val_rec:
                return 0.0
            val_rec = val_rec[0]
            dt = val_rec.item_def_id.data_type
            if dt in ('integer', 'float', 'currency', 'percent'):
                val = val_rec.value_number
                if (val is None or val is False) and val_rec.item_def_id.source_type == 'auto':
                    val = val_rec.auto_value
                return val or 0.0
            elif dt == 'boolean':
                return 1.0 if val_rec.value_bool else 0.0
            else:
                try:
                    return float(val_rec.value_text or 0.0)
                except (ValueError, TypeError):
                    return 0.0

        def get_input_value(input_def):
            dep_vals = self.return_id.value_ids.filtered(lambda v: v.item_def_id == input_def)
            if not dep_vals:
                return 0.0
            
            # 1. Computed is site-level, Input is site-level: match the site
            if self.item_def_id.reporting_level == 'site' and input_def.reporting_level == 'site':
                dep_val = dep_vals.filtered(lambda v: v.site_id == self.site_id)
                return get_value_number_from_record(dep_val)
                
            # 2. Input is trust-level: match site_id = False/None
            if input_def.reporting_level == 'organisational':
                dep_val = dep_vals.filtered(lambda v: not v.site_id)
                return get_value_number_from_record(dep_val)
                
            # 3. Computed is trust-level, Input is site-level: sum all sites
            if self.item_def_id.reporting_level == 'organisational' and input_def.reporting_level == 'site':
                return sum(get_value_number_from_record(v) for v in dep_vals if v.site_id)
                
            return 0.0

        # Get float/numeric values of the inputs
        input_vals = [get_input_value(inp) for inp in input_defs]
        
        result = 0.0
        if op == 'sum':
            result = sum(input_vals)
        elif op == 'sub':
            if input_vals:
                result = input_vals[0] - sum(input_vals[1:])
        elif op == 'mul':
            if input_vals:
                import math
                result = math.prod(input_vals)
        elif op == 'div':
            if input_vals:
                result = input_vals[0]
                for val in input_vals[1:]:
                    if val != 0.0:
                        result /= val
                    else:
                        result = 0.0
                        break
        elif op == 'avg':
            if input_vals:
                result = sum(input_vals) / len(input_vals)
        elif op == 'pct':
            if len(input_vals) >= 2:
                num = input_vals[0]
                den = input_vals[1]
                result = (num / den) * 100.0 if den != 0.0 else 0.0
            elif input_vals:
                result = input_vals[0]

        # Write the calculated result to the appropriate field
        dt = self.item_def_id.data_type
        vals = {}
        if dt in ('integer', 'float', 'currency', 'percent'):
            try:
                vals['value_number'] = float(result)
            except (ValueError, TypeError):
                vals['value_number'] = 0.0
        elif dt == 'boolean':
            vals['value_bool'] = bool(result)
        else:
            vals['value_text'] = str(result) if result is not None else False
            
        vals['status'] = 'populated'
        
        self.with_context(bypass_status_update=True, bypass_is_overridden_set=True).write(vals)
        # Re-run _update_status to correctly evaluate ranges and allowed values
        self.with_context(bypass_status_update=True)._update_status()

    def _recalculate_dependents(self, visited=None):
        if visited is None:
            visited = set()
        
        for record in self:
            if record.id in visited:
                continue
            visited.add(record.id)
            
            # Find all computed items on the return
            computed_vals = record.return_id.value_ids.filtered(
                lambda v: v.item_def_id.source_type == 'computed'
            )
            
            for comp_val in computed_vals:
                # Check site scoping: if both are site-level, they must match
                if record.site_id and comp_val.site_id and comp_val.site_id != record.site_id:
                    continue
                
                # Check if record's item is in the computed_input_ids of the computed item definition
                if record.item_def_id in comp_val.item_def_id.computed_input_ids:
                    # Recalculate this computed value
                    comp_val._calculate_computed_value(visited=visited)