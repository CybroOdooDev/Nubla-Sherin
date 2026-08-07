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

class NHSESite(models.Model):
    _name = 'nhs.estate.site'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'NHS estate site / campus'
    _order = 'name'
    _parent_name = 'parent_id'
    _parent_store = True

    name = fields.Char(
        string='Site Name',
        required=True,
        tracking=True,
        help="Official name of the site/location (e.g., 'St. Mary's Hospital', 'Northgate Health Centre')"
    )
    code = fields.Char(
        string='Site Code',
        required=True,
        tracking=True,
        index=True,
        help="Unique reference code for the site (e.g., NHS site code or internal identifier)"
    )
    parent_id = fields.Many2one(
        'nhs.estate.site',
        string='Parent Site',
        index=True,
        ondelete='restrict',
        help="Parent site for hierarchical site structures (e.g., hospital campus containing multiple sites)"
    )
    parent_path = fields.Char(
        index=True,
        help="Hierarchical path of parent sites for efficient tree structure navigation"
    )
    child_ids = fields.One2many(
        'nhs.estate.site',
        'parent_id',
        string='Sub-sites',
        help="List of child/sub-sites associated with this parent site"
    )
    child_count = fields.Integer(
        string='Child Count',
        compute='_compute_child_count',
        store=True,
        help="Total number of sub-sites under this site (auto-calculated)"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Company that owns or manages this site (defaults to current company)"
    )
    site_type = fields.Selection([
        ('acute', 'Acute Hospital'),
        ('community', 'Community'),
        ('mental_health', 'Mental Health'),
        ('admin', 'Admin'),
        ('other', 'Other')
    ], string='Site Type',
        help="Category/type classification of the healthcare site"
    )
    operational_status = fields.Selection([
        ('operational', 'Operational'),
        ('partial', 'Partially Operational'),
        ('closed', 'Closed'),
        ('disposed', 'Disposed')
    ], string='Operational Status',
        required=True,
        default='operational',
        group_expand=True,
        help="Current operational state of the site"
    )
    street = fields.Char(
        string='Street',
        help="Street address line 1 of the site location"
    )
    street2 = fields.Char(
        string='Street2',
        help="Street address line 2 of the site location (optional)"
    )
    city = fields.Char(
        string='City',
        help="City or town where the site is located"
    )
    zip = fields.Char(
        string='ZIP',
        help="Postal/ZIP code for the site address"
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        help="Country where the site is located"
    )
    site_id = fields.Many2one(
        'nhs.estate.site',
        string='Site',
        compute='_compute_site_id',
        store=True,
        index=True,
        help="Primary site reference (computed for hierarchical consistency)"
    )
    latitude = fields.Float(
        string='Latitude',
        digits=(16, 10),
        help="Geographic latitude coordinate for the site (for mapping purposes)"
    )
    longitude = fields.Float(
        string='Longitude',
        digits=(16, 10),
        help="Geographic longitude coordinate for the site (for mapping purposes)"
    )
    land_area_ha = fields.Float(
        string='Land Area (hectares)',
        help="Total land area of the site measured in hectares"
    )
    car_parking_spaces = fields.Integer(
        string='Car Parking Spaces',
        help="Total number of car parking spaces available at the site"
    )
    acquired_date = fields.Date(
        string='Acquisition Date',
        help="Date the site was acquired or officially opened"
    )
    owner_org = fields.Char(
        string='Owner Organisation',
        help="Name of the organisation that owns the site"
    )
    manager_id = fields.Many2one(
        'res.users',
        string='Site Manager',
        help="User responsible for managing the site (primary contact)"
    )
    building_ids = fields.One2many(
        'nhs.estate.building',
        'site_id',
        string='Buildings',
        help="List of buildings located at this site"
    )
    building_count = fields.Integer(
        string='Building Count',
        compute='_compute_building_count',
        store=True,
        help="Total number of buildings at this site (auto-calculated)"
    )
    space_count = fields.Integer(
        string='Space Count',
        compute='_compute_space_count',
        store=True,
        help="Total number of spaces/rooms across all buildings at this site (auto-calculated)"
    )
    total_gia = fields.Float(
        string='Total Gross Internal Area (m²)',
        compute='_compute_rollups',
        store=True,
        help="Total gross internal area of all buildings at this site in square meters (auto-calculated)"
    )
    total_backlog = fields.Monetary(
        string='Total Backlog',
        currency_field='currency_id',
        compute='_compute_rollups',
        store=True,
        help="Total estimated cost of all backlog items across this site (auto-calculated)"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help="Currency used for financial values (defaults to company currency)"
    )
    image = fields.Many2many(
        'ir.attachment',
        'nhs_estate_site_image_rel',
        'site_id', 'attachment_id',
        string='Site Photos',
        help="Main photographs or aerial views of the site"
    )
    active = fields.Boolean(
        default=True,
        help="Whether this site record is active and visible in the system"
    )
    is_virtual = fields.Boolean(compute='_compute_virtual_info')
    virtual_type_str = fields.Char(compute='_compute_virtual_info')
    virtual_space_type = fields.Char(compute='_compute_virtual_info')
    virtual_operational_status = fields.Char(compute='_compute_virtual_info')
    site_clinical_area = fields.Float(
        string='Clinical Area (m²)',
        compute='_compute_site_analysis',
        store=True,
        help='Total clinical area on site'
    )
    site_non_clinical_area = fields.Float(
        string='Non-Clinical Area (m²)',
        compute='_compute_site_analysis',
        store=True,
        help='Total non-clinical area on site'
    )
    site_occupied_area = fields.Float(
        string='Occupied Area (m²)',
        compute='_compute_site_analysis',
        store=True,
        help='Total occupied area on site'
    )
    site_vacant_area = fields.Float(
        string='Vacant Area (m²)',
        compute='_compute_site_analysis',
        store=True,
        help='Total vacant area on site'
    )

    _name_uniq = models.Constraint(
        'unique(code)',
        'Site code must be unique!',
    )

    @api.depends('building_ids.clinical_area', 'building_ids.non_clinical_area',
                 'building_ids.occupied_area', 'building_ids.vacant_area')
    def _compute_site_analysis(self):
        """Compute total clinical area,non-clinical area ,occupied area and vacant area for this site.
        Map to the buildings associated to this site and fetch the data.
        """
        for site in self:
            site.site_clinical_area = sum(site.building_ids.mapped('clinical_area'))
            site.site_non_clinical_area = sum(site.building_ids.mapped('non_clinical_area'))
            site.site_occupied_area = sum(site.building_ids.mapped('occupied_area'))
            site.site_vacant_area = sum(site.building_ids.mapped('vacant_area'))

    @api.depends('parent_id')
    def _compute_site_id(self):
        """Compute the top-level parent site for this site record.
        Walks up the site hierarchy until it finds a site without a parent,
        and assigns its ID to the site_id field.
        """
        for record in self:
            curr = record
            while curr.parent_id:
                curr = curr.parent_id
            record.site_id = curr.id

    @api.depends('building_ids')
    def _compute_building_count(self):
        """Compute the total number of buildings directly associated with this site."""
        for record in self:
            record.building_count = len(record.building_ids)

    @api.depends('building_ids.floor_ids.space_ids')
    def _compute_space_count(self):
        """Compute the total count of spaces/rooms across all buildings and floors of this site."""
        for record in self:
            count = 0
            for building in record.building_ids:
                for floor in building.floor_ids:
                    count += len(floor.space_ids)
            record.space_count = count

    @api.depends('building_ids.gia', 'building_ids.backlog_total')
    def _compute_rollups(self):
        """Compute rollup metrics (total GIA and backlog cost) for this site.
        Aggregates GIA and backlog maintenance costs from all child buildings.
        """
        for record in self:
            record.total_gia = sum(record.building_ids.mapped('gia'))
            record.total_backlog = sum(record.building_ids.mapped('backlog_total'))

    @api.depends('child_ids')
    def _compute_child_count(self):
        """Compute the number of direct child sites for this site."""
        for record in self:
            record.child_count = len(record.child_ids)

    @api.depends()
    def _compute_virtual_info(self):
        """Determine virtual record properties based on virtual ID ranges.
        Ids >= 300000 are virtual Space records.
        Ids >= 200000 are virtual Floor records.
        Ids >= 100000 are virtual Building records.
        Real site records have IDs < 100000.
        """
        for record in self:
            try:
                rid = int(record.id) if record.id else 0
            except (ValueError, TypeError):
                rid = 0
            if rid >= 300000:
                record.is_virtual = True
                record.virtual_type_str = 'Space'
                record.virtual_space_type = False
                record.virtual_operational_status = False
            elif rid >= 200000:
                record.is_virtual = True
                record.virtual_type_str = 'Floor'
                record.virtual_space_type = False
                record.virtual_operational_status = False
            elif rid >= 100000:
                record.is_virtual = True
                record.virtual_type_str = 'Building'
                record.virtual_space_type = False
                record.virtual_operational_status = False
            else:
                record.is_virtual = False
                record.virtual_type_str = False
                record.virtual_space_type = False
                record.virtual_operational_status = False

    def _compute_display_name(self):
        """Compute custom display names for both real and virtual records in tree/hierarchy context.
        - Real records receive '[code] name' formatting.
        - Virtual records resolve display names from underlying building, floor, or space objects.
        """
        real_records = self.filtered(lambda r: isinstance(r.id, int) and r.id < 100000 or not r.id)
        if real_records:
            super(NHSESite, real_records)._compute_display_name()
            # Restore the legacy name_get behavior for display_name
            for record in real_records:
                if record.code and record.name and not record.display_name.startswith(f"[{record.code}]"):
                    record.display_name = f"[{record.code}] {record.name}"
        for record in self:
            try:
                rid = int(record.id) if record.id else 0
            except (ValueError, TypeError):
                rid = 0
            if rid >= 100000:
                vid = rid
                if vid < 200000:
                    b = self.env['nhs.estate.building'].browse(vid - 100000)
                    record.display_name = f"[{b.code}] {b.name}" if b.code else b.name
                elif vid < 300000:
                    f = self.env['nhs.estate.floor'].browse(vid - 200000)
                    record.display_name = f.name
                else:
                    s = self.env['nhs.estate.space'].browse(vid - 300000)
                    record.display_name = f"[{s.code}] {s.name}" if s.code else s.name

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle code field normalization and sequence generation.
        Args:
            vals_list (list of dicts): Field value dicts for new records.
        Returns:
            recordset: Newly created site records.
        """
        for vals in vals_list:
            # Prepare code (convert to uppercase)
            vals = self._prepare_code(vals)
            # Assign sequence if no code provided
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('nhs.estate.site')
        return super().create(vals_list)

    def write(self, vals):
        """Override write to handle code field casing and route parent updates for virtual records.
        Args:
            vals (dict): Fields and values to update.
        Returns:
            bool: True if successful, False otherwise.
        """
        if vals.get('code'):
            vals['code'] = vals['code'].upper()

        def is_real(r):
            if not r.id:
                return True
            try:
                return int(r.id) < 100000
            except (ValueError, TypeError):
                return True

        real_records = self.filtered(is_real)
        virtual_records = self.filtered(lambda r: not is_real(r))
        res = True
        if real_records:
            res = super(NHSESite, real_records).write(vals)
        if virtual_records and 'parent_id' in vals:
            new_parent_id = vals['parent_id']
            for record in virtual_records:
                vid = record.id
                if vid < 200000:
                    b = self.env['nhs.estate.building'].browse(vid - 100000)
                    b.site_id = new_parent_id
                elif vid < 300000:
                    f = self.env['nhs.estate.floor'].browse(vid - 200000)
                    f.building_id = new_parent_id - 100000 if new_parent_id else False
                else:
                    s = self.env['nhs.estate.space'].browse(vid - 300000)
                    s.floor_id = new_parent_id - 200000 if new_parent_id else False
        return res

    def exists(self):
        """Verify the existence of site records, supporting both real and virtual record IDs.
        Separates input IDs into real site IDs and virtual IDs, querying existence
        individually and returning the combined recordset of existing records.
        Returns:
            recordset: Sites that exist in the database or virtual space.
        """
        real_ids = []
        virtual_ids = []
        for rid in self._ids:
            try:
                num_id = int(rid) if rid else 0
                if num_id >= 100000:
                    virtual_ids.append(num_id)
                else:
                    real_ids.append(rid)
            except (ValueError, TypeError):
                real_ids.append(rid)
        real_records = self.browse(real_ids)
        existing_real = super(NHSESite, real_records).exists()
        existing_virtual = []
        for vid in virtual_ids:
            if vid < 200000:
                if self.env['nhs.estate.building'].browse(vid - 100000).exists():
                    existing_virtual.append(vid)
            elif vid < 300000:
                if self.env['nhs.estate.floor'].browse(vid - 200000).exists():
                    existing_virtual.append(vid)
            else:
                if self.env['nhs.estate.space'].browse(vid - 300000).exists():
                    existing_virtual.append(vid)
        return self.browse(existing_real.ids + existing_virtual)

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        """Override search to handle custom virtual tree/hierarchy search queries.
        Translates virtual search domains to return matching virtual records if a hierarchy query is detected.
        """
        if self._is_hierarchy_query(args) and not self.env.context.get('in_resolve_domain'):
            self = self.with_context(in_resolve_domain=True)
            ids = self._resolve_domain_to_ids(args)
            return self.browse(ids)
        return super().search(args, offset, limit, order)

    @api.model
    def search_count(self, args, limit=None):
        """Override search_count to count records matching custom virtual tree queries."""
        if self._is_hierarchy_query(args) and not self.env.context.get('in_resolve_domain'):
            self = self.with_context(in_resolve_domain=True)
            ids = self._resolve_domain_to_ids(args)
            return len(ids)
        return super().search_count(args, limit)

    @api.model
    @api.readonly
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        """Override web_search_read to provide custom formatting for virtual hierarchy nodes."""
        if self._is_hierarchy_query(domain) and not self.env.context.get('in_resolve_domain'):
            self = self.with_context(in_resolve_domain=True)
            ids = self._resolve_domain_to_ids(domain)
            records = self.browse(ids)
            values_records = records.web_read(specification)
            return self._format_web_search_read_results(domain, values_records, offset, limit, count_limit)
        return super().web_search_read(domain, specification, offset, limit, order, count_limit)

    @api.readonly
    def web_read(self, specification):
        """Override web_read to construct virtual nodes dynamically.
        Resolves specifications on virtual building, floor, and space records,
        mapping database relations to the simulated site hierarchy structures.
        """
        real_ids = []
        virtual_ids = []
        for rid in self._ids:
            try:
                num_id = int(rid) if rid else 0
                if num_id >= 100000:
                    virtual_ids.append(num_id)
                else:
                    real_ids.append(rid)
            except (ValueError, TypeError):
                real_ids.append(rid)
        record_data_by_id = {}
        if real_ids:
            real_records = self.browse(real_ids)
            real_res = super(NHSESite, real_records).web_read(specification)
            for r_data in real_res:
                record_data_by_id[r_data['id']] = r_data
        child_field_spec = specification.get('child_ids', {})
        if 'child_ids' in specification:
            for rid in real_ids:
                if rid in record_data_by_id:
                    site = self.browse(rid)
                    child_node_ids = site.child_ids.ids + [100000 + b.id for b in site.building_ids]
                    if child_field_spec.get('fields'):
                        child_records_vals = self.browse(child_node_ids).web_read(child_field_spec['fields'])
                        record_data_by_id[rid]['child_ids'] = child_records_vals
                    else:
                        record_data_by_id[rid]['child_ids'] = child_node_ids
        for vid in virtual_ids:
            record_data = {'id': vid}
            if vid < 200000:
                b = self.env['nhs.estate.building'].browse(vid - 100000)
                if not b.exists():
                    continue
                name = b.name or 'Unnamed Building'
                code = b.code or False
                display_name = f"[{b.code}] {b.name}" if b.code else b.name
                parent_id = b.site_id.id
                parent_name = b.site_id.name
                child_ids = [200000 + f.id for f in b.floor_ids]
                site_type = b.site_id.site_type if b.site_id else False
                operational_status = b.operational_status
                city = b.site_id.city if b.site_id else False
                building_count = len(b.floor_ids)
                space_count = b.space_count
                total_gia = b.gia
                total_backlog = b.backlog_total
                company_id = b.company_id.id if b.company_id else False
                site_pp = b.site_id.parent_path or f"{b.site_id.id}/" if b.site_id else ""
                parent_path = f"{site_pp}{100000 + b.id}/"
                image = []
            elif vid < 300000:
                f = self.env['nhs.estate.floor'].browse(vid - 200000)
                if not f.exists():
                    continue
                name = f.name or 'Unnamed Floor'
                code = False
                display_name = f.name or 'Unnamed Floor'
                parent_id = 100000 + f.building_id.id
                parent_name = f.building_id.name
                child_ids = [300000 + s.id for s in f.space_ids]
                site_type = f.building_id.site_id.site_type if f.building_id and f.building_id.site_id else False
                operational_status = f.building_id.operational_status if f.building_id else False
                city = f.building_id.site_id.city if f.building_id and f.building_id.site_id else False
                building_count = 0
                space_count = f.space_count
                total_gia = f.gia
                total_backlog = 0.0
                company_id = f.company_id.id if f.company_id else False
                site_pp = f.building_id.site_id.parent_path or f"{f.building_id.site_id.id}/" if (f.building_id and
                                                                                        f.building_id.site_id) else ""
                parent_path = f"{site_pp}{100000 + f.building_id.id}/{200000 + f.id}/"
                image = []
            else:
                s = self.env['nhs.estate.space'].browse(vid - 300000)
                if not s.exists():
                    continue
                name = s.name or 'Unnamed Space'
                code = s.code or False
                display_name = f"[{s.code}] {s.name}" if s.code else (s.name or 'Unnamed Space')
                parent_id = 200000 + s.floor_id.id
                parent_name = s.floor_id.name
                child_ids = []
                site_type = False
                operational_status = False
                virtual_space_type = dict(s._fields['space_type'].selection).get(
                    s.space_type) if s.space_type else False
                virtual_operational_status = dict(s._fields['utilisation'].selection).get(
                    s.utilisation) if s.utilisation else False
                city = s.department
                building_count = 0
                space_count = 0
                total_gia = s.area
                total_backlog = 0.0
                company_id = s.company_id.id if s.company_id else False
                site_pp = s.floor_id.building_id.site_id.parent_path or f"{s.floor_id.building_id.site_id.id}/" \
                    if s.floor_id and s.floor_id.building_id and s.floor_id.building_id.site_id else ""
                parent_path = f"{site_pp}{100000 + s.floor_id.building_id.id}/{200000 + s.floor_id.id}/{300000 + s.id}/"
                image = []
            for fname, field_spec in specification.items():
                if fname == 'id':
                    continue
                elif fname == 'parent_path':
                    record_data['parent_path'] = parent_path
                elif fname == 'display_name':
                    record_data['display_name'] = display_name
                elif fname == 'name':
                    record_data['name'] = name
                elif fname == 'code':
                    record_data['code'] = code
                elif fname == 'site_type':
                    record_data['site_type'] = site_type
                elif fname == 'operational_status':
                    record_data['operational_status'] = operational_status
                elif fname == 'virtual_space_type':
                    if vid >= 300000:
                        record_data['virtual_space_type'] = virtual_space_type
                    else:
                        record_data['virtual_space_type'] = False
                elif fname == 'virtual_operational_status':
                    if vid >= 300000:
                        record_data['virtual_operational_status'] = virtual_operational_status
                    else:
                        record_data['virtual_operational_status'] = False
                elif fname == 'city':
                    record_data['city'] = city
                elif fname == 'building_count':
                    record_data['building_count'] = building_count
                elif fname == 'space_count':
                    record_data['space_count'] = space_count
                elif fname == 'total_gia':
                    record_data['total_gia'] = total_gia
                elif fname == 'total_backlog':
                    record_data['total_backlog'] = total_backlog
                elif fname == 'company_id':
                    record_data['company_id'] = company_id
                elif fname == 'image':
                    record_data['image'] = image
                elif fname == 'is_virtual':
                    record_data['is_virtual'] = True
                elif fname == 'virtual_type_str':
                    if vid >= 300000:
                        record_data['virtual_type_str'] = 'Space'
                    elif vid >= 200000:
                        record_data['virtual_type_str'] = 'Floor'
                    else:
                        record_data['virtual_type_str'] = 'Building'
                elif fname == 'parent_id':
                    if parent_id:
                        if 'fields' in field_spec:
                            p_spec = field_spec['fields']
                            p_data = {'id': parent_id}
                            if 'display_name' in p_spec:
                                p_data['display_name'] = parent_name
                            record_data['parent_id'] = p_data
                        else:
                            record_data['parent_id'] = (parent_id, parent_name)
                    else:
                        record_data['parent_id'] = False
                elif fname == 'site_id':
                    if vid < 200000:
                        b = self.env['nhs.estate.building'].browse(vid - 100000)
                        site = b.site_id
                    elif vid < 300000:
                        f = self.env['nhs.estate.floor'].browse(vid - 200000)
                        site = f.building_id.site_id if f.building_id else False
                    else:
                        s = self.env['nhs.estate.space'].browse(vid - 300000)
                        site = s.floor_id.building_id.site_id if s.floor_id and s.floor_id.building_id else False
                    if site:
                        if 'fields' in field_spec:
                            s_spec = field_spec['fields']
                            s_data = {'id': site.id}
                            if 'display_name' in s_spec:
                                s_data['display_name'] = site.name
                            record_data['site_id'] = s_data
                        else:
                            record_data['site_id'] = (site.id, site.name)
                    else:
                        record_data['site_id'] = False
                elif fname == 'child_ids':
                    if field_spec.get('fields'):
                        child_records_vals = self.browse(child_ids).web_read(field_spec['fields'])
                        record_data['child_ids'] = child_records_vals
                    else:
                        record_data['child_ids'] = child_ids
                else:
                    if self._fields.get(fname):
                        field_type = self._fields[fname].type
                        if field_type in ('one2many', 'many2many'):
                            record_data[fname] = []
                        else:
                            record_data[fname] = False
                    else:
                        record_data[fname] = False
            record_data_by_id[vid] = record_data
        result = []
        for rid in self._ids:
            if rid in record_data_by_id:
                result.append(record_data_by_id[rid])
        return result

    @api.model
    def hierarchy_read(self, domain, specification, parent_field, child_field=None, order=None):
        """Override hierarchy_read to execute in context of virtual hierarchy view.
        Forces `in_hierarchy_view=True` in context to ensure search and load operations
        translate virtual structures.
        """
        self = self.with_context(in_hierarchy_view=True)
        return super().hierarchy_read(domain, specification, parent_field, child_field, order)

    def action_operational(self):
        """Set the site's operational status to 'operational'."""
        self.operational_status = 'operational'

    def action_partial_operational(self):
        """Set the site's operational status to 'partial' operational."""
        self.operational_status = 'partial'

    def action_closed(self):
        """Set the site's operational status to 'closed'."""
        self.operational_status = 'closed'

    def action_disposed(self):
        """Set the site's operational status to 'disposed'."""
        self.operational_status = 'disposed'

    def action_view_buildings(self):
        """Return an action displaying all buildings associated with this site.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Buildings',
            'res_model': 'nhs.estate.building',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id}
        }

    def action_view_hierarchy(self):
        """Return an action displaying the estate hierarchy tree view for this site and its descendants.
        Resolves descendant real site IDs and constructs a domain containing
        both real site IDs and virtual building IDs.
        """
        self.ensure_one()
        descendant_sites = self.search([('id', 'child_of', self.id)])
        site_ids = descendant_sites.ids
        building_ids = self.env['nhs.estate.building'].search([('site_id', 'in', site_ids)]).ids
        domain = [('id', 'in', site_ids)]
        for b_id in building_ids:
            domain[0][2].append(100000 + b_id)
        return {
            'type': 'ir.actions.act_window',
            'name': f'Hierarchy: {self.name}',
            'res_model': 'nhs.estate.site',
            'view_mode': 'hierarchy',
            'view_id': self.env.ref('odoo_nhs_estate.view_nhs_estate_site_hierarchy').id,
            'domain': domain,
            'context': {
                'default_parent_id': self.id,
                'in_hierarchy_view': True,
                'hierarchy_site_id': self.id,
                'hierarchy_root_site_id': self.id,
            },
        }

    def action_view_documents(self):
        """Return an action displaying all attachments/documents linked to this site.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.estate.site'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.estate.site',
                'default_res_id': self.id,
            }
        }

    def action_open_record(self):
        """Return a window action redirecting to the true form view of the selected node.
        Differentiates based on ID ranges:
        - Ids < 100000 -> Open nhs.estate.site
        - Ids < 200000 -> Open nhs.estate.building (resolved ID = ID - 100000)
        - Ids < 300000 -> Open nhs.estate.floor (resolved ID = ID - 200000)
        - Else -> Open nhs.estate.space (resolved ID = ID - 300000)
        """
        self.ensure_one()
        if self.id < 100000:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'nhs.estate.site',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'current',
            }
        elif self.id < 200000:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'nhs.estate.building',
                'res_id': self.id - 100000,
                'view_mode': 'form',
                'target': 'current',
            }
        elif self.id < 300000:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'nhs.estate.floor',
                'res_id': self.id - 200000,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'nhs.estate.space',
                'res_id': self.id - 300000,
                'view_mode': 'form',
                'target': 'current',
            }

    @api.model
    def get_estate_tree_data(self, site_ids=None):
        """Return the full Site -> Building -> Floor -> Space hierarchy as a list
        of dicts suitable for JSON serialisation by the OWL tree view.
        Args:
            site_ids (list of int, optional): list of site IDs to restrict the result.
        Returns:
            list: List of site node dicts.
        """
        domain = [('active', '=', True)]
        if site_ids:
            domain.append(('id', 'in', site_ids))
        sites = self.search(domain, order='name')
        result = []
        for site in sites:
            site_node = {
                'id': site.id,
                'name': site.name,
                'code': site.code or '',
                'model': 'nhs.estate.site',
                'type': 'site',
                'building_count': site.building_count,
                'total_gia': site.total_gia,
                'total_backlog': site.total_backlog,
                'operational_status': site.operational_status or '',
                'site_type': site.site_type or '',
                'city': site.city or '',
                'children': [],
            }
            for building in site.building_ids.sorted('name'):
                building_node = {
                    'id': building.id,
                    'name': building.name,
                    'code': building.code or '',
                    'model': 'nhs.estate.building',
                    'type': 'building',
                    'floor_count': building.floor_count,
                    'space_count': building.space_count,
                    'gia': building.gia,
                    'backlog_total': building.backlog_total,
                    'latest_condition_grade': building.latest_condition_grade or '',
                    'operational_status': building.operational_status or '',
                    'children': [],
                }
                for floor in building.floor_ids.sorted('sequence'):
                    floor_node = {
                        'id': floor.id,
                        'name': floor.name,
                        'code': '',
                        'model': 'nhs.estate.floor',
                        'type': 'floor',
                        'sequence': floor.sequence,
                        'space_count': floor.space_count,
                        'gia': floor.gia,
                        'function': floor.function_id.name if floor.function_id else '',
                        'children': [],
                    }
                    for space in floor.space_ids.sorted('name'):
                        space_node = {
                            'id': space.id,
                            'name': space.name,
                            'code': space.code or '',
                            'model': 'nhs.estate.space',
                            'type': 'space',
                            'area': space.area,
                            'space_type': space.space_type or '',
                            'is_clinical': space.is_clinical,
                            'utilisation': space.utilisation or '',
                            'department': space.department or '',
                            'children': [],
                        }
                        floor_node['children'].append(space_node)
                    building_node['children'].append(floor_node)
                site_node['children'].append(building_node)
            result.append(site_node)
        return result

    @api.model
    def get_import_templates(self):
        """Provide standard templates available for importing site records.
        Returns a list of dicts specifying labels and template asset file paths.
        """
        return [{
            'label': 'Import Template for Site',
            'template': '/odoo_nhs_estate/static/import_templates/site_template.xlsx',
        }]

    def _prepare_code(self, vals):
        """Normalize the code field by converting it to uppercase.
        Args:
            vals (dict): Field values.
        Returns:
            dict: The updated value dictionary with uppercase code.
        """
        if vals.get('code'):
            vals['code'] = vals['code'].upper()
        return vals

    def _is_hierarchy_query(self, domain):
        """Determine if a search domain contains parameters requesting virtual hierarchy nodes.
        Args:
            domain (list): The query domain.
        Returns:
            bool: True if the query is for virtual nodes or within the hierarchy view context.
        """
        if self.env.context.get('in_hierarchy_view'):
            return True
        if domain:
            for leaf in domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    field, op, val = leaf
                    if field == 'id':
                        vals = val if isinstance(val, list) else [val]
                        if any(isinstance(x, int) and x >= 100000 for x in vals):
                            return True
                    elif field == 'parent_id':
                        vals = val if isinstance(val, list) else [val]
                        if any(isinstance(x, int) and x >= 100000 for x in vals):
                            return True
        return False

    @api.model
    def _resolve_domain_to_ids(self, domain):
        """Resolve standard search domains to virtual IDs representing hierarchy nodes.
        Maps query domains (such as matching building codes/names, sites, or spaces)
        to the appropriate set of virtual IDs.
        Args:
            domain (list): The query domain.
        Returns:
            list: List of matching virtual and real IDs.
        """
        search_terms = []
        op_status_filter = None
        site_type_filter = None
        has_backlog_filter = False
        parent_id_filter = None
        has_parent_id_filter = False
        id_filter = None
        site_id_filter = None

        def parse_leaf(leaf):
            nonlocal op_status_filter, site_type_filter, has_backlog_filter, parent_id_filter, has_parent_id_filter, \
                id_filter, site_id_filter
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                field, op, val = leaf
                if field == 'name' and op in ('ilike', '=like', '='):
                    if val:
                        search_terms.append(val)
                elif field == 'code' and op in ('ilike', '='):
                    if val:
                        search_terms.append(val)
                elif field == 'operational_status' and op == '=':
                    op_status_filter = val
                elif field == 'site_type' and op == '=':
                    site_type_filter = val
                elif field == 'total_backlog' and op == '>' and val == 0:
                    has_backlog_filter = True
                elif field == 'parent_id':
                    has_parent_id_filter = True
                    parent_id_filter = val
                elif field == 'id':
                    if op == 'in':
                        id_filter = val
                    elif op == '=':
                        id_filter = [val]
                    elif op == 'child_of':
                        site_id_filter = val
                elif field == 'site_id':
                    if op == '=':
                        site_id_filter = val
                    elif op == 'in':
                        site_id_filter = val
            elif isinstance(leaf, (list, tuple)):
                for item in leaf:
                    parse_leaf(item)

        if domain:
            for item in domain:
                parse_leaf(item)
        hierarchy_root_site_id = self.env.context.get('hierarchy_root_site_id')
        if hierarchy_root_site_id:
            site_id_filter = hierarchy_root_site_id
        hierarchy_site_id = self.env.context.get('hierarchy_site_id')
        if hierarchy_site_id and not hierarchy_root_site_id:
            site_id_filter = hierarchy_site_id
        if id_filter is not None:
            return [int(x) for x in id_filter if x]
        if has_parent_id_filter:
            pids = parent_id_filter if isinstance(parent_id_filter, list) else [parent_id_filter]
            children_ids = []
            for pid in pids:
                if not pid:
                    if site_id_filter:
                        sites = self.env['nhs.estate.site'].search([('id', '=', site_id_filter), ('active', '=', True)])
                    else:
                        sites = self.env['nhs.estate.site'].search([('parent_id', '=', False), ('active', '=', True)])
                    children_ids.extend(sites.ids)
                elif pid < 100000:
                    site = self.env['nhs.estate.site'].browse(pid)
                    # Include all descendants
                    child_sites = self.search([('id', 'child_of', site.id)])
                    children_ids.extend(child_sites.ids)
                    # Include buildings for all descendant sites
                    for s in child_sites:
                        buildings = self.env['nhs.estate.building'].search([('site_id', '=', s.id)])
                        children_ids.extend([100000 + b.id for b in buildings])
                elif pid < 200000:
                    building = self.env['nhs.estate.building'].browse(pid - 100000)
                    children_ids.extend([200000 + f.id for f in building.floor_ids])
                elif pid < 300000:
                    floor = self.env['nhs.estate.floor'].browse(pid - 200000)
                    children_ids.extend([300000 + s.id for s in floor.space_ids])
            return children_ids
        if site_id_filter:
            root_site = self.browse(site_id_filter)
            if root_site.exists():
                descendant_sites = self.search([('id', 'child_of', root_site.id)])
                result_ids = list(descendant_sites.ids)
                for site in descendant_sites:
                    buildings = self.env['nhs.estate.building'].search([('site_id', '=', site.id)])
                    for b in buildings:
                        result_ids.append(100000 + b.id)
                        floors = self.env['nhs.estate.floor'].search([('building_id', '=', b.id)])
                        for f in floors:
                            result_ids.append(200000 + f.id)
                            spaces = self.env['nhs.estate.space'].search([('floor_id', '=', f.id)])
                            for s in spaces:
                                result_ids.append(300000 + s.id)
                return result_ids
        site_domain = [('active', '=', True)]
        if site_id_filter:
            site_domain.append(('id', 'child_of', site_id_filter))
        if op_status_filter:
            site_domain.append(('operational_status', '=', op_status_filter))
        if site_type_filter:
            site_domain.append(('site_type', '=', site_type_filter))
        if has_backlog_filter:
            site_domain.append(('total_backlog', '>', 0))
        if search_terms:
            term_domain = ['|'] * (len(search_terms) - 1)
            for term in search_terms:
                term_domain.append('|')
                term_domain.append(('name', 'ilike', term))
                term_domain.append(('code', 'ilike', term))
            site_domain.extend(term_domain)
        matching_sites = self.env['nhs.estate.site'].search(site_domain)
        result_ids = set()
        for site in matching_sites:
            curr = site
            while curr:
                result_ids.add(curr.id)
                curr = curr.parent_id
        b_domain = []
        if site_id_filter:
            b_domain.append(('site_id', 'child_of', site_id_filter))
        if op_status_filter:
            b_domain.append(('operational_status', '=', op_status_filter))
        if search_terms:
            term_domain = ['|'] * (len(search_terms) - 1)
            for term in search_terms:
                term_domain.append('|')
                term_domain.append(('name', 'ilike', term))
                term_domain.append(('code', 'ilike', term))
            b_domain.extend(term_domain)
        matching_buildings = self.env['nhs.estate.building'].search(b_domain)
        for b in matching_buildings:
            if b.site_id:
                result_ids.add(100000 + b.id)
                curr = b.site_id
                while curr:
                    result_ids.add(curr.id)
                    curr = curr.parent_id
        f_domain = []
        if site_id_filter:
            f_domain.append(('building_id.site_id', 'child_of', site_id_filter))
        if search_terms:
            term_domain = ['|'] * (len(search_terms) - 1)
            for term in search_terms:
                term_domain.append(('name', 'ilike', term))
            f_domain.extend(term_domain)
        matching_floors = self.env['nhs.estate.floor'].search(f_domain)
        for f in matching_floors:
            if f.building_id and f.building_id.site_id:
                result_ids.add(200000 + f.id)
                result_ids.add(100000 + f.building_id.id)
                curr = f.building_id.site_id
                while curr:
                    result_ids.add(curr.id)
                    curr = curr.parent_id
        s_domain = []
        if site_id_filter:
            s_domain.append(('floor_id.building_id.site_id', 'child_of', site_id_filter))
        if search_terms:
            term_domain = ['|'] * (len(search_terms) - 1)
            for term in search_terms:
                term_domain.append('|')
                term_domain.append(('name', 'ilike', term))
                term_domain.append(('code', 'ilike', term))
            s_domain.extend(term_domain)
        matching_spaces = self.env['nhs.estate.space'].search(s_domain)
        for s in matching_spaces:
            if s.floor_id and s.floor_id.building_id and s.floor_id.building_id.site_id:
                result_ids.add(300000 + s.id)
                result_ids.add(200000 + s.floor_id.id)
                result_ids.add(100000 + s.floor_id.building_id.id)
                curr = s.floor_id.building_id.site_id
                while curr:
                    result_ids.add(curr.id)
                    curr = curr.parent_id
        if not search_terms and not op_status_filter and not site_type_filter and not has_backlog_filter:
            if site_id_filter:
                sites = self.env['nhs.estate.site'].search([('id', '=', site_id_filter), ('active', '=', True)])
            else:
                sites = self.env['nhs.estate.site'].search([('parent_id', '=', False), ('active', '=', True)])
            return sites.ids
        return list(result_ids)

    @api.model
    def get_dashboard_metrics(self):
        """Fetch and aggregate metrics for display on the NHS Estate dashboard."""
        from datetime import date, timedelta
        import re
        metrics = {}
        metrics['site_count'] = self.search_count([('active', '=', True)])
        metrics['building_count'] = self.env['nhs.estate.building'].search_count([])
        metrics['floor_count'] = self.env['nhs.estate.floor'].search_count([])
        metrics['space_count'] = self.env['nhs.estate.space'].search_count([])
        metrics['total_backlog'] = sum(self.env['nhs.estate.backlog'].search([]).mapped('cost_estimate'))
        metrics['total_gia'] = sum(self.env['nhs.estate.building'].search([]).mapped('gia'))
        metrics['high_risk_backlog_count'] = self.env['nhs.estate.backlog'].search_count(
            [('risk_category', '=', 'high')])
        metrics['total_backlog_count'] = self.env['nhs.estate.backlog'].search_count([])
        today = date.today()
        one_year_later = today + timedelta(days=365)
        metrics['expiring_tenure_count'] = self.env['nhs.estate.tenure'].search_count([
            '|', '|',
            '&', '&', ('lease_end', '!=', False), ('lease_end', '>=', today), ('lease_end', '<=', one_year_later),
            '&', '&', ('contract_end', '!=', False),('contract_end','>=', today),('contract_end','<=', one_year_later),
            '&', '&', ('break_date', '!=', False), ('break_date', '>=', today), ('break_date', '<=', one_year_later)
        ])
        metrics['poor_condition_buildings_count'] = self.env['nhs.estate.building'].search_count(
            [('latest_condition_grade', '=', 'D')])
        metrics['condition_grades'] = {
            'A': self.env['nhs.estate.building'].search_count([('latest_condition_grade', '=', 'A')]),
            'B': self.env['nhs.estate.building'].search_count([('latest_condition_grade', '=', 'B')]),
            'C': self.env['nhs.estate.building'].search_count([('latest_condition_grade', '=', 'C')]),
            'D': self.env['nhs.estate.building'].search_count([('latest_condition_grade', '=', 'D')]),
            'False': self.env['nhs.estate.building'].search_count([('latest_condition_grade', '=', False)]),
        }
        metrics['backlog_by_risk'] = {
            'high': sum(
                self.env['nhs.estate.backlog'].search([('risk_category', '=', 'high')]).mapped('cost_estimate')),
            'significant': sum(
                self.env['nhs.estate.backlog'].search([('risk_category', '=', 'significant')]).mapped('cost_estimate')),
            'moderate': sum(
                self.env['nhs.estate.backlog'].search([('risk_category', '=', 'moderate')]).mapped('cost_estimate')),
            'low': sum(self.env['nhs.estate.backlog'].search([('risk_category', '=', 'low')]).mapped('cost_estimate'))
        }
        tenure_types = ['freehold', 'leasehold', 'pfi', 'lift', 'nhsps', 'chp', 'licence']
        tenure_breakdown = {}
        for t_type in tenure_types:
            buildings_of_type = self.env['nhs.estate.building'].search([('tenure_type', '=', t_type)])
            tenure_breakdown[t_type] = {
                'count': len(buildings_of_type),
                'gia': sum(buildings_of_type.mapped('gia'))
            }
        metrics['tenure_breakdown'] = tenure_breakdown
        gia_by_function = {}
        buildings = self.env['nhs.estate.building'].search([])
        for b in buildings:
            func_name = b.function_id.name or 'Unassigned'
            gia_by_function[func_name] = gia_by_function.get(func_name, 0) + b.gia
        metrics['gia_by_function'] = [{'name': name, 'gia': gia} for name, gia in gia_by_function.items()]
        current_year = today.year
        years = list(range(current_year - 4, current_year + 2))
        trend_data = []
        for y in years:
            backlogs_in_year = self.env['nhs.estate.backlog'].search(['|', ('target_year', '=', y),
                                                                      ('create_date', '>=', f'{y}-01-01'),
                                                                      ('create_date', '<=', f'{y}-12-31')])
            backlog_cost = sum(backlogs_in_year.mapped('cost_estimate'))
            surveys_in_year = self.env['nhs.estate.condition'].search_count([
                ('survey_date', '>=', f'{y}-01-01'),
                ('survey_date', '<=', f'{y}-12-31')
            ])
            trend_data.append({
                'year': y,
                'backlog_cost': backlog_cost,
                'survey_count': surveys_in_year
            })
        metrics['trend_data'] = trend_data
        nhs_models = ['nhs.estate.site', 'nhs.estate.building', 'nhs.estate.space', 'nhs.estate.tenure',
                      'nhs.estate.condition', 'nhs.estate.backlog']
        recent_messages = self.env['mail.message'].search([
            ('model', 'in', nhs_models),
            ('message_type', '!=', 'notification')
        ], limit=10, order='date desc')
        activities = []
        model_names = {
            'nhs.estate.site': 'Site',
            'nhs.estate.building': 'Building',
            'nhs.estate.space': 'Space',
            'nhs.estate.tenure': 'Tenure',
            'nhs.estate.condition': 'Condition',
            'nhs.estate.backlog': 'Backlog'
        }
        for msg in recent_messages:
            res_id = msg.res_id
            res_name = msg.record_name or ''
            author = msg.author_id.name or 'System'
            body_text = msg.body or ''
            body_text = re.sub(r'<[^>]*>', '', body_text)
            body_text = body_text.strip()
            activities.append({
                'date': msg.date.strftime('%Y-%m-%d %H:%M:%S') if msg.date else '',
                'author': author,
                'body': body_text,
                'model_label': model_names.get(msg.model, 'Estate'),
                'record_name': res_name,
                'res_id': res_id,
                'res_model': msg.model
            })
        metrics['recent_activities'] = activities
        upcoming_leases = self.env['nhs.estate.tenure'].search([
            ('lease_end', '!=', False),
            ('lease_end', '>=', today)
        ], limit=5, order='lease_end asc')
        metrics['upcoming_leases'] = [{
            'id': l.id,
            'name': l.name,
            'building_name': l.building_id.name,
            'lease_end': l.lease_end.strftime('%Y-%m-%d'),
            'days_remaining': (l.lease_end - today).days
        } for l in upcoming_leases]
        lease_expiries_by_month = []
        for i in range(12):
            m_start = today + timedelta(days=30 * i)
            m_end = today + timedelta(days=30 * (i + 1))
            count = self.env['nhs.estate.tenure'].search_count([
                ('lease_end', '!=', False),
                ('lease_end', '>=', m_start),
                ('lease_end', '<', m_end)
            ])
            month_label = m_start.strftime('%b %Y')
            lease_expiries_by_month.append({
                'month': month_label,
                'count': count
            })
        metrics['lease_expiries_by_month'] = lease_expiries_by_month
        overdue_surveys = self.env['nhs.estate.condition'].search([
            ('next_survey_date', '!=', False),
            ('next_survey_date', '<', today)
        ], limit=5, order='next_survey_date asc')
        metrics['overdue_surveys'] = [{
            'id': s.id,
            'name': s.name,
            'building_name': s.building_id.name,
            'next_survey_date': s.next_survey_date.strftime('%Y-%m-%d'),
            'overall_grade': s.overall_grade or 'Unassigned'
        } for s in overdue_surveys]
        metrics['operational_status'] = {
            'operational': self.env['nhs.estate.building'].search_count([('operational_status', '=', 'operational')]),
            'partial': self.env['nhs.estate.building'].search_count([('operational_status', '=', 'partial')]),
            'closed': self.env['nhs.estate.building'].search_count([('operational_status', '=', 'closed')]),
            'disposed': self.env['nhs.estate.building'].search_count([('operational_status', '=', 'disposed')])
        }
        buildings_list = []
        for b in self.env['nhs.estate.building'].search([]):
            buildings_list.append({
                'id': b.id,
                'name': b.name,
                'site_name': b.site_id.name,
                'gia': b.gia,
                'tenure_type': b.tenure_type or 'Unassigned',
                'latest_condition_grade': b.latest_condition_grade or 'Unassessed',
                'backlog_total': b.backlog_total,
                'operational_status': b.operational_status
            })
        metrics['buildings'] = buildings_list
        recent_surveys = self.env['nhs.estate.condition'].search([], limit=5, order='survey_date desc')
        metrics['recent_surveys'] = [{
            'id': s.id,
            'name': s.name,
            'building_name': s.building_id.name,
            'survey_date': s.survey_date.strftime('%Y-%m-%d') if s.survey_date else '',
            'overall_grade': s.overall_grade or 'Unassigned'
        } for s in recent_surveys]
        recent_backlogs = self.env['nhs.estate.backlog'].search([], limit=5, order='create_date desc')
        metrics['recent_backlogs'] = [{
            'id': b.id,
            'name': b.name,
            'building_name': b.building_id.name,
            'risk_category': b.risk_category or 'low',
            'cost_estimate': b.cost_estimate
        } for b in recent_backlogs]
        high_risk_backlogs = self.env['nhs.estate.backlog'].search([('risk_category', '=', 'high')], limit=5,
                                                                   order='create_date desc')
        metrics['high_risk_backlogs'] = [{
            'id': b.id,
            'name': b.name,
            'building_name': b.building_id.name,
            'cost_estimate': b.cost_estimate
        } for b in high_risk_backlogs]
        recent_sites_buildings = []
        recent_sites = self.env['nhs.estate.site'].search([('parent_id', '=', False)], limit=5,
                                                          order='create_date desc')
        for s in recent_sites:
            recent_sites_buildings.append({
                'id': s.id,
                'type': 'Site',
                'name': s.name,
                'create_date': s.create_date.strftime('%Y-%m-%d') if s.create_date else ''
            })
        recent_bldgs = self.env['nhs.estate.building'].search([], limit=5, order='create_date desc')
        for b in recent_bldgs:
            recent_sites_buildings.append({
                'id': b.id,
                'type': 'Building',
                'name': b.name,
                'create_date': b.create_date.strftime('%Y-%m-%d') if b.create_date else ''
            })
        recent_sites_buildings = sorted(recent_sites_buildings, key=lambda x: x['create_date'],
                                        reverse=True)[:5]
        metrics['recent_sites_buildings'] = recent_sites_buildings
        return metrics
