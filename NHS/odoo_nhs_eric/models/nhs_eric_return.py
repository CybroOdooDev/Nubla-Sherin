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
    """
        Model for NHS ERIC Returns. This models an organisation's complete
        Estates Returns Information Collection (ERIC) return submission for
        a specific financial year. Each return captures all estate data items
        defined in the ERIC dataset, tracks validation status, and manages
        the submission workflow from draft through to final submission.
    """
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
        help='Financial year from the data set.'
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
        help='Total count of the values associated with this return.'
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
        compute='_compute_comparison_lines',
        store=True,
        help="Comparison lines for this return.",
    )
    notes = fields.Text(
        string='Notes',
        help='Free-text notes for the return.'
    )

    @api.constrains('company_id', 'dataset_id')
    def _check_unique_company_year(self):
        """Ensure only one return per organization per year."""
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
        """
            Override create to sanitize value records and ensure proper initialization.
            - Removes invalid value entries without item_def_id
            - Creates value records for all items in the dataset
            - Sets prior_return_id if available
        """
        for vals in vals_list:
            if 'value_ids' in vals and isinstance(vals['value_ids'], list):
                sanitized = []
                for cmd in vals['value_ids']:
                    if isinstance(cmd, (tuple, list)) and len(cmd) == 3 and cmd[0] == 0:
                        if isinstance(cmd[2], dict) and not cmd[2].get('item_def_id'):
                            continue
                    sanitized.append(cmd)
                vals['value_ids'] = sanitized
        returns = super(NhsEricReturn, self).create(vals_list)
        params = self.env['ir.config_parameter'].sudo()
        auto_populate = params.get_param('odoo_nhs_eric.eric_auto_populate_on_create') == 'True'
        carry_forward = params.get_param('odoo_nhs_eric.eric_carry_forward_manual') == 'True'
        for record in returns:
            record._ensure_value_records()
            if not record.prior_return_id and record.dataset_id.prior_dataset_id:
                prior = self.search([
                    ('company_id', '=', record.company_id.id),
                    ('dataset_id', '=', record.dataset_id.prior_dataset_id.id)
                ], limit=1)
                if prior:
                    record.prior_return_id = prior.id
            if auto_populate:
                record.action_populate()
            if carry_forward and record.prior_return_id:
                record.action_carry_forward()
        return returns

    @api.onchange('dataset_id')
    def _onchange_dataset_id(self):
        """
        When dataset changes, rebuild value and section records.
        Creates section lines for all dataset sections and value records
        for all active items at organisational and site levels.
        """
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
            items = self.dataset_id.section_ids.mapped('item_def_ids').filtered(
                lambda i: i.change_flag != 'removed'
            )
            sites = self.env['nhs.estate.site'].sudo().search([
                ('company_id', '=', self.company_id.id)
            ])
            value_vals = []
            for item in items:
                if item.reporting_level in ('organisational'):
                    value_vals.append((0, 0, {
                        'item_def_id': item.id,
                        'site_id': False,
                        'status': 'gap',
                    }))
                elif item.reporting_level == 'site':
                    for site in sites:
                        value_vals.append((0, 0, {
                            'item_def_id': item.id,
                            'site_id': site.id,
                            'status': 'gap',
                        }))
            self.value_ids = value_vals

    def write(self, vals):
        """
        Override write to enforce locking for finalised/submitted returns.
        Prevents editing of locked returns except for allowed fields.
        Rebuilds values and carries forward data when dataset changes.
        Raises:
            UserError: If attempting to modify a locked return.
        """
        for record in self:
            if record.state in ('finalised', 'submitted'):
                allowed_fields = {'state', 'finalised_by_id', 'finalised_at', 'notes'}
                modified_fields = {f for f in vals.keys() if
                                   not (f.startswith('message_') or f.startswith('activity_') or f in allowed_fields)}
                if modified_fields:
                    raise UserError('This return has been finalised/submitted and is locked for editing.')
            if 'dataset_id' in vals and vals['dataset_id'] != record.dataset_id.id:
                record.value_ids.unlink()
                record.section_line_ids.unlink()
        res = super(NhsEricReturn, self).write(vals)
        if 'dataset_id' in vals:
            params = self.env['ir.config_parameter'].sudo()
            auto_populate = params.get_param('odoo_nhs_eric.eric_auto_populate_on_create') == 'True'
            carry_forward = params.get_param('odoo_nhs_eric.eric_carry_forward_manual') == 'True'
            for record in self:
                record._ensure_value_records()
                if not record.prior_return_id and record.dataset_id.prior_dataset_id:
                    prior = self.search([
                        ('company_id', '=', record.company_id.id),
                        ('dataset_id', '=', record.dataset_id.prior_dataset_id.id)
                    ], limit=1)
                    if prior:
                        record.prior_return_id = prior.id
                if auto_populate:
                    record.action_populate()
                if carry_forward and record.prior_return_id:
                    record.action_carry_forward()
        return res

    def unlink(self):
        """
        Prevent deletion of finalised or submitted returns.
        Raises:
            UserError: If attempting to delete a locked return.
        """
        for record in self:
            if record.state in ('finalised', 'submitted'):
                raise UserError('Cannot delete a finalised or submitted return!')
        return super(NhsEricReturn, self).unlink()

    def _ensure_value_records(self):
        """Ensure that every active (non-removed) item in the dataset has a value record on this return."""
        self.sudo()._ensure_section_lines()
        for record in self:
            items = record.dataset_id.section_ids.mapped('item_def_ids').filtered(
                lambda i: i.change_flag != 'removed'
            )
            sites = self.env['nhs.estate.site'].sudo().search([
                ('company_id', '=', record.company_id.id)
            ])
            redundant_values = self.env['nhs.eric.value']
            for val in record.sudo().value_ids:
                item = val.item_def_id
                if not item or item not in items:
                    redundant_values |= val
                    continue
                if item.reporting_level == 'organisational':
                    if val.site_id:
                        redundant_values |= val
                elif item.reporting_level == 'site':
                    if val.site_id not in sites:
                        redundant_values |= val
            if redundant_values:
                redundant_values.with_context(bypass_owner_check=True).unlink()
            existing = set()
            for val in record.sudo().value_ids:
                if val.item_def_id and val.item_def_id in items:
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
            'context': {'search_default_group_section': 1},
        }

    def action_view_gap_values(self):
        """Return an action displaying all gap values associated with this return.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gap Values',
            'res_model': 'nhs.eric.value',
            'view_mode': 'list,form',
            'domain': [('return_id', 'in', self.id), ('status', '=', 'gap'), ('source_type', '=', 'manual')],
            'context': {'search_default_group_section': 1},
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
            'domain': [('return_id', 'in', self.id), ('status', 'in', ['gap', 'invalid'])],
            'context': {'search_default_group_section': 1},
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
        items = self.dataset_id.section_ids.mapped('item_def_ids').filtered(lambda i:
                                                                            i.change_flag != 'removed')
        auto_items = items.filtered(lambda i: i.source_type == 'auto')
        for item_def in auto_items:
            if not item_def.source_key:
                continue
            existing = self.sudo().value_ids.filtered(
                lambda v: v.item_def_id.id == item_def.id
            )
            for rec in existing:
                try:
                    site = rec.site_id if item_def.reporting_level == 'site' else None
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
                rec.sudo().with_context(bypass_owner_check=True, bypass_status_update=True,
                                        bypass_recalculate_dependents=True).write(vals_to_write)
                if not rec.is_overridden:
                    rec.sudo().with_context(bypass_owner_check=True, bypass_status_update=True,
                                            bypass_recalculate_dependents=True)._set_typed_value(value)
        for comp_val in self.value_ids.filtered(lambda v: v.item_def_id.source_type == 'computed'):
            comp_val._calculate_computed_value()
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
        values_by_site = {}
        for val in self.value_ids:
            if val.item_def_id.change_flag == 'removed':
                continue
            s_key = val.item_def_id.source_key
            if not s_key and val.item_def_id.source_type == 'computed':
                inputs = val.item_def_id.computed_input_ids.mapped('source_key')
                if set(inputs) == {'estate.backlog.high', 'estate.backlog.significant', 'estate.backlog.moderate',
                                   'estate.backlog.low'}:
                    s_key = 'estate.backlog.total'
            if s_key:
                values_by_site.setdefault(val.site_id.id, {})[s_key] = val
        for site_id, keys in values_by_site.items():
            occupied_keys = [k for k in keys if k == 'estate.occupied_floor_area' or 'occupied' in k]
            total_gia_keys = [k for k in keys if k == 'estate.total_gia' or (
                    'total_gia' in k and not any(x in k for x in ('occupied', 'unallocated', 'vacant')))]
            for occ_k in occupied_keys:
                for gia_k in total_gia_keys:
                    occ_rec = keys[occ_k]
                    gia_rec = keys[gia_k]
                    if (occ_rec._has_value() and occ_rec.status != 'gap' and gia_rec._has_value() and
                            gia_rec.status != 'gap'):
                        occ_val = occ_rec._get_numeric_value()
                        gia_val = gia_rec._get_numeric_value()
                        if occ_val is not None and gia_val is not None and occ_val > gia_val:
                            errors.append((occ_rec, f"Occupied area ({occ_val}) cannot exceed GIA ({gia_val})."))

            owned_k = next((k for k in keys if k == 'estate.tenure.owned' or 'tenure.owned' in k or 'tenure_own' in k),
                           None)
            leased_k = next((k for k in keys if k == 'estate.tenure.leased' or 'tenure.leased' in k or
                             'tenure_lease' in k), None)
            if owned_k and leased_k:
                own_rec = keys[owned_k]
                lease_rec = keys[leased_k]
                if (own_rec._has_value() and own_rec.status != 'gap' and lease_rec._has_value() and
                        lease_rec.status != 'gap'):
                    own_val = own_rec._get_numeric_value()
                    lease_val = lease_rec._get_numeric_value()
                    is_tenure_pct = (own_rec.item_def_id.data_type == 'percent' or
                                     lease_rec.item_def_id.data_type == 'percent' or 'tenure' in (
                            own_rec.item_def_id.source_key or '') or (own_rec.item_def_id.source_key or '') in (
                            'estate.tenure.owned', 'estate.tenure.leased'))
                    if is_tenure_pct:
                        gia_rec = keys.get('estate.total_gia')
                        gia_val = gia_rec._get_numeric_value() if gia_rec and gia_rec._has_value() else 0.0
                        if own_val == 0.0 and lease_val == 0.0 and gia_val == 0.0:
                            pass
                        elif abs((own_val + lease_val) - 100.0) > 1.0:
                            errors.append(
                                (own_rec, f"Tenure Owned ({own_val}%) and Leased ({lease_val}%) must sum to 100%."))
                            errors.append(
                                (lease_rec, f"Tenure Owned ({own_val}%) and Leased ({lease_val}%) must sum to 100%."))
                    else:
                        total_k = next((k for k in keys if k in ('estate.land_area', 'estate.total_gia')),
                                       None)
                        if total_k and total_k in keys:
                            tot_rec = keys[total_k]
                            if tot_rec._has_value() and tot_rec.status != 'gap':
                                tot_val = tot_rec._get_numeric_value()
                                if abs((own_val + lease_val) - tot_val) > 1.0:
                                    errors.append((own_rec,
                                                   f"Tenure Owned ({own_val}) and Leased ({lease_val}) must sum to "
                                                   f"total ({tot_val})."))
                                    errors.append((lease_rec,
                                                   f"Tenure Owned ({own_val}) and Leased ({lease_val}) must sum to "
                                                   f"total ({tot_val})."))
                                    errors.append((tot_rec,
                                                   f"Total ({tot_val}) does not match sum of Tenure Owned and Leased "
                                                   f"({own_val + lease_val})."))

            high_k = next((k for k in keys if k == 'estate.backlog.high' or 'backlog.high' in k), None)
            sig_k = next((k for k in keys if k == 'estate.backlog.significant' or 'backlog.significant' in k), None)
            mod_k = next((k for k in keys if k == 'estate.backlog.moderate' or 'backlog.moderate' in k), None)
            low_k = next((k for k in keys if k == 'estate.backlog.low' or 'backlog.low' in k), None)
            tot_backlog_k = next(
                (k for k in keys if k == 'estate.backlog.total' or 'backlog.total' in k), None)
            if tot_backlog_k:
                tot_back_rec = keys[tot_backlog_k]
                comp_keys = [k for k in (high_k, sig_k, mod_k, low_k) if k and k in keys]
                if tot_back_rec._has_value() and tot_back_rec.status != 'gap' and comp_keys and all(
                        keys[k]._has_value() and keys[k].status != 'gap' for k in comp_keys):
                    comp_sum = sum(keys[k]._get_numeric_value() for k in comp_keys)
                    tot_val = tot_back_rec._get_numeric_value()
                    if abs(comp_sum - tot_val) > 1.0:
                        errors.append((tot_back_rec,
                                f"Total Backlog ({tot_val}) does not match the sum of risk components ({comp_sum})."))
                        for k in comp_keys:
                            errors.append((keys[k], f"Risk component values must sum to Total Backlog ({tot_val})."))
        return errors

    def _detect_anomalies(self):
        """Compare numeric values against the prior year return and flag anomalies."""
        self.ensure_one()
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
                            'anomaly_reason': f"Value differs by {diff_pct:.1f}% from prior year (Prior: {prior_num},"
                                              f" Current: {current_num})"
                        })

    def action_validate(self):
        """Validate the return against all defined rules."""
        self.ensure_one()
        if self.state in ('finalised', 'submitted'):
            raise UserError('Cannot validate a finalised or submitted return!')
        computed_items = self.dataset_id.section_ids.mapped('item_def_ids').filtered(
            lambda i: i.source_type == 'computed' and i.change_flag != 'removed'
        )
        for item_def in computed_items:
            self._compute_item_value(item_def)
        self._detect_anomalies()
        policy = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_eric.eric_validation_policy', 'block'
        )
        errors = []
        error_items = []
        for value in self.value_ids:
            if value.item_def_id.change_flag == 'removed':
                continue
            if not value._has_value() or value.status == 'gap':
                value.status = 'gap'
                if value.item_def_id.required:
                    error_msg=(f"Required item '{value.item_def_id.name}' ({value.item_code or value.item_def_id.code})"
                                 f" is missing a value (gap).")
                    errors.append(error_msg)
                    error_items.append(value)
                    value.write({'status': 'invalid'})
                continue
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
            is_valid = True
            validation_error = None
            if dt in ('integer', 'float', 'currency', 'percent'):
                if val is None:
                    validation_error = f"Item '{value.item_def_id.name}' has invalid numeric value."
                    is_valid = False
                elif dt == 'integer' and val % 1 != 0:
                    validation_error = f"Item '{value.item_def_id.name}' ({value.item_code or value.item_def_id.code}) must be an integer, but got {val}."
                    is_valid = False
                elif dt == 'currency' and val < 0:
                    validation_error = f"Item '{value.item_def_id.name}' has negative currency value."
                    is_valid = False
                elif dt == 'percent' and not (0 <= val <= 100):
                    validation_error = f"Item '{value.item_def_id.name}' has invalid percent value ({val})."
                    is_valid = False
                else:
                    db_min, db_max = self._get_item_min_max(value.item_def_id.id)
                    has_min = db_min is not None and db_min > 0
                    has_max = db_max is not None and db_max > 0
                    if has_min and val < db_min:
                        validation_error = f"Item '{value.item_def_id.name}' value {val} is less than minimum {db_min}."
                        is_valid = False
                    elif has_max and val > db_max:
                        validation_error = f"Item '{value.item_def_id.name}' value {val} is greater than maximum {db_max}."
                        is_valid = False
            elif dt == 'text':
                if value.item_def_id.required and not val:
                    validation_error = f"Item '{value.item_def_id.name}' is required but has no text value."
                    is_valid = False
            elif dt == 'boolean':
                if val is None:
                    validation_error = f"Item '{value.item_def_id.name}' has invalid boolean value."
                    is_valid = False
            if is_valid and value.item_def_id.allowed_values:
                allowed_vals = [v.strip().lower() for v in value.item_def_id.allowed_values.split(',') if v.strip()]
                if allowed_vals:
                    if dt == 'text':
                        val_str = str(val or '').strip().lower()
                        if val_str not in allowed_vals:
                            validation_error = f"Item '{value.item_def_id.name}' value '{val_str}' is not in allowed values: {value.item_def_id.allowed_values}."
                            is_valid = False
                    elif dt in ('integer', 'float', 'currency', 'percent'):
                        if val is not None:
                            val_str = str(int(val)) if isinstance(val, (int, float)) and val.is_integer() else str(val)
                            val_str = val_str.lower()
                            if val_str not in allowed_vals:
                                validation_error = f"Item '{value.item_def_id.name}' value '{val_str}' is not in allowed values: {value.item_def_id.allowed_values}."
                                is_valid = False
                    elif dt == 'boolean':
                        b_val = bool(val)
                        matches_yes = b_val and any(x in allowed_vals for x in ('yes', 'true', '1', 'y', 't'))
                        matches_no = (not b_val) and any(x in allowed_vals for x in ('no', 'false', '0', 'n', 'f'))
                        if not (matches_yes or matches_no):
                            validation_error = f"Item '{value.item_def_id.name}' boolean value '{val}' does not match allowed values: {value.item_def_id.allowed_values}."
                            is_valid = False
            if is_valid:
                value.status = 'populated'
            else:
                value.status = 'invalid'
                if validation_error:
                    errors.append(validation_error)
                    error_items.append(value)
        cross_errors = self._perform_cross_field_checks()
        for value_record, err_msg in cross_errors:
            value_record.status = 'invalid'
            if value_record not in error_items:
                error_items.append(value_record)
            errors.append(f"Cross-field failure for '{value_record.item_def_id.name}': {err_msg}")
        if not self.env.context.get('bypass_sign_off_check'):
            unsigned_sections = self.section_line_ids.filtered(lambda s: s.state != 'signed_off')
            if unsigned_sections:
                errors.append(
                    f"The following sections are not signed off: {', '.join(unsigned_sections.mapped('section_id.name'))}")
        if errors:
            if policy == 'block':
                invalid_items = self.value_ids.filtered(lambda v: v.status == 'invalid')
                required_gaps = self.value_ids.filtered(
                    lambda v: v.item_def_id.required and v.status == 'gap'
                )
                unsigned_sections = self.section_line_ids.filtered(lambda s: s.state != 'signed_off')
                if invalid_items or required_gaps or unsigned_sections :
                    limit = 10
                    msg = "\n".join(errors[:limit])
                    if len(errors) > limit:
                        msg += f"\n... and {len(errors) - limit} more errors."
                    raise UserError(f"Validation failed!\n{msg}")
                else:
                    self.state = 'validated'
                    self.message_post(body=f"Validation completed with {len(errors)} warnings.")
            else:
                self.state = 'validated'
                self.message_post(body=f"Validation completed with {len(errors)} warnings/gaps (Policy: Warn Only).")
        else:
            self.state = 'validated'
        return True

    def _get_item_min_max(self, item_def_id):
        """Helper to get min/max values for an item definition."""
        self.env.cr.execute(
            "SELECT min_value, max_value FROM nhs_eric_item_def WHERE id = %s",
            (item_def_id,)
        )
        result = self.env.cr.fetchone()
        return result if result else (None, None)

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
        if not self.env.context.get('bypass_sign_off_check'):
            unsigned_sections = self.section_line_ids.filtered(lambda s: s.state != 'signed_off')
            if unsigned_sections:
                raise UserError(
                    'Cannot finalise: not all sections are signed off. Unsigned sections: %s'
                    % ', '.join(unsigned_sections.mapped('section_id.name'))
                )
        if policy == 'block':
            invalid_or_required_gaps = self.value_ids.filtered(
                lambda v: (v.status == 'invalid' or (
                        v.item_def_id.required and v.status == 'gap')) and v.item_def_id.change_flag != 'removed'
            )
            if invalid_or_required_gaps:
                raise UserError(
                    'Cannot finalise: there are validation errors or missing required values in this return.')
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
        """
        Generate a formatted Excel export of the finalised return.
        Creates a professional Excel workbook with:
        - Title and metadata section
        - All sections with their items and values
        - Proper formatting and styling
        Returns:
            tuple: (bytes_data, filename)
        """
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_name': 'Segoe UI',
            'font_color': '#ffffff',
            'bg_color': '#005EB8',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#003A70',
            'text_wrap': True,
            'indent': 0,
        })
        meta_label_format = workbook.add_format({
            'bold': True,
            'font_name': 'Segoe UI',
            'font_size': 10,
            'bg_color': '#F0F4F8',
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#D0D9E0',
            'text_wrap': True,
            'indent': 1,
        })
        meta_value_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#D0D9E0',
            'text_wrap': True,
            'indent': 1,
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
            'bottom_color': '#005EB8',
            'text_wrap': True,
            'indent': 1,
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
            'border_color': '#003A70',
            'text_wrap': True,
            'indent': 1,
        })
        table_cell_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#E2E8F0',
            'text_wrap': True,
            'indent': 1,
        })
        table_cell_num_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#E2E8F0',
            'num_format': '#,##0.00',
            'text_wrap': True,
            'indent': 0,
        })
        table_cell_int_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#E2E8F0',
            'num_format': '#,##0',
            'text_wrap': True,
            'indent': 0,
        })
        table_cell_percent_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#E2E8F0',
            'num_format': '0.00%',
            'text_wrap': True,
            'indent': 0,
        })
        table_cell_currency_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#E2E8F0',
            'num_format': '£#,##0.00',
            'text_wrap': True,
            'indent': 0,
        })
        table_cell_text_center_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#E2E8F0',
            'text_wrap': True,
            'indent': 0,
        })
        worksheet = workbook.add_worksheet('Finalised ERIC Return')
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 45)
        worksheet.set_column('C:C', 16)
        worksheet.set_column('D:D', 25)
        worksheet.set_column('E:E', 16)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 35)
        worksheet.set_row(0, 45)
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
            worksheet.set_row(r, 24)
            worksheet.merge_range(r, 0, r, 1, label, meta_label_format)
            worksheet.merge_range(r, 2, r, 6, val, meta_value_format)
            r += 1
        r += 1
        sections = self.dataset_id.section_ids.sorted('sequence')
        for section in sections:
            worksheet.set_row(r, 30)
            worksheet.merge_range(r, 0, r, 6, f"Section: {section.name} [{section.code}]", section_header_format)
            r += 1
            worksheet.set_row(r, 26)
            headers = ['Item Code', 'Item Name', 'Data Type', 'Value', 'Unit', 'Reporting Level', 'Site Code/Name']
            for col, header in enumerate(headers):
                worksheet.write(r, col, header, table_header_format)
            r += 1
            values = self.value_ids.filtered(
                lambda v: v.section_id == section and v.item_def_id.change_flag != 'removed'
            ).sorted(
            lambda v: (v.item_def_id.reporting_level, v.site_id.name or '', v.item_def_id.sequence)
            )
            for val in values:
                worksheet.set_row(r, 22)
                worksheet.write(r, 0, val.item_def_id.code or '', table_cell_format)
                worksheet.write(r, 1, val.item_def_id.name or '', table_cell_format)
                worksheet.write(r, 2, (val.item_def_id.data_type or '').title(), table_cell_text_center_format)
                dt = val.item_def_id.data_type
                v_typed = self._get_value_typed(val)
                if dt == 'integer' and v_typed != '' and v_typed is not None:
                    worksheet.write_number(r, 3, v_typed, table_cell_int_format)
                elif dt == 'currency' and v_typed != '' and v_typed is not None:
                    worksheet.write_number(r, 3, v_typed, table_cell_currency_format)
                elif dt == 'percent' and v_typed != '' and v_typed is not None:
                    worksheet.write_number(r, 3, v_typed / 100.0, table_cell_percent_format)
                elif dt in ('float',) and v_typed != '' and v_typed is not None:
                    worksheet.write_number(r, 3, v_typed, table_cell_num_format)
                else:
                    worksheet.write(r, 3, v_typed if v_typed != '' else '', table_cell_format)
                worksheet.write(r, 4, val.item_def_id.unit or '', table_cell_text_center_format)
                worksheet.write(r, 5, (val.item_def_id.reporting_level or '').title(), table_cell_text_center_format)
                if val.site_id:
                    site_display = f"[{val.site_id.code}] {val.site_id.name}"
                else:
                    site_display = 'Organisational'
                worksheet.write(r, 6, site_display, table_cell_format)
                r += 1
            r += 2
        footer_format = workbook.add_format({
            'font_name': 'Segoe UI',
            'font_size': 9,
            'font_color': '#666666',
            'align': 'right',
            'valign': 'vcenter',
            'top': 1,
            'top_color': '#D0D9E0',
            'indent': 1,
        })
        worksheet.set_row(r, 20)
        worksheet.merge_range(
            r, 0, r, 6,
            f"Generated on: {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            footer_format
        )
        workbook.close()
        output.seek(0)
        filename = f"ERIC_Export_{self.name.replace(' ', '_')}_{fields.Date.today()}.xlsx"
        return output.getvalue(), filename

    def action_export_finalized_excel(self):
        """
        Export the return to a formatted Excel file.
        Creates an attachment and returns a download URL.
        Raises:
            UserError: If return is not finalised or submitted.
        """
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
                lambda v: v.item_def_id.code == prior_val.item_def_id.code and
                          v.site_id.id == prior_val.site_id.id
            )
            attachment_copies = []
            if prior_val.attachment_ids:
                for att in prior_val.attachment_ids:
                    copy_att = self.env['ir.attachment'].create({
                        'name': att.name,
                        'type': att.type,
                        'datas': att.datas,
                        'mimetype': att.mimetype,
                        'res_model': 'nhs.eric.value',
                    })
                    attachment_copies.append(copy_att.id)
            if not existing:
                current_item_def = self.dataset_id.section_ids.mapped('item_def_ids').filtered(
                    lambda i: i.code == prior_val.item_def_id.code
                )
                if current_item_def:
                    new_val = self.env['nhs.eric.value'].with_context(
                        bypass_owner_check=True
                    ).create({
                        'return_id': self.id,
                        'item_def_id': current_item_def[0].id,
                        'site_id': prior_val.site_id.id,
                        'value_number': prior_val.value_number,
                        'value_text': prior_val.value_text,
                        'value_bool': prior_val.value_bool,
                        'status': 'populated' if prior_val._has_value() else 'gap',
                        'attachment_ids': [(6, 0, attachment_copies)] if attachment_copies else False
                    })
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
        self.message_post(
            body=f"Carried forward {copied_count} manual values from prior year return '{self.prior_return_id.name}'.")
        return True

    @api.depends(
        'value_ids', 'value_ids.value_number', 'value_ids.auto_value', 'value_ids.value_text', 'value_ids.value_bool',
        'value_ids.is_overridden', 'prior_return_id', 'prior_return_id.value_ids',
        'prior_return_id.value_ids.value_number', 'prior_return_id.value_ids.auto_value',
        'prior_return_id.value_ids.is_overridden'
    )
    def _compute_comparison_lines(self):
        """
        Compute comparison lines showing year-on-year changes for each item.
        Only shows items that have changed or are new.
        """
        for record in self:
            if not record.prior_return_id:
                prior = False
                if record.dataset_id and record.dataset_id.prior_dataset_id:
                    prior = self.search([
                        ('company_id', '=', record.company_id.id),
                        ('dataset_id', '=', record.dataset_id.prior_dataset_id.id)
                    ], limit=1)
                if not prior and record.id:
                    prior = self.search([
                        ('company_id', '=', record.company_id.id),
                        ('id', '<', record.id)
                    ], order='id desc', limit=1)
                if prior:
                    record.prior_return_id = prior.id
                else:
                    record.comparison_line_ids = [(5, 0, 0)]
                    continue
            prior_vals = {}
            for val in record.prior_return_id.value_ids:
                if val.item_def_id.change_flag == 'removed':
                    continue
                key = (val.item_def_id.code, val.site_id.id if val.site_id else False)
                prior_vals[key] = val
            threshold_param = self.env['ir.config_parameter'].sudo().get_param(
                'odoo_nhs_eric.anomaly_threshold_pct', '50.0')
            try:
                threshold = float(threshold_param)
            except ValueError:
                threshold = 50.0
            lines_vals = []
            for val in record.value_ids:
                if val.item_def_id.change_flag == 'removed':
                    continue
                key = (val.item_def_id.code, val.site_id.id if val.site_id else False)
                prior_val = prior_vals.get(key)
                prior_has_value = prior_val and prior_val._has_value()
                current_has_value = val._has_value()
                if not current_has_value and not prior_has_value:
                    continue
                change_pct = 0.0
                cur_num = val._get_numeric_value() or 0.0
                pri_num = prior_val._get_numeric_value() or 0.0 if prior_val else 0.0
                if prior_has_value and current_has_value:
                    if pri_num != 0.0:
                        change_pct = ((cur_num - pri_num) / abs(pri_num)) * 100.0
                    elif cur_num != 0.0:
                        change_pct = 100.0
                    if abs(change_pct) < 0.01 and cur_num == pri_num:
                        if val._get_value_display() == prior_val._get_value_display():
                            continue
                elif current_has_value and not prior_has_value:
                    change_pct = 100.0
                elif not current_has_value and prior_has_value:
                    change_pct = -100.0
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
                    'return_id': record.id,
                    'item_def_id': val.item_def_id.id,
                    'site_id': val.site_id.id if val.site_id else False,
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
                'codes': ['E_GIA', 'GIA', 'S_GIA'],
                'source_keys': ['estate.total_gia', 'estate.occupied_floor_area']
            },
            'backlog_total': {
                'codes': ['E_BACKLOG_TOT', 'E_BACKLOG_TOTAL', 'BACKLOG_TOTAL', 'S_BACKLOG_TOT', 'S_BACKLOG_TOTAL'],
                'source_keys': ['estate.backlog.total']
            },
            'backlog_high': {
                'codes': ['E_BACKLOG_HIGH', 'BACKLOG_HIGH', 'S_BACKLOG_HIGH'],
                'source_keys': ['estate.backlog.high']
            },
            'backlog_significant': {
                'codes': ['E_BACKLOG_SIGNIFICANT', 'BACKLOG_SIGNIFICANT', 'S_BACKLOG_SIGNIFICANT'],
                'source_keys': ['estate.backlog.significant']
            },
            'backlog_moderate': {
                'codes': ['E_BACKLOG_MODERATE', 'BACKLOG_MODERATE', 'S_BACKLOG_MODERATE'],
                'source_keys': ['estate.backlog.moderate']
            },
            'backlog_low': {
                'codes': ['E_BACKLOG_LOW', 'BACKLOG_LOW', 'S_BACKLOG_LOW'],
                'source_keys': ['estate.backlog.low']
            },
            'compliance_pct': {
                'codes': ['C_PCT', 'C_COMPLIANCE', 'COMPLIANCE_PCT'],
                'source_keys': ['compliance.pct', 'compliance.compliance_pct']
            }
        }
        rules = mapping.get(metric_type, {})
        matching_vals = self.value_ids.filtered(
            lambda v: v.item_def_id.code in rules.get('codes', []) or v.item_def_id.source_key in
                      rules.get('source_keys', [])
        )
        if not matching_vals:
            return 0.0

        def get_val_num(v):
            return v._get_numeric_value() or 0.0

        trust_vals = matching_vals.filtered(lambda v: not v.site_id)
        if trust_vals:
            if metric_type == 'compliance_pct':
                return get_val_num(trust_vals[0])
            return sum(get_val_num(v) for v in trust_vals)
        if metric_type == 'compliance_pct':
            valid_vals = [get_val_num(v) for v in matching_vals]
            return sum(valid_vals) / len(valid_vals) if valid_vals else 0.0
        else:
            return sum(get_val_num(v) for v in matching_vals)

    @api.model
    def get_dashboard_metrics(self, return_id=None):
        """Fetch metrics, trends, source coverage, and section status for NHS ERIC Returns."""
        all_returns = self.search([])
        return_list = [{'id': r.id, 'name': r.name or r.year, 'year': r.year} for r in all_returns]
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
        sections_outstanding = 0
        section_lines = []
        for line in ret.section_line_ids:
            if line.state != 'signed_off':
                sections_outstanding += 1
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
        gia = ret._get_key_metric_value('gia')
        backlog = ret._get_key_metric_value('backlog_total')
        compliance = ret._get_key_metric_value('compliance_pct')
        metrics['headline'] = {
            'gia': gia,
            'backlog': backlog,
            'compliance': compliance,
            'cost_per_m2': (backlog / gia) if gia > 0 else 0.0,
        }
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
        trends = self.env['nhs.eric.trend.metric'].search([('company_id', '=', ret.company_id.id)],
                                                          order='year asc')
        trend_data = []
        for t in trends:
            trend_data.append({
                'year': t.year,
                'gia': t.gia,
                'backlog': t.backlog,
                'compliance_pct': t.compliance_pct,
                'cost_per_m2': t.cost_per_m2,
            })
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
            trend_data = sorted(trend_data, key=lambda x: x['year'])
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
    """
        Model for ERIC Return Comparison Lines. This models the year-on-year
        comparison data for individual ERIC items. Each line represents a
        single item's value comparison between the current return and the
        prior year's return, showing changes, trends, and alerts.
    """
    _name = 'nhs.eric.return.comparison.line'
    _description = 'ERIC Return Comparison Line'
    _order = 'item_code asc'

    return_id = fields.Many2one('nhs.eric.return', string='Return', ondelete='cascade', required=True,
                                 help="Return this line belongs to.")
    item_def_id = fields.Many2one('nhs.eric.item.def', string='Item', required=True,
                                   help="ERIC item being compared.")
    item_code = fields.Char(related='item_def_id.code', string='Code', store=True,
                             help="Item code.")
    site_id = fields.Many2one('nhs.estate.site', string='Site',
                               help="Site for site-level comparisons.")
    current_value_display = fields.Char(string='Current Value',
                                         help="Current year's value display.")
    prior_value_display = fields.Char(string='Prior Value',
                                       help="Prior year's value display.")
    current_value_num = fields.Float(string='Current Num',
                                      help="Current year's numeric value.")
    prior_value_num = fields.Float(string='Prior Num',
                                    help="Prior year's numeric value.")
    percentage_change = fields.Float(string='Change (%)',
                                      help="Percentage change between values.")
    highlight_color = fields.Selection([
        ('green', 'Increase'),
        ('red', 'Decrease'),
        ('orange', 'Significant Change'),
        ('normal', 'Normal')
    ], string='Alert Level', default='normal',
        help="Alert color based on change significance.")
    change_flag = fields.Selection([
        ('up', '↗ Up'),
        ('down', '↘ Down'),
        ('flat', '→ No Change')
    ], string='Trend', default='flat',
        help="Trend direction: Up, Down, or Flat.")


class NhsEricTrendMetric(models.Model):
    """
        Model for ERIC Trend Metrics. This stores historical trend data for
        key ERIC metrics across financial years. Each record captures
        aggregated metrics like GIA, backlog costs by risk category,
        compliance percentages, and cost per square meter for trend analysis.
    """
    _name = 'nhs.eric.trend.metric'
    _description = 'ERIC Trend Metrics'
    _order = 'year asc'

    year = fields.Char(string='Year', required=True, help="Financial year of the trend data.")
    company_id = fields.Many2one('res.company', string='Organisation', required=True,
                                 help="Organisation to which metrics belong.")
    gia = fields.Float(string='Total GIA (m²)', help="Total Gross Internal Area in m².")
    backlog = fields.Float(string='Total Backlog Cost (£)', help="Total estimated backlog cost.")
    backlog_high = fields.Float(string='High Risk Backlog (£)', help="Cost of backlog items at high risk.")
    backlog_significant = fields.Float(string='Significant Risk Backlog (£)',
                                       help="Cost of backlog items at significant risk.")
    backlog_moderate = fields.Float(string='Moderate Risk Backlog (£)',
                                    help="Cost of backlog items at moderate risk.")
    backlog_low = fields.Float(string='Low Risk Backlog (£)', help="Cost of backlog items at low risk.")
    compliance_pct = fields.Float(string='Overall Compliance (%)', help="Overall compliance percentage.")
    cost_per_m2 = fields.Float(string='Cost per m² (£/m²)', help="Backlog cost per square meter of GIA.")

    @api.model
    def refresh_trends(self, company_id=None):
        """Regenerate trend records from all returns."""
        domain = []
        if company_id:
            domain.append(('company_id', '=', company_id))
        returns = self.env['nhs.eric.return'].search(domain)
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
        existing_keys = {(r.company_id.id, r.year) for r in returns}
        trend_domain = [('company_id', '=', company_id)] if company_id else []
        all_trends = self.search(trend_domain)
        for t in all_trends:
            if (t.company_id.id, t.year) not in existing_keys:
                t.unlink()
