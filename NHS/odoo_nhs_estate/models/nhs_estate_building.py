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

class NHSESBuilding(models.Model):
    _name = 'nhs.estate.building'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Building or block within a site'
    _order = 'site_id, name'

    name = fields.Char(
        string='Building Name',
        required=True,
        tracking=True,
        help="Official name of the building for identification purposes"
    )
    code = fields.Char(
        string='Building Reference',
        required=True,
        tracking=True,
        help="Unique reference code or identifier for the building (e.g., asset code)"
    )
    site_id = fields.Many2one(
        'nhs.estate.site',
        string='Site',
        required=True,
        ondelete='restrict',
        help="The site/location where the building is situated"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='site_id.company_id',
        store=True,
        help="Company associated with the building (inherited from site)"
    )
    build_year = fields.Integer(
        string='Build Year',
        help="Year the building was originally constructed"
    )
    age_years = fields.Integer(
        string='Age (years)',
        compute='_compute_age',
        help="Age of the building in years (auto-calculated from build year)"
    )
    storeys = fields.Integer(
        string='Number of Storeys',
        help="Total number of floors/levels in the building"
    )
    gia = fields.Float(
        string='Gross Internal Area (m²)',
        compute='_compute_areas',
        store=True,
        help="Total Gross Internal Area in square meters (auto-calculated from floor areas)"
    )
    nia = fields.Float(
        string='Net Internal Area (m²)',
        help="Net Internal Area in square meters (usable space)"
    )
    tenure_id = fields.Many2one(
        'nhs.estate.tenure',
        string='Tenure',
        domain="[('building_id', '=', id)]",
        help="Land/property tenure arrangement for the building"
    )
    tenure_type = fields.Selection(
        related='tenure_id.tenure_type',
        string='Tenure Type',
        store=True,
        help="Type of tenure (inherited from tenure record)"
    )
    function_id = fields.Many2one(
        'nhs.estate.function',
        string='Predominant Function',
        help="Main primary use or function of the building"
    )
    construction_type = fields.Char(
        string='Construction Type/Method',
        help="Building construction method or structural type (e.g., steel frame, concrete)"
    )
    is_listed = fields.Boolean(
        string='Listed Building',
        help="Whether the building has protected/heritage status (listed status)"
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
        help="Current operational state of the building"
    )
    last_refurb_date = fields.Date(
        string='Last Major Refurbishment',
        help="Date of the most significant refurbishment or renovation work"
    )
    floor_ids = fields.One2many(
        'nhs.estate.floor',
        'building_id',
        string='Floors',
        help="List of floors associated with this building"
    )
    floor_count = fields.Integer(
        string='Floor Count',
        compute='_compute_floor_count',
        store=True,
        help="Total number of floors in the building (auto-calculated)"
    )
    space_count = fields.Integer(
        string='Space Count',
        compute='_compute_space_count',
        store=True,
        help="Total number of spaces/rooms across all floors (auto-calculated)"
    )
    condition_ids = fields.One2many(
        'nhs.estate.condition',
        'building_id',
        string='Condition Surveys',
        help="Historical condition survey records for the building"
    )
    condition_count = fields.Integer(
        string='Condition Survey Count',
        compute='_compute_condition_count',
        store=True,
        help="Number of condition surveys conducted (auto-calculated)"
    )
    latest_condition_grade = fields.Selection([
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Fair'),
        ('D', 'D - Poor')
    ], string='Latest Condition Grade',
        compute='_compute_latest_condition_grade',
        store=True,
        help="Most recent condition grade awarded to the building"
    )
    backlog_ids = fields.One2many(
        'nhs.estate.backlog',
        'building_id',
        string='Backlog Items',
        help="List of backlog maintenance items for this building"
    )
    backlog_count = fields.Integer(
        string='Backlog Count',
        compute='_compute_backlog_count',
        store=True,
        help="Total number of backlog items for this building (auto-calculated)"
    )
    backlog_total = fields.Monetary(
        string='Backlog Total',
        currency_field='currency_id',
        compute='_compute_backlog_total',
        store=True,
        help="Total estimated cost of all backlog items for this building"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help="Currency used for financial values (defaults to company currency)"
    )
    image = fields.Many2many(
        'ir.attachment',
        'nhs_estate_building_image_rel',
        'building_id', 'attachment_id',
        string='Building Photos and Floor Plan',
        help="Main photographs or images of the building"
    )
    active = fields.Boolean(
        default=True,
        help="Whether this building record is active and visible in the system"
    )
    clinical_area = fields.Float(
        string='Clinical Area (m²)',
        compute='_compute_analysis',
        store=True,
        help='Total area of clinical spaces'
    )
    non_clinical_area = fields.Float(
        string='Non-Clinical Area (m²)',
        compute='_compute_analysis',
        store=True,
        help='Total area of non-clinical spaces'
    )
    occupied_area = fields.Float(
        string='Occupied Area (m²)',
        compute='_compute_analysis',
        store=True,
        help='Total area of occupied spaces (full/over utilisation)'
    )
    vacant_area = fields.Float(
        string='Vacant Area (m²)',
        compute='_compute_analysis',
        store=True,
        help='Total area of vacant spaces (empty/under utilisation)'
    )

    _unique_code = models.Constraint(
        'UNIQUE(code)',
        'The code must be unique!'
    )

    @api.depends('floor_ids.space_ids.area', 'floor_ids.space_ids.is_clinical',
                 'floor_ids.space_ids.is_occupied')
    def _compute_analysis(self):
        """Compute all area analytics"""
        for building in self:
            spaces = self.env['nhs.estate.space'].search([
                ('building_id', '=', building.id)
            ])
            clinical = 0.0
            non_clinical = 0.0
            occupied = 0.0
            vacant = 0.0
            for space in spaces:
                area = space.area or 0.0
                if space.is_clinical:
                    clinical += area
                else:
                    non_clinical += area

                if space.is_occupied:
                    occupied += area
                else:
                    vacant += area
            building.clinical_area = clinical
            building.non_clinical_area = non_clinical
            building.occupied_area = occupied
            building.vacant_area = vacant

    @api.depends('build_year')
    def _compute_age(self):
        """Calculate the age of the building in years.
        Computes the difference between the current calendar year and the building's
        construction year (build_year).
        """
        current_year = fields.Date.today().year
        for record in self:
            if record.build_year:
                record.age_years = max(0, current_year - record.build_year)
            else:
                record.age_years = 0

    @api.onchange('build_year')
    def _check_build_year(self):
        """Ensure the build year is not in the future.
        Raises:
            ValidationError: If the build_year is greater than the current year.
        """
        current_year = fields.Date.today().year
        for record in self:
            if record.build_year and record.build_year > current_year:
                raise ValidationError("The build year cannot be in the future.")

    @api.depends('floor_ids')
    def _compute_floor_count(self):
        """Compute the total number of floors/levels defined in this building.
        Counts the associated floor records for each building.
        """
        for record in self:
            record.floor_count = len(record.floor_ids)

    @api.depends('floor_ids.space_ids')
    def _compute_space_count(self):
        """Compute the total number of spaces/rooms across all floors of the building.
        Aggregates space counts from all associated floor levels.
        """
        for record in self:
            count = 0
            for floor in record.floor_ids:
                count += len(floor.space_ids)
            record.space_count = count

    @api.depends('condition_ids')
    def _compute_condition_count(self):
        """Compute the total count of condition survey records for the building.
        Counts the linked condition survey records.
        """
        for record in self:
            record.condition_count = len(record.condition_ids)

    @api.depends('backlog_ids')
    def _compute_backlog_count(self):
        """Compute the total count of backlog maintenance items for this building.
        Counts the associated backlog records.
        """
        for record in self:
            record.backlog_count = len(record.backlog_ids)

    @api.depends('condition_ids.survey_date', 'condition_ids.overall_grade')
    def _compute_latest_condition_grade(self):
        """Determine the latest condition survey grade for this building.
        Retrieves the overall grade from the most recent condition survey sorted by survey date.
        """
        for record in self:
            latest_survey = record.condition_ids.sorted('survey_date', reverse=True)[:1]
            record.latest_condition_grade = latest_survey.overall_grade if latest_survey else False

    @api.depends('backlog_ids.cost_estimate')
    def _compute_backlog_total(self):
        """Compute the total cost of all backlog maintenance items for the building.
        Sums up the estimated costs of all associated backlog records.
        """
        for record in self:
            record.backlog_total = sum(record.backlog_ids.mapped('cost_estimate'))

    @api.depends('floor_ids.gia', 'nia')
    def _compute_areas(self):
        """Compute the Gross Internal Area (GIA) of the building.
        Sums the GIA of all associated floors and adds the Net Internal Area (NIA) if specified.
        """
        for record in self:
            if record.nia > 0:
                total = sum(floor.gia for floor in record.floor_ids if floor.gia)
                record.gia = total + record.nia
            else:
                record.gia = sum(floor.gia for floor in record.floor_ids if floor.gia)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to assign a sequence code if not explicitly provided.
        Args:
            vals_list (list of dicts): Values for record creation.
        Returns:
            recordset: Newly created building records.
        """
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('nhs.estate.building')
        return super().create(vals_list)

    def action_view_floors(self):
        """Return an action to display all floors associated with this building.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Floors',
            'res_model': 'nhs.estate.floor',
            'view_mode': 'list,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id}
        }

    def action_view_tenure(self):
        """Return an action to display all tenure/lease records associated with this building.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tenure',
            'res_model': 'nhs.estate.tenure',
            'view_mode': 'list,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id}
        }

    def action_view_conditions(self):
        """Return an action to display all condition surveys conducted for this building.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Condition Surveys',
            'res_model': 'nhs.estate.condition',
            'view_mode': 'list,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id}
        }

    def action_view_backlog(self):
        """Return an action to display all backlog maintenance items for this building.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Backlog Items',
            'res_model': 'nhs.estate.backlog',
            'view_mode': 'list,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id}
        }

    def action_view_spaces_from_building(self):
        """Return an action to display all spaces/rooms within this building.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Spaces',
            'res_model': 'nhs.estate.space',
            'view_mode': 'list,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id}
        }

    def action_view_documents(self):
        """Return an action to display all attachments/documents linked to this building.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.estate.building'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.estate.building',
                'default_res_id': self.id,
            }
        }

    @api.model
    def get_import_templates(self):
        """Provide standard templates available for importing buildings.
        Returns a list of dicts specifying labels and template asset file paths.
        """
        return [{
            'label': 'Import Template for Building',
            'template': '/odoo_nhs_estate/static/import_templates/building.xlsx',
        }]

    def action_operational(self):
        """Set the building's operational status to 'operational'."""
        self.operational_status = 'operational'

    def action_partial_operational(self):
        """Set the building's operational status to 'partial' operational."""
        self.operational_status = 'partial'

    def action_closed(self):
        """Set the building's operational status to 'closed'."""
        self.operational_status = 'closed'

    def action_disposed(self):
        """Set the building's operational status to 'disposed'."""
        self.operational_status = 'disposed'
