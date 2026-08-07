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
import io
import base64
import xlsxwriter

class NhsEricReturn(models.Model):
    _name = 'nhs.eric.return'
    _description = 'An organisation\'s ERIC return for a collection year'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, create_date desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help='Display, e.g. "ERIC 2025/26 — Example NHS Trust".'
    )
    dataset_id = fields.Many2one(
        'nhs.eric.dataset',
        string='Data Set',
        required=True,
        ondelete='restrict',
        domain=[('state', '=', 'active')],
        help='The data-set version this return follows.'
    )
    year = fields.Char(
        string='Year',
        related='dataset_id.year',
        store=True,
        help='From the data set.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Organisation',
        required=True,
        default=lambda self: self.env.company,
        help='Submitting organisation; record rules scope on it.'
    )
    ods_code = fields.Char(
        string='ODS Code',
        help='Provider ODS code (soft; from Trust suite if present, else entered).'
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('validated', 'Validated'),
            ('finalised', 'Finalised'),
            ('submitted', 'Submitted')
        ],
        string='Status',
        required=True,
        default='draft',
        tracking=True,
        help='Return lifecycle status: draft → in_progress → validated → finalised → submitted.'
    )
    section_line_ids = fields.One2many(
         'nhs.eric.return.section',
         'return_id',
         string='Section Line Statuses',
         copy=False,
         help='Status and assignments for each section in this return.'
     )
    value_ids = fields.One2many(
         'nhs.eric.value',
         'return_id',
         string='Values',
         copy=False,
         help='The populated item values for this return.'
     )
    values_count = fields.Integer(
        string='Values Count',
        compute='_compute_stats',
        store=True,
        help='Total count of the values assciated with this return.'
    )
    completeness_pct = fields.Float(
        string='Completeness %',
        compute='_compute_stats',
        store=True,
        help='% of required items populated.'
    )
    validation_error_count = fields.Integer(
        string='Validation Errors',
        compute='_compute_stats',
        store=True,
        help='Failing validations.'
    )
    gap_count = fields.Integer(
        string='Gap Count',
        compute='_compute_stats',
        store=True,
        help='Required items with no value.'
    )
    gap_invalid_count = fields.Integer(
        string='Gap & Invalid Count',
        compute='_compute_stats',
        store=True,
        help='Required items with no value or failing validations.'
    )
    last_populated = fields.Datetime(
        string='Last Populated',
        help='When auto-population last ran.'
    )
    finalised_by_id = fields.Many2one(
        'res.users',
        string='Finalised By',
        help='Finalisation stamp; locks the return.'
    )
    finalised_at = fields.Datetime(
        string='Finalised At',
        help='Finalisation stamp; locks the return.'
    )
    prior_return_id = fields.Many2one(
        'nhs.eric.return',
        string='Prior Return',
        help='Last year\'s return, for comparison and manual carry-forward.'
    )
    comparison_line_ids = fields.One2many(
        'nhs.eric.return.comparison.line',
        'return_id',
        string='Year-on-Year Comparison Lines',
        compute='_compute_comparison_lines'
    )
    notes = fields.Text(
        string='Notes',
        help='Free-text notes for the return.'
    )

    @api.constrains('company_id', 'dataset_id')
    def _check_unique_company_year(self):
        """Ensure only one return per organisation per year."""
        for record in self:
            existing = self.search([
                ('company_id', '=', record.company_id.id),
                ('dataset_id', '=', record.dataset_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(
                    'A return for this organisation and year already exists!'
                )

    @api.depends('dataset_id', 'company_id')
    def _compute_name(self):
        """Compute display name from dataset and company."""
        for record in self:
            year = record.dataset_id.year or ''
            company = record.company_id.name or ''
            record.name = f"ERIC {year} — {company}"

    @api.model_create_multi
    def create(self, vals_list):
        returns = super(NhsEricReturn, self).create(vals_list)
        for record in returns:
            # Ensure all items are initialized as value records
            record._ensure_value_records()
            
            # Find and set prior return if not already set
            if not record.prior_return_id and record.dataset_id.prior_dataset_id:
                prior = self.search([
                    ('company_id', '=', record.company_id.id),
                    ('dataset_id', '=', record.dataset_id.prior_dataset_id.id)
                ], limit=1)
                if prior:
                    record.prior_return_id = prior.id
        return returns

    @api.onchange('dataset_id')
    def _onchange_dataset_id(self):
        if self.dataset_id:
            self.value_ids = [(5, 0, 0)]
            self.section_line_ids = [(5, 0, 0)]
            
            sections = self.dataset_id.section_ids
            section_vals = []
            for sec in sections:
                section_vals.append((0, 0, {
                    'section_id': sec.id,
                    'state': 'draft',
                }))
            self.section_line_ids = section_vals
            
            items = self.dataset_id.section_ids.mapped('item_def_ids').filtered(lambda i: i.change_flag != 'removed')
            sites = self.env['nhs.estate.site'].search([('company_id', '=', self.company_id.id)])
            
            value_vals = []
            for item in items:
                if item.reporting_level == 'organisational':
                    value_vals.append((0, 0, {
                        'item_def_id': item.id,
                        'site_id': False,
                        'status': 'gap',
                    }))
                elif item.reporting_level == 'site':
                    if item.site_id:
                        value_vals.append((0, 0, {
                            'item_def_id': item.id,
                            'site_id': item.site_id.id,
                            'status': 'gap',
                        }))
                    else:
                        for site in sites:
                            value_vals.append((0, 0, {
                                'item_def_id': item.id,
                                'site_id': site.id,
                                'status': 'gap',
                            }))
            self.value_ids = value_vals

    def write(self, vals):
        for record in self:
            if record.state in ('finalised', 'submitted'):
                allowed_fields = {'state', 'finalised_by_id', 'finalised_at', 'notes'}
                modified_fields = {f for f in vals.keys() if not (f.startswith('message_') or f.startswith('activity_') or f in allowed_fields)}
                if modified_fields:
                    raise UserError('This return has been finalised/submitted and is locked for editing.')
            if 'dataset_id' in vals and vals['dataset_id'] != record.dataset_id.id:
                record.value_ids.unlink()
                record.section_line_ids.unlink()
        res = super(NhsEricReturn, self).write(vals)
        if 'dataset_id' in vals:
            for record in self:
                record._ensure_value_records()
                if not record.prior_return_id and record.dataset_id.prior_dataset_id:
                    prior = self.search([
                        ('company_id', '=', record.company_id.id),
                        ('dataset_id', '=', record.dataset_id.prior_dataset_id.id)
                    ], limit=1)
                    if prior:
                        record.prior_return_id = prior.id
                params = self.env['ir.config_parameter'].sudo()
                auto_populate = params.get_param('odoo_nhs_eric.eric_auto_populate_on_create') == 'True'
                carry_forward = params.get_param('odoo_nhs_eric.eric_carry_forward_manual') == 'True'
                if carry_forward and record.prior_return_id:
                    record.action_carry_forward()
                if auto_populate:
                    record.action_populate()
        return res

    def unlink(self):
        for record in self:
            if record.state in ('finalised', 'submitted'):
                raise UserError('Cannot delete a finalised or submitted return!')
        return super(NhsEricReturn, self).unlink()

    def _ensure_value_records(self):
        """Ensure that every active (non-removed) item in the dataset has a value record on this return."""
        self.sudo()._ensure_section_lines()
        for record in self:
            items = record.dataset_id.section_ids.mapped('item_def_ids').filtered(lambda i: i.change_flag != 'removed')
            sites = self.env['nhs.estate.site'].sudo().search([('company_id', '=', record.company_id.id)])
            
            # Clean up redundant value records
            redundant_values = self.env['nhs.eric.value']
            for val in record.sudo().value_ids:
                item = val.item_def_id
                if item not in items:
                    redundant_values |= val
                    continue
                if item.reporting_level == 'organisational':
                    if val.site_id:
                        redundant_values |= val
                elif item.reporting_level == 'site':
                    if item.site_id:
                        if val.site_id != item.site_id:
                            redundant_values |= val
                    else:
                        if val.site_id not in sites:
                            redundant_values |= val
            if redundant_values:
                redundant_values.with_context(bypass_owner_check=True).unlink()

            existing = set()
            for val in record.sudo().value_ids:
                existing.add((val.item_def_id.id, val.site_id.id or False))
                
            to_create = []
            for item in items:
                if item.reporting_level == 'organisational':
                    if (item.id, False) not in existing:
                        to_create.append({
                            'return_id': record.id,
                            'item_def_id': item.id,
                            'site_id': False,
                            'status': 'gap',
                        })
                elif item.reporting_level == 'site':
                    if item.site_id:
                        if (item.id, item.site_id.id) not in existing:
                            to_create.append({
                                'return_id': record.id,
                                'item_def_id': item.id,
                                'site_id': item.site_id.id,
                                'status': 'gap',
                            })
                    else:
                        for site in sites:
                            if (item.id, site.id) not in existing:
                                to_create.append({
                                    'return_id': record.id,
                                    'item_def_id': item.id,
                                    'site_id': site.id,
                                    'status': 'gap',
                                })
            if to_create:
                self.env['nhs.eric.value'].sudo().create(to_create)

    def _ensure_section_lines(self):
        """Ensure that every section in the dataset has a return section record on this return."""
        for record in self:
            sections = record.dataset_id.section_ids
            existing_sections = record.sudo().section_line_ids.mapped('section_id')
            missing_sections = sections - existing_sections
            
            vals = []
            for sec in missing_sections:
                vals.append({
                    'return_id': record.id,
                    'section_id': sec.id,
                    'state': 'draft',
                })
            if vals:
                self.env['nhs.eric.return.section'].sudo().create(vals)

    def action_view_all_values(self):
        """Return an action displaying all values associated with this return.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Values',
            'res_model': 'nhs.eric.value',
            'view_mode': 'list,form',
            'domain': [('return_id', 'in', self.id)],
        }

    def action_view_gap_invalid_values(self):
        """Return an action displaying all gap and invalid values associated with this return.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gap and Invalid Values',
            'res_model': 'nhs.eric.value',
            'view_mode': 'list,form',
            'domain': [('return_id', 'in', self.id),('status', 'in', ['gap', 'invalid'])],
        }

    def action_bulk_manual_entry(self):
        """Return action for bulk manual entry of values."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Manual Entry',
            'res_model': 'nhs.eric.value',
            'view_mode': 'list,form',
            'domain': [('return_id', '=', self.id)],
            'context': {
                'default_return_id': self.id,
                'search_default_manual_only': 1,
            }
        }

    @api.depends('value_ids', 'value_ids.status')
    def _compute_stats(self):
        """Compute completeness, gap count, and validation error count."""
        for record in self:
            total = len(record.value_ids)
            if not total:
                record.completeness_pct = 0.0
                record.gap_count = 0
                record.validation_error_count = 0
                record.gap_invalid_count = 0
                record.values_count = 0
                continue

            filled = record.value_ids.filtered(
                lambda v: v.status != 'gap' and v.status != 'invalid'
            )
            gaps = record.value_ids.filtered(lambda v: v.status == 'gap')
            invalid = record.value_ids.filtered(lambda v: v.status == 'invalid')

            record.completeness_pct = (len(filled) / total) * 100 if total > 0 else 0.0
            record.gap_count = len(gaps)
            record.validation_error_count = len(invalid)
            record.gap_invalid_count = len(invalid) + len(gaps)
            record.values_count = total

    def action_populate(self):
        """Run source resolver to auto-populate values from estate/compliance."""
        self.ensure_one()

        if self.state in ('finalised', 'submitted'):
            raise UserError('Cannot populate a finalised or submitted return!')

        self.sudo()._ensure_value_records()

        resolver = self.env['nhs.eric.source.resolver'].sudo()
        items = self.dataset_id.section_ids.mapped('item_def_ids').filtered(lambda i: i.change_flag != 'removed')
        auto_items = items.filtered(lambda i: i.source_type == 'auto')

        for item_def in auto_items:
            if not item_def.source_key:
                continue

            existing = self.sudo().value_ids.filtered(
                lambda v: v.item_def_id.id == item_def.id
            )

            for rec in existing:
                try:
                    site = item_def.site_id or rec.site_id if item_def.reporting_level == 'site' else None
                    value = resolver.resolve(
                        item_def.source_key,
                        self.company_id,
                        self.dataset_id.year,
                        site=site
                    )
                except Exception:
                    value = None

                vals_to_write = {
                    'auto_value_populated': value is not None,
                    'source_note': f"Auto from {item_def.source_key}",
                    'status': 'populated' if value is not None else 'gap'
                }
                dt = item_def.data_type
                if dt in ('integer', 'float', 'currency', 'percent'):
                    try:
                        vals_to_write['auto_value'] = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        vals_to_write['auto_value'] = 0.0
                elif dt == 'text':
                    vals_to_write['auto_value_text'] = str(value) if value is not None else False
                    vals_to_write['auto_value'] = 0.0
                elif dt == 'boolean':
                    vals_to_write['auto_value_bool'] = bool(value) if value is not None else False
                    vals_to_write['auto_value'] = 1.0 if vals_to_write['auto_value_bool'] else 0.0

                rec.sudo().with_context(bypass_owner_check=True, bypass_status_update=True).write(vals_to_write)
                if not rec.is_overridden:
                    rec.sudo().with_context(bypass_owner_check=True, bypass_status_update=True)._set_typed_value(value)

        # Refresh computed items
        computed_items = items.filtered(lambda i: i.source_type == 'computed')
        for item_def in computed_items:
            self.with_context(bypass_status_update=True)._compute_item_value(item_def)

        # Batch update status of all value records
        self.value_ids.with_context(bypass_status_update=True)._update_status()

        self.last_populated = fields.Datetime.now()
        if self.state == 'draft':
            self.state = 'in_progress'

        return True

    def _compute_item_value(self, item_def):
        """Compute a value based on formula."""
        existing = self.value_ids.filtered(
            lambda v: v.item_def_id.id == item_def.id
        )
        for rec in existing:
            rec._calculate_computed_value()

    def _perform_cross_field_checks(self):
        """Perform cross-field verification (e.g. occupied area <= GIA; parts summing to totals)."""
        self.ensure_one()
        errors = []

        # Group values by site to check rules at the appropriate scope
        values_by_site = {}
        for val in self.value_ids:
            if val.item_def_id.change_flag == 'removed':
                continue
            values_by_site.setdefault(val.site_id.id, {})[val.item_def_id.code] = val

        for site_id, codes in values_by_site.items():
            # 1. Rule: Occupied area not exceeding GIA
            occupied_keys = [k for k in codes if 'OCCUPIED' in k]
            gia_keys = [k for k in codes if 'GIA' in k]
            for occ_k in occupied_keys:
                for gia_k in gia_keys:
                    if occ_k and gia_k and occ_k[0] == gia_k[0]:
                        occ_val = codes[occ_k].value_number
                        gia_val = codes[gia_k].value_number
                        if occ_val is not None and gia_val is not None and occ_val > gia_val:
                            errors.append((codes[occ_k], f"Occupied area ({occ_val}) cannot exceed GIA ({gia_val})."))

            # 2. Rule: Parts summing to totals (e.g. tenure owned + leased/other == total land/GIA)
            owned_k = next((k for k in codes if 'TENURE_OWN' in k or 'TEN_OWN' in k), None)
            leased_k = next((k for k in codes if 'TENURE_LEASE' in k or 'TEN_LEASE' in k), None)
            total_k = next((k for k in codes if k in ('S_LAND', 'E_LAND_AREA', 'E_LAND', 'S_GIA', 'E_GIA')), None)
            if owned_k and leased_k and total_k:
                own_val = codes[owned_k].value_number or 0.0
                lease_val = codes[leased_k].value_number or 0.0
                tot_val = codes[total_k].value_number
                if tot_val is not None and abs((own_val + lease_val) - tot_val) > 1.0:
                    errors.append((codes[owned_k], f"Tenure Owned ({own_val}) and Leased ({lease_val}) must sum to total ({tot_val})."))
                    errors.append((codes[leased_k], f"Tenure Owned ({own_val}) and Leased ({lease_val}) must sum to total ({tot_val})."))
                    errors.append((codes[total_k], f"Total ({tot_val}) does not match sum of Tenure Owned and Leased ({own_val + lease_val})."))

            # 3. Rule: Risk-category backlog components sum to total backlog
            high_k = next((k for k in codes if 'BACKLOG_HIGH' in k or 'BACK_HIGH' in k), None)
            sig_k = next((k for k in codes if 'BACKLOG_SIGNIFICANT' in k or 'BACK_SIGN' in k), None)
            mod_k = next((k for k in codes if 'BACKLOG_MODERATE' in k or 'BACK_MOD' in k), None)
            low_k = next((k for k in codes if 'BACKLOG_LOW' in k or 'BACK_LOW' in k), None)
            tot_backlog_k = next((k for k in codes if k in ('E_BACKLOG_TOT', 'E_BACKLOG_TOTAL', 'BACKLOG_TOTAL', 'S_BACKLOG_TOT')), None)
            
            if tot_backlog_k:
                comp_sum = 0.0
                has_any_comp = False
                for k in (high_k, sig_k, mod_k, low_k):
                    if k:
                        comp_sum += codes[k].value_number or 0.0
                        has_any_comp = True
                
                tot_val = codes[tot_backlog_k].value_number or 0.0
                if has_any_comp and abs(comp_sum - tot_val) > 1.0:
                    errors.append((codes[tot_backlog_key] if 'tot_backlog_key' in locals() else codes[tot_backlog_k], f"Total Backlog ({tot_val}) does not match the sum of risk components ({comp_sum})."))
                    for k in (high_k, sig_k, mod_k, low_k):
                        if k:
                            errors.append((codes[k], f"Risk component values must sum to Total Backlog ({tot_val})."))

        return errors

    def _detect_anomalies(self):
        """Compare numeric values against the prior year return and flag anomalies."""
        self.ensure_one()
        # Reset anomalies first
        self.value_ids.write({'is_anomaly': False, 'anomaly_reason': False})
        
        if not self.prior_return_id:
            return

        params = self.env['ir.config_parameter'].sudo()
        threshold_val = params.get_param('odoo_nhs_eric.anomaly_threshold_pct', '50.0')
        try:
            threshold = float(threshold_val)
        except ValueError:
            threshold = 50.0

        for val in self.value_ids:
            if val.item_def_id.change_flag == 'removed':
                continue
            if val.item_def_id.data_type not in ('integer', 'float', 'currency', 'percent'):
                continue
            if not val._has_value():
                continue

            # Find matching value in prior return by item code and site
            prior_val = self.prior_return_id.value_ids.filtered(
                lambda v: v.item_def_id.code == val.item_def_id.code and v.site_id.id == val.site_id.id
            )
            if prior_val and prior_val[0]._has_value():
                current_num = val.value_number or 0.0
                prior_num = prior_val[0].value_number or 0.0
                if prior_num != 0.0:
                    diff_pct = abs(((current_num - prior_num) / prior_num) * 100.0)
                    if diff_pct >= threshold:
                        val.write({
                            'is_anomaly': True,
                            'anomaly_reason': f"Value differs by {diff_pct:.1f}% from prior year (Prior: {prior_num}, Current: {current_num})"
                        })

    def action_validate(self):
        """Validate the return against all defined rules."""
        self.ensure_one()

        if self.state in ('finalised', 'submitted'):
            raise UserError('Cannot validate a finalised or submitted return!')

        # Reset all anomaly flags and perform detection
        self._detect_anomalies()

        # Fetch all item definitions in a single database query to know their real nullable min/max values
        item_defs = self.value_ids.mapped('item_def_id')
        db_min_max = {}
        if item_defs:
            item_defs.flush_recordset(['min_value', 'max_value'])
            self.env.cr.execute(
                "SELECT id, min_value, max_value FROM nhs_eric_item_def WHERE id = ANY(%s)",
                (item_defs.ids,)
            )
            db_min_max = {row[0]: (row[1], row[2]) for row in self.env.cr.fetchall()}

        errors = []
        for value in self.value_ids:
            # Ignore removed items
            if value.item_def_id.change_flag == 'removed':
                continue

            # Check required fields & general gaps
            if not value._has_value():
                value.status = 'gap'
                if value.item_def_id.required:
                    errors.append(f"Item '{value.item_def_id.name}' ({value.item_code or value.item_def_id.code}) is missing a value (gap).")
                continue

            # Get active value based on source type and data type
            source_type = value.item_def_id.source_type
            dt = value.item_def_id.data_type
            val = None

            if value.is_overridden or source_type != 'auto':
                if dt in ('integer', 'float', 'currency', 'percent'):
                    val = value.value_number
                elif dt == 'text':
                    val = value.value_text
                elif dt == 'boolean':
                    val = value.value_bool
            else:
                if dt in ('integer', 'float', 'currency', 'percent'):
                    val = value.auto_value
                elif dt == 'text':
                    val = value.auto_value_text
                elif dt == 'boolean':
                    val = value.auto_value_bool

            # Check range for numeric types
            if dt in ('integer', 'float', 'currency', 'percent'):
                if val is None:
                    value.status = 'invalid'
                    errors.append(f"Item '{value.item_def_id.name}' has invalid numeric value.")
                    continue

                if dt == 'integer' and val % 1 != 0:
                    value.status = 'invalid'
                    errors.append(f"Item '{value.item_def_id.name}' ({value.item_code or value.item_def_id.code}) must be an integer, but got {val}.")
                    continue

                db_min, db_max = db_min_max.get(value.item_def_id.id, (None, None))
                # Clean up database float defaults (False/None/0.0)
                has_min = db_min is not None and db_min is not False and (db_min != 0.0 or (db_max and db_max > 0.0))
                has_max = db_max is not None and db_max is not False and db_max != 0.0

                if has_min:
                    if val < db_min:
                        value.status = 'invalid'
                        errors.append(f"Item '{value.item_def_id.name}' value {val} is less than minimum {db_min}.")
                        continue
                if has_max:
                    if val > db_max:
                        value.status = 'invalid'
                        errors.append(f"Item '{value.item_def_id.name}' value {val} is greater than maximum {db_max}.")
                        continue
            elif dt == 'text':
                if value.item_def_id.required and not val:
                    value.status = 'invalid'
                    errors.append(f"Item '{value.item_def_id.name}' is required but has no text value.")
                    continue
            elif dt == 'boolean':
                if val is None:
                    value.status = 'invalid'
                    errors.append(f"Item '{value.item_def_id.name}' has invalid boolean value.")
                    continue
            elif dt == 'currency':
                if val is None or val < 0 :
                    value.status = 'invalid'
                    errors.append(f"Item '{value.item_def_id.name}' has invalid currency value.")
                    continue
            elif dt == 'percent':
                if val is None or not (0 < val < 100):
                    value.status = 'invalid'
                    errors.append(f"Item '{value.item_def_id.name}' has invalid percent value.")
                    continue


            # Check allowed values
            if value.item_def_id.allowed_values:
                allowed_vals = [v.strip().lower() for v in value.item_def_id.allowed_values.split(',') if v.strip()]
                if allowed_vals:
                    val_str = ''
                    if dt == 'text':
                        val_str = str(val or '').strip().lower()
                    elif dt in ('integer', 'float', 'currency', 'percent'):
                        if val is not None:
                            if val % 1 == 0:
                                val_str = str(int(val))
                            else:
                                val_str = str(val)
                            val_str = val_str.lower()
                    elif dt == 'boolean':
                        val_str = str(bool(val)).lower()

                    if val_str not in allowed_vals:
                        value.status = 'invalid'
                        errors.append(f"Item '{value.item_def_id.name}' value '{val_str}' is not in allowed values: {value.item_def_id.allowed_values}.")
                        continue

            value.status = 'populated'

        # Run cross-field checks
        cross_errors = self._perform_cross_field_checks()
        for value_record, err_msg in cross_errors:
            value_record.status = 'invalid'
            errors.append(f"Cross-field failure for '{value_record.item_def_id.name}': {err_msg}")

        # Check section sign-offs
        if not self.env.context.get('bypass_sign_off_check'):
            unsigned_sections = self.section_line_ids.filtered(lambda s: s.state != 'signed_off')
            if unsigned_sections:
                errors.append(f"The following sections are not signed off: {', '.join(unsigned_sections.mapped('section_id.name'))}")

        policy = self.env['ir.config_parameter'].sudo().get_param('odoo_nhs_eric.eric_validation_policy', 'block')
        if errors:
            if policy == 'block':
                limit = 10
                msg = "\n".join(errors[:limit])
                if len(errors) > limit:
                    msg += f"\n... and {len(errors) - limit} more errors."
                raise UserError(f"Validation failed!\n{msg}")
            else:
                self.message_post(body=f"Validation completed with {len(errors)} warnings/gaps (Policy: Warn Only).")

        self.state = 'validated'
        return True

    def action_finalise(self):
        """Finalise and lock the return for submission."""
        self.ensure_one()

        if not self.env.user.has_group('odoo_nhs_eric.group_nhs_eric_manager'):
            raise UserError('Only an Estates Lead / Manager can finalise the return.')

        if self.state == 'finalised':
            raise UserError('This return is already finalised!')

        policy = self.env['ir.config_parameter'].sudo().get_param('odoo_nhs_eric.eric_validation_policy', 'block')

        if self.state != 'validated':
            try:
                self.action_validate()
            except UserError as e:
                if policy == 'block':
                    raise UserError('Please fix all validation errors before finalising.')

        # Enforce that all sections are signed off before overall finalisation
        if not self.env.context.get('bypass_sign_off_check'):
            unsigned_sections = self.section_line_ids.filtered(lambda s: s.state != 'signed_off')
            if unsigned_sections:
                raise UserError(
                    'Cannot finalise: not all sections are signed off. Unsigned sections: %s'
                    % ', '.join(unsigned_sections.mapped('section_id.name'))
                )

        # Explicitly check for invalid or gap items
        if policy == 'block':
            invalid_or_required_gaps = self.value_ids.filtered(
                lambda v: (v.status == 'invalid' or (v.item_def_id.required and v.status == 'gap')) and v.item_def_id.change_flag != 'removed'
            )
            if invalid_or_required_gaps:
                raise UserError('Cannot finalise: there are validation errors or missing required values in this return.')

        self.write({
            'state': 'finalised',
            'finalised_by_id': self.env.user.id,
            'finalised_at': fields.Datetime.now()
        })

        self.env['nhs.eric.trend.metric'].refresh_trends(self.company_id.id)

        return True

    def _get_value_typed(self, value):
        """Helper to get a type-safe value suitable for spreadsheet cell writing."""
        if not value or not value._has_value():
            return ""
        dt = value.item_def_id.data_type
        if dt in ('integer', 'float', 'currency', 'percent'):
            val = value.value_number
            if val is None:
                return ""
            if dt == 'integer':
                return int(val)
            return float(val)
        elif dt == 'boolean':
            return "Yes" if value.value_bool else "No"
        else:
            return value.value_text or ""

    def generate_finalized_excel(self):
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_name': 'Segoe UI',
            'font_color': '#ffffff',
            'bg_color': '#005EB8',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#003A70'
        })
        
        meta_label_format = workbook.add_format({
            'bold': True,
            'font_name': 'Segoe UI',
            'font_size': 10,
            'bg_color': '#F0F4F8',
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#D0D9E0'
        })
        
        meta_value_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#D0D9E0'
        })
        
        section_header_format = workbook.add_format({
            'bold': True,
            'font_name': 'Segoe UI',
            'font_size': 12,
            'font_color': '#005EB8',
            'bg_color': '#E1EDF7',
            'align': 'left',
            'valign': 'vcenter',
            'bottom': 2,
            'bottom_color': '#005EB8'
        })
        
        table_header_format = workbook.add_format({
            'bold': True,
            'font_name': 'Segoe UI',
            'font_size': 10,
            'font_color': '#ffffff',
            'bg_color': '#005EB8',
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#003A70'
        })
        
        table_cell_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#E2E8F0'
        })
        
        table_cell_num_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#E2E8F0',
            'num_format': '#,##0.00'
        })

        table_cell_int_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#E2E8F0',
            'num_format': '#,##0'
        })

        worksheet = workbook.add_worksheet('Finalised ERIC Return')
        worksheet.set_column('A:A', 15) # Item Code
        worksheet.set_column('B:B', 35) # Item Name
        worksheet.set_column('C:C', 15) # Data Type
        worksheet.set_column('D:D', 20) # Value
        worksheet.set_column('E:E', 12) # Unit
        worksheet.set_column('F:F', 15) # Reporting Level
        worksheet.set_column('G:G', 25) # Site Code/Name
        
        worksheet.set_row(0, 40)
        worksheet.merge_range('A1:G1', self.name, title_format)
        
        metadata = [
            ('Dataset Name', self.dataset_id.name or ''),
            ('Financial Year', self.year or ''),
            ('Organisation', self.company_id.name or ''),
            ('Finalised Date', self.finalised_at.strftime('%Y-%m-%d %H:%M:%S') if self.finalised_at else ''),
            ('Finalised By', self.finalised_by_id.name or '')
        ]
        
        r = 3
        for label, val in metadata:
            worksheet.set_row(r, 20)
            worksheet.merge_range(r, 0, r, 1, label, meta_label_format)
            worksheet.merge_range(r, 2, r, 6, val, meta_value_format)
            r += 1
            
        r += 1 # Empty row

        sections = self.dataset_id.section_ids.sorted('sequence')
        for section in sections:
            worksheet.set_row(r, 24)
            worksheet.merge_range(r, 0, r, 6, f"Section: {section.name} [{section.code}]", section_header_format)
            r += 1
            
            worksheet.set_row(r, 20)
            headers = ['Item Code', 'Item Name', 'Data Type', 'Value', 'Unit', 'Reporting Level', 'Site Code/Name']
            for col, header in enumerate(headers):
                worksheet.write(r, col, header, table_header_format)
            r += 1
            
            values = self.value_ids.filtered(lambda v: v.section_id == section and v.item_def_id.change_flag != 'removed').sorted(
                lambda v: (v.item_def_id.reporting_level, v.site_id.name or '', v.item_def_id.sequence)
            )
            
            for val in values:
                worksheet.set_row(r, 18)
                worksheet.write(r, 0, val.item_def_id.code or '', table_cell_format)
                worksheet.write(r, 1, val.item_def_id.name or '', table_cell_format)
                worksheet.write(r, 2, (val.item_def_id.data_type or '').title(), table_cell_format)
                
                dt = val.item_def_id.data_type
                v_typed = self._get_value_typed(val)
                if dt in ('integer', 'float', 'currency', 'percent') and v_typed != '':
                    if dt == 'integer':
                        worksheet.write_number(r, 3, v_typed, table_cell_int_format)
                    else:
                        worksheet.write_number(r, 3, v_typed, table_cell_num_format)
                else:
                    worksheet.write(r, 3, v_typed, table_cell_format)
                    
                worksheet.write(r, 4, val.item_def_id.unit or '', table_cell_format)
                worksheet.write(r, 5, (val.item_def_id.reporting_level or '').title(), table_cell_format)
                worksheet.write(r, 6, f"[{val.site_id.code}] {val.site_id.name}" if val.site_id else '' , table_cell_format)
                r += 1
                
            r += 2

        workbook.close()
        output.seek(0)
        
        filename = f"ERIC_Export_{self.name.replace(' ', '_')}_{fields.Date.today()}.xlsx"
        return output.getvalue(), filename

    def action_export_finalized_excel(self):
        self.ensure_one()
        if self.state not in ('finalised', 'submitted'):
            raise UserError('Only finalised or submitted returns can be exported to finalized Excel.')
            
        data, filename = self.generate_finalized_excel()
        
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(data),
            'res_model': 'nhs.eric.return',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=true",
            'target': 'self',
        }

    def action_submit(self):
        """Mark the return as submitted to NHS England."""
        self.ensure_one()

        if self.state != 'finalised':
            raise UserError('Return must be finalised before marking as submitted!')

        self.state = 'submitted'
        return True

    def action_open_report(self):
        """Open the ERIC Return PDF report."""
        self.ensure_one()
        return self.env.ref('odoo_nhs_eric.report_nhs_eric_return_pdf').report_action(self, config=False)

    def action_open_gap_report_pdf(self):
        """Open the ERIC Gap Report PDF."""
        self.ensure_one()
        return self.env.ref('odoo_nhs_eric.report_nhs_eric_gap_pdf').report_action(self, config=False)


    def action_carry_forward(self):
        """Carry forward manual items from prior year's return."""
        self.ensure_one()

        if not self.prior_return_id:
            raise UserError('No prior return set for carry forward!')

        if self.state in ('finalised', 'submitted'):
            raise UserError('Cannot carry forward to a finalised or submitted return!')

        prior_values = self.prior_return_id.value_ids.filtered(
            lambda v: v.item_def_id.source_type == 'manual' and v.item_def_id.change_flag != 'removed'
        )

        copied_count = 0
        for prior_val in prior_values:
            existing = self.value_ids.filtered(
                lambda v: v.item_def_id.code == prior_val.item_def_id.code and v.site_id.id == prior_val.site_id.id
            )

            # Copy attachments if any
            attachment_copies = []
            if prior_val.attachment_ids:
                for att in prior_val.attachment_ids:
                    # Create new attachment record copying the old one
                    copy_att = self.env['ir.attachment'].create({
                        'name': att.name,
                        'type': att.type,
                        'datas': att.datas,
                        'mimetype': att.mimetype,
                        'res_model': 'nhs.eric.value',
                    })
                    attachment_copies.append(copy_att.id)

            if not existing:
                # Find matching item def in current dataset
                current_item_def = self.dataset_id.section_ids.mapped('item_def_ids').filtered(lambda i: i.code == prior_val.item_def_id.code)
                if current_item_def:
                    new_val = self.env['nhs.eric.value'].with_context(bypass_owner_check=True).create({
                        'return_id': self.id,
                        'item_def_id': current_item_def[0].id,
                        'site_id': prior_val.site_id.id,
                        'value_number': prior_val.value_number,
                        'value_text': prior_val.value_text,
                        'value_bool': prior_val.value_bool,
                        'status': 'populated' if prior_val._has_value() else 'gap',
                        'attachment_ids': [(6, 0, attachment_copies)] if attachment_copies else False
                    })
                    # Link attachment to the new record specifically
                    if attachment_copies:
                        self.env['ir.attachment'].browse(attachment_copies).write({'res_id': new_val.id})
                    copied_count += 1
            else:
                existing.with_context(bypass_owner_check=True).write({
                    'value_number': prior_val.value_number,
                    'value_text': prior_val.value_text,
                    'value_bool': prior_val.value_bool,
                    'status': 'populated' if prior_val._has_value() else 'gap',
                    'attachment_ids': [(4, att_id) for att_id in attachment_copies]
                })
                if attachment_copies:
                    self.env['ir.attachment'].browse(attachment_copies).write({'res_id': existing.id})
                copied_count += 1

        self.message_post(body=f"Carried forward {copied_count} manual values from prior year return '{self.prior_return_id.name}'.")
        return True

    def action_view_prior_comparison(self):
        """Generate year-on-year comparison data."""
        self.ensure_one()

        if not self.prior_return_id:
            raise UserError('No prior return set for comparison!')

        comparison_data = []
        for value in self.value_ids:
            prior_value = self.prior_return_id.value_ids.filtered(
                lambda v: v.item_def_id.id == value.item_def_id.id and v.site_id.id == value.site_id.id
            )

            if prior_value:
                prior = prior_value[0]
            else:
                prior = None

            comparison_data.append({
                'item': value.item_def_id.name,
                'code': value.item_def_id.code,
                'current': value._get_value_display(),
                'prior': prior._get_value_display() if prior else 'N/A',
                'change': self._calculate_change(value, prior)
            })

        return comparison_data

    def _calculate_change(self, current, prior):
        """Calculate percentage change between current and prior values."""
        if not prior or not current._has_value():
            return 0.0

        current_val = current.value_number or 0
        prior_val = prior.value_number or 0

        if prior_val == 0:
            return 0.0

        return ((current_val - prior_val) / prior_val) * 100

    @api.depends('value_ids', 'value_ids.value_number', 'value_ids.value_text', 'value_ids.value_bool', 'prior_return_id', 'prior_return_id.value_ids', 'prior_return_id.value_ids.value_number')
    def _compute_comparison_lines(self):
        for record in self:
            if not record.prior_return_id:
                record.comparison_line_ids = [(5, 0, 0)]
                continue

            # Load prior values into a dict for quick matching
            prior_vals = {}
            for val in record.prior_return_id.value_ids:
                if val.item_def_id.change_flag == 'removed':
                    continue
                key = (val.item_def_id.code, val.site_id.id)
                prior_vals[key] = val

            # Get anomaly threshold
            threshold_param = self.env['ir.config_parameter'].sudo().get_param('odoo_nhs_eric.anomaly_threshold_pct', '50.0')
            try:
                threshold = float(threshold_param)
            except ValueError:
                threshold = 50.0

            lines_vals = []
            for val in record.value_ids:
                if val.item_def_id.change_flag == 'removed':
                    continue

                key = (val.item_def_id.code, val.site_id.id)
                prior_val = prior_vals.get(key)

                # Calculate change
                change_pct = 0.0
                cur_num = val.value_number or 0.0
                pri_num = prior_val.value_number or 0.0 if prior_val else 0.0

                if prior_val and prior_val._has_value() and val._has_value():
                    if pri_num != 0.0:
                        change_pct = ((cur_num - pri_num) / abs(pri_num)) * 100.0
                    elif cur_num != 0.0:
                        change_pct = 100.0

                # Highlight state
                alert = 'normal'
                if abs(change_pct) >= threshold and abs(change_pct) > 0:
                    alert = 'orange'
                elif change_pct > 0:
                    alert = 'green'
                elif change_pct < 0:
                    alert = 'red'

                flag = 'flat'
                if change_pct > 0:
                    flag = 'up'
                elif change_pct < 0:
                    flag = 'down'

                lines_vals.append((0, 0, {
                    'item_def_id': val.item_def_id.id,
                    'site_id': val.site_id.id,
                    'current_value_display': val._get_value_display(),
                    'prior_value_display': prior_val._get_value_display() if prior_val else 'N/A',
                    'current_value_num': cur_num,
                    'prior_value_num': pri_num,
                    'percentage_change': change_pct,
                    'highlight_color': alert,
                    'change_flag': flag,
                }))

            record.comparison_line_ids = [(5, 0, 0)] + lines_vals

    def _get_key_metric_value(self, metric_type):
        """Helper to find the value of a key metric by code or source key."""
        self.ensure_one()
        mapping = {
            'gia': {
                'codes': ['E_GIA', 'GIA'],
                'source_keys': ['estate.total_gia', 'estate.occupied_floor_area']
            },
            'backlog_total': {
                'codes': ['E_BACKLOG_TOT', 'E_BACKLOG_TOTAL', 'BACKLOG_TOTAL'],
                'source_keys': ['estate.backlog.total']
            },
            'backlog_high': {
                'codes': ['E_BACKLOG_HIGH', 'BACKLOG_HIGH'],
                'source_keys': ['estate.backlog.high']
            },
            'backlog_significant': {
                'codes': ['E_BACKLOG_SIGNIFICANT', 'BACKLOG_SIGNIFICANT'],
                'source_keys': ['estate.backlog.significant']
            },
            'backlog_moderate': {
                'codes': ['E_BACKLOG_MODERATE', 'BACKLOG_MODERATE'],
                'source_keys': ['estate.backlog.moderate']
            },
            'backlog_low': {
                'codes': ['E_BACKLOG_LOW', 'BACKLOG_LOW'],
                'source_keys': ['estate.backlog.low']
            },
            'compliance_pct': {
                'codes': ['C_PCT', 'C_COMPLIANCE', 'COMPLIANCE_PCT'],
                'source_keys': ['compliance.pct', 'compliance.compliance_pct']
            }
        }
        
        rules = mapping.get(metric_type, {})
        matching_vals = self.value_ids.filtered(
            lambda v: v.item_def_id.code in rules.get('codes', []) or v.item_def_id.source_key in rules.get('source_keys', [])
        )
        if not matching_vals:
            return 0.0

        def get_val_num(v):
            if v.item_def_id.source_type == 'auto' and not v.is_overridden:
                return v.auto_value or 0.0
            return v.value_number or 0.0

        # Prefer trust-level records (those without site_id) if they exist
        trust_vals = matching_vals.filtered(lambda v: not v.site_id)
        if trust_vals:
            if metric_type == 'compliance_pct':
                return get_val_num(trust_vals[0])
            return sum(get_val_num(v) for v in trust_vals)

        # Otherwise, aggregate site-level records
        if metric_type == 'compliance_pct':
            valid_vals = [get_val_num(v) for v in matching_vals]
            return sum(valid_vals) / len(valid_vals) if valid_vals else 0.0
        else:
            return sum(get_val_num(v) for v in matching_vals)

    @api.model
    def get_dashboard_metrics(self, return_id=None):
        """Fetch metrics, trends, source coverage, and section status for NHS ERIC Returns."""
        # Find all available returns to allow user switching
        all_returns = self.search([])
        return_list = [{'id': r.id, 'name': r.name or r.year, 'year': r.year} for r in all_returns]
        
        # Determine target return
        ret = None
        if return_id:
            ret = self.browse(return_id)
        if not ret or not ret.exists():
            ret = all_returns[:1]
            
        metrics = {
            'has_data': False,
            'returns': return_list,
            'selected_return_id': ret.id if ret else False,
        }
        
        if not ret:
            return metrics
            
        metrics['has_data'] = True
        metrics['name'] = ret.name
        metrics['year'] = ret.year
        metrics['state'] = ret.state
        metrics['completeness_pct'] = ret.completeness_pct
        metrics['gap_count'] = ret.gap_count
        metrics['validation_error_count'] = ret.validation_error_count
        
        # Section status summary
        sections_outstanding = 0
        section_lines = []
        for line in ret.section_line_ids:
            if line.state != 'signed_off':
                sections_outstanding += 1
            
            # Compute section completeness
            vals = ret.value_ids.filtered(lambda v: v.section_id == line.section_id)
            req_vals = vals.filtered(lambda v: v.item_def_id.required)
            req_count = len(req_vals)
            populated_req = len(req_vals.filtered(lambda v: v.status == 'populated'))
            comp_pct = (populated_req / req_count * 100.0) if req_count > 0 else 100.0
            
            section_lines.append({
                'id': line.id,
                'name': line.section_id.name,
                'owner': line.owner_id.name or 'Unassigned',
                'reviewer': line.reviewer_id.name or 'Unassigned',
                'state': line.state,
                'completeness_pct': comp_pct,
            })
            
        metrics['sections_outstanding'] = sections_outstanding
        metrics['section_lines'] = section_lines
        
        # Headline metrics for the selected return
        gia = ret._get_key_metric_value('gia')
        backlog = ret._get_key_metric_value('backlog_total')
        compliance = ret._get_key_metric_value('compliance_pct')
        
        metrics['headline'] = {
            'gia': gia,
            'backlog': backlog,
            'compliance': compliance,
            'cost_per_m2': (backlog / gia) if gia > 0 else 0.0,
        }
        
        # Data-source coverage
        total_vals = len(ret.value_ids)
        auto_count = len(ret.value_ids.filtered(lambda v: v.item_def_id.source_type == 'auto'))
        manual_count = len(ret.value_ids.filtered(lambda v: v.item_def_id.source_type == 'manual'))
        computed_count = len(ret.value_ids.filtered(lambda v: v.item_def_id.source_type == 'computed'))
        
        metrics['coverage'] = {
            'total': total_vals,
            'auto': auto_count,
            'manual': manual_count,
            'computed': computed_count,
            'auto_pct': (auto_count / total_vals * 100.0) if total_vals > 0 else 0.0,
        }
        
        # Year-on-year trends
        # Retrieve trends for this company
        trends = self.env['nhs.eric.trend.metric'].search([('company_id', '=', ret.company_id.id)], order='year asc')
        trend_data = []
        for t in trends:
            trend_data.append({
                'year': t.year,
                'gia': t.gia,
                'backlog': t.backlog,
                'compliance_pct': t.compliance_pct,
                'cost_per_m2': t.cost_per_m2,
            })
            
        # Ensure the selected return's current values are included in trend_data 
        # so the dashboard always has the current return's data for comparison!
        # If the selected return is not already in trend_data (e.g. because it's not finalised), add it.
        if ret and not any(d['year'] == ret.year for d in trend_data):
            r_gia = ret._get_key_metric_value('gia')
            r_backlog = ret._get_key_metric_value('backlog_total')
            r_compliance = ret._get_key_metric_value('compliance_pct')
            trend_data.append({
                'year': ret.year,
                'gia': r_gia,
                'backlog': r_backlog,
                'compliance_pct': r_compliance,
                'cost_per_m2': (r_backlog / r_gia) if r_gia > 0 else 0.0,
            })
            # Re-sort trend_data by year
            trend_data = sorted(trend_data, key=lambda x: x['year'])
            
        # Fallback trend data on-the-fly if empty or only 1 year
        if len(trend_data) < 2:
            trend_data = []
            fallback_returns = self.search([('company_id', '=', ret.company_id.id)], order='year asc')
            for r in fallback_returns:
                r_gia = r._get_key_metric_value('gia')
                r_backlog = r._get_key_metric_value('backlog_total')
                r_compliance = r._get_key_metric_value('compliance_pct')
                trend_data.append({
                    'year': r.year,
                    'gia': r_gia,
                    'backlog': r_backlog,
                    'compliance_pct': r_compliance,
                    'cost_per_m2': (r_backlog / r_gia) if r_gia > 0 else 0.0,
                })
        metrics['trends'] = trend_data
        
        return metrics


class NhsEricReturnComparisonLine(models.Model):
    _name = 'nhs.eric.return.comparison.line'
    _description = 'ERIC Return Comparison Line'
    _order = 'item_code asc'

    return_id = fields.Many2one('nhs.eric.return', string='Return', ondelete='cascade', required=True)
    item_def_id = fields.Many2one('nhs.eric.item.def', string='Item', required=True)
    item_code = fields.Char(related='item_def_id.code', string='Code', store=True)
    site_id = fields.Many2one('nhs.estate.site', string='Site')
    current_value_display = fields.Char(string='Current Value')
    prior_value_display = fields.Char(string='Prior Value')
    current_value_num = fields.Float(string='Current Num')
    prior_value_num = fields.Float(string='Prior Num')
    percentage_change = fields.Float(string='Change (%)')
    highlight_color = fields.Selection([
        ('green', 'Increase'),
        ('red', 'Decrease'),
        ('orange', 'Significant Change'),
        ('normal', 'Normal')
    ], string='Alert Level', default='normal')
    change_flag = fields.Selection([
        ('up', '↗ Up'),
        ('down', '↘ Down'),
        ('flat', '→ No Change')
    ], string='Trend', default='flat')


class NhsEricTrendMetric(models.Model):
    _name = 'nhs.eric.trend.metric'
    _description = 'ERIC Trend Metrics'
    _order = 'year asc'

    year = fields.Char(string='Year', required=True)
    company_id = fields.Many2one('res.company', string='Organisation', required=True)
    gia = fields.Float(string='Total GIA (m²)')
    backlog = fields.Float(string='Total Backlog Cost (£)')
    backlog_high = fields.Float(string='High Risk Backlog (£)')
    backlog_significant = fields.Float(string='Significant Risk Backlog (£)')
    backlog_moderate = fields.Float(string='Moderate Risk Backlog (£)')
    backlog_low = fields.Float(string='Low Risk Backlog (£)')
    compliance_pct = fields.Float(string='Overall Compliance (%)')
    cost_per_m2 = fields.Float(string='Cost per m² (£/m²)')

    @api.model
    def refresh_trends(self, company_id=None):
        """Regenerate trend records from all returns."""
        domain = []
        if company_id:
            domain.append(('company_id', '=', company_id))
            
        returns = self.env['nhs.eric.return'].search(domain)
        
        # Sort returns: submitted > finalised > validated > in_progress > draft
        state_weight = {
            'submitted': 5,
            'finalised': 4,
            'validated': 3,
            'in_progress': 2,
            'draft': 1
        }
        returns = sorted(returns, key=lambda r: state_weight.get(r.state, 0), reverse=True)
        
        processed = set()
        
        for ret in returns:
            key = (ret.company_id.id, ret.year)
            if key in processed:
                continue
            processed.add(key)
            
            trend = self.search([
                ('company_id', '=', ret.company_id.id),
                ('year', '=', ret.year)
            ])
            
            gia = ret._get_key_metric_value('gia')
            backlog = ret._get_key_metric_value('backlog_total')
            backlog_high = ret._get_key_metric_value('backlog_high')
            backlog_significant = ret._get_key_metric_value('backlog_significant')
            backlog_moderate = ret._get_key_metric_value('backlog_moderate')
            backlog_low = ret._get_key_metric_value('backlog_low')
            compliance_pct = ret._get_key_metric_value('compliance_pct')
            cost_per_m2 = backlog / gia if gia > 0 else 0.0
            
            vals = {
                'gia': gia,
                'backlog': backlog,
                'backlog_high': backlog_high,
                'backlog_significant': backlog_significant,
                'backlog_moderate': backlog_moderate,
                'backlog_low': backlog_low,
                'compliance_pct': compliance_pct,
                'cost_per_m2': cost_per_m2,
            }
            
            if trend:
                trend.write(vals)
            else:
                vals.update({
                    'company_id': ret.company_id.id,
                    'year': ret.year,
                })
                self.create(vals)

        # Clean up any trend records that no longer have corresponding returns
        existing_keys = {(r.company_id.id, r.year) for r in returns}
        trend_domain = [('company_id', '=', company_id)] if company_id else []
        all_trends = self.search(trend_domain)
        for t in all_trends:
            if (t.company_id.id, t.year) not in existing_keys:
                t.unlink()

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        if not self.env.context.get('bypass_refresh_trends'):
            self.with_context(bypass_refresh_trends=True).refresh_trends()
        return super().search(args, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not self.env.context.get('bypass_refresh_trends'):
            self.with_context(bypass_refresh_trends=True).refresh_trends()
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)