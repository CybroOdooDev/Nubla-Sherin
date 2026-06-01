# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NhsTrustSpecialty(models.Model):
    _name = 'nhs.trust.specialty'
    _description = 'NHS Clinical Specialty'
    _order = 'name'

    name = fields.Char(
        string='Specialty Name',
        required=True,
        translate=True,
        help="Specialty name (e.g. 'Cardiology', 'Trauma & Orthopaedics', 'Maternity'). Translatable."
    )
    code = fields.Char(
        string='NHS Code',
        help="Optional NHS Data Dictionary specialty code (e.g. '320' for Cardiology, '110' for T&O)."
    )
    description = fields.Text(
        string='Description',
        help="Short description of what the specialty covers."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag."
    )

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Specialty name must be unique!'),
    ]


class NhsTrustSite(models.Model):
    _name = 'nhs.trust.site'
    _description = 'NHS Trust Site / Hospital'
    _inherit = ['mail.thread']
    _order = 'trust_id, name'

    name = fields.Char(
        string='Site Name',
        required=True,
        tracking=True,
        help="Site name (e.g. 'The Royal London Hospital', 'Whipps Cross University Hospital')."
    )
    code = fields.Char(
        string='ODS Sub-Code',
        help="ODS sub-code for the site (e.g. 'RNJ12' is a sub-code of trust RNJ). Used in datasets that drill below trust level."
    )
    trust_id = fields.Many2one(
        'nhs.trust',
        string='Parent Trust',
        required=True,
        ondelete='cascade',
        index=True,
        help="Parent Trust. ondelete='cascade' — deleting the trust cascades to sites."
    )
    site_type = fields.Selection([
        ('acute_hospital', 'Acute Hospital'),
        ('teaching_hospital', 'Teaching Hospital'),
        ('community_hospital', 'Community Hospital'),
        ('mental_health_unit', 'Mental Health Unit'),
        ('clinic', 'Clinic'),
        ('community_centre', 'Community Centre'),
        ('ambulance_station', 'Ambulance Station'),
        ('admin_office', 'Admin Office'),
        ('other', 'Other'),
    ],
        string='Site Type',
        required=True,
        default='acute_hospital',
        help="Drives filtering and reporting. Teaching hospitals are typically the larger university-affiliated sites with research and training roles."
    )

    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    county = fields.Char(string='County')
    zip = fields.Char(string='Postcode')
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env.ref('base.uk', raise_if_not_found=False),
    )
    phone = fields.Char(
        string='Phone',
        help="Site main phone — rendered with phone widget."
    )
    email = fields.Char(
        string='Email',
        help="Site general email."
    )

    # GPS
    latitude = fields.Float(
        string='Latitude',
        digits=(10, 7),
        help="GPS latitude in decimal degrees (e.g. 51.5176 for London Hospital). Reserved for a future map view. 7 decimals = ~11mm precision."
    )
    longitude = fields.Float(
        string='Longitude',
        digits=(10, 7),
        help="GPS longitude (e.g. -0.0598 for London Hospital)."
    )

    site_manager_id = fields.Many2one(
        'res.partner',
        string='Site Manager',
        help="Person responsible for site-level operations (typically a General Manager or Site Director)."
    )

    # A&E
    has_ae_department = fields.Boolean(
        string='Has A&E Department',
        default=False,
        help="Tick if the site has an A&E / Emergency Department. Drives the red 'A&E' badge on kanban cards."
    )
    ae_type = fields.Selection([
        ('type1', 'Type 1 – Major / Consultant-led 24h A&E'),
        ('type2', 'Type 2 – Single Specialty A&E'),
        ('type3', 'Type 3 – Minor Injury Unit / Urgent Care Centre'),
        ('type4', 'Type 4 – Walk-in Centre / Minor Injury Unit'),
    ],
        string='A&E Type',
        help="Only relevant if has_ae_department=True. Type 1: Major 24-hour A&E. Type 2: Single specialty. Type 3: MIU/UCC. Type 4: Walk-in."
    )

    # Capacity
    bed_capacity = fields.Integer(
        string='Bed Capacity',
        default=0,
        help="Total available overnight beds at this site. Summed up to Trust.total_bed_capacity."
    )
    icu_bed_capacity = fields.Integer(
        string='ICU Bed Capacity',
        default=0,
        help="Intensive Care Unit (Level 3 critical care) beds. Subset of bed_capacity."
    )
    operating_theatres = fields.Integer(
        string='Operating Theatres',
        default=0,
        help="Number of operating theatres on site."
    )
    opening_hours = fields.Char(
        string='Opening Hours',
        help="Free-text description (e.g. '24/7', 'Mon-Fri 08:00-18:00'). Not structured because patterns vary widely."
    )

    # Relationships
    specialty_ids = fields.Many2many(
        'nhs.trust.specialty',
        string='Clinical Specialties',
        help="Clinical specialties offered at this site. Helps patients and commissioners find the right site."
    )
    department_ids = fields.One2many(
        'nhs.trust.department',
        'site_id',
        string='Departments',
        help="Departments based at this site (Acute Medicine, Pharmacy, Radiology, etc.)."
    )
    department_count = fields.Integer(
        string='Department Count',
        compute='_compute_department_count',
        help="Count for the stat button."
    )
    notes = fields.Text(
        string='Notes',
        help="Free-text operational notes."
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Archive flag — archive a site rather than delete it to preserve historical data."
    )

    @api.depends('department_ids')
    def _compute_department_count(self):
        for site in self:
            site.department_count = len(site.department_ids)

    def action_view_departments(self):
        self.ensure_one()
        return {
            'name': 'Departments',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.trust.department',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id, 'default_trust_id': self.trust_id.id},
        }
