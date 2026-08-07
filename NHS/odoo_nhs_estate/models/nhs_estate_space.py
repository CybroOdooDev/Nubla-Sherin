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

class NHSESSpace(models.Model):
    _name = 'nhs.estate.space'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Functional space / room'
    _order = 'floor_id, name'

    name = fields.Char(
        string='Space Name',
        required=True,
        tracking=True,
        help="Name or label for the space/room (e.g., 'Ward 3A', 'Theatre 2', 'Admin Office 101')"
    )
    code = fields.Char(
        string='Space Reference',
        tracking=True,
        help="Unique reference code or identifier for the space (e.g., room number, asset code)"
    )
    floor_id = fields.Many2one(
        'nhs.estate.floor',
        string='Floor',
        required=True,
        ondelete='restrict',
        help="The floor on which this space is located"
    )
    building_id = fields.Many2one(
        'nhs.estate.building',
        string='Building',
        related='floor_id.building_id',
        store=True,
        help="Building containing this space (inherited from floor)"
    )
    site_id = fields.Many2one(
        'nhs.estate.site',
        string='Site',
        related='floor_id.site_id',
        store=True,
        help="Site where this space is located (inherited from floor)"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='floor_id.company_id',
        store=True,
        help="Company associated with this space (inherited from floor)"
    )
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True,
        help="Full hierarchical name showing the complete location path (e.g., 'Building > Floor > Space')"
    )
    function_id = fields.Many2one(
        'nhs.estate.function',
        string='Function/Use',
        help="Primary function or use type of the space (e.g., clinical, administrative, storage)"
    )
    is_clinical = fields.Boolean(
        string='Clinical',
        compute='_compute_is_clinical',
        store=True,
        readonly=False,
        help="Indicates whether this space is clinical/patient-facing (true) or non-clinical (false)"
    )
    space_type = fields.Selection([
        ('ward', 'Ward'),
        ('theatre', 'Theatre'),
        ('office', 'Office'),
        ('store', 'Store'),
        ('plant', 'Plant'),
        ('circulation', 'Circulation'),
        ('clinical_room', 'Clinical Room'),
        ('wc', 'WC'),
        ('other', 'Other')
    ], string='Space Type',
        help="Category/type classification of the space (e.g., Ward, Theatre, Office)"
    )
    area = fields.Float(
        string='Area (m²)',
        help="Floor area of the space in square meters"
    )
    capacity = fields.Integer(
        string='Capacity',
        help="Maximum occupancy or capacity of the space (e.g., number of beds, people, or equipment)"
    )
    department = fields.Char(
        string='Department/Service',
        help="Department, service, or clinical specialty that occupies the space"
    )
    utilisation = fields.Selection([
        ('empty', 'Empty'),
        ('under', 'Under-utilised'),
        ('full', 'Fully Utilised'),
        ('over', 'Over-utilised')
    ], string='Occupancy/Utilisation Status',
        help="Current occupancy and utilisation level of the space"
    )
    cost_centre = fields.Char(
        string='Cost Centre Reference',
        help="Financial cost centre reference code for budget tracking"
    )
    notes = fields.Text(
        string='Notes',
        help="Additional information, observations, or special requirements for the space"
    )
    active = fields.Boolean(
        default=True,
        help="Whether this space record is active and visible in the system"
    )
    occupancy_status = fields.Selection([
        ('occupied', 'Occupied'),
        ('vacant', 'Vacant'),
    ], string='Occupancy Status',
        compute='_compute_occupancy_status',
        store=True,
        help='Current occupancy status of the space (auto-calculated from utilisation)')
    is_occupied = fields.Boolean(
        string='Is Occupied',
        compute='_compute_occupancy_status',
        store=True,
        help='True if space is currently occupied'
    )

    @api.depends('utilisation')
    def _compute_occupancy_status(self):
        """Auto-determine occupancy from utilisation field"""
        for record in self:
            if record.utilisation in ['empty', 'under']:
                record.occupancy_status = 'vacant'
                record.is_occupied = False
            elif record.utilisation in ['full', 'over']:
                record.occupancy_status = 'occupied'
                record.is_occupied = True
            else:
                record.occupancy_status = 'vacant'
                record.is_occupied = False

    @api.depends('site_id.name', 'building_id.name', 'floor_id.name', 'name')
    def _compute_complete_name(self):
        """Compute the full hierarchical name/location path for this space.
        Joins parent site, building, floor, and space name with ' / ' delimiters
        to produce a complete location reference string.
        """
        for record in self:
            parts = []
            if record.site_id and record.site_id.name:
                parts.append(record.site_id.name)
            if record.building_id and record.building_id.name:
                parts.append(record.building_id.name)
            if record.floor_id and record.floor_id.name:
                parts.append(record.floor_id.name)
            if record.name:
                parts.append(record.name)
            record.complete_name = ' / '.join(parts) if parts else record.name

    @api.depends('function_id.is_clinical')
    def _compute_is_clinical(self):
        """Check and store if the space is used for clinical purposes.
        Determines clinical status based on the is_clinical field of the
        assigned estate function category.
        """
        for record in self:
            if record.function_id:
                record.is_clinical = record.function_id.is_clinical
            else:
                record.is_clinical = False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to assign a sequence code if not explicitly provided.
        Args:
            vals_list (list of dicts): Values for record creation.
        Returns:
            recordset: Newly created space records.
        """
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('nhs.estate.space')
        return super().create(vals_list)

    def action_view_documents(self):
        """Return an action to display all attachments/documents linked to this space.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.estate.space'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.estate.space',
                'default_res_id': self.id,
            }
        }

    @api.model
    def get_import_templates(self):
        """Provide standard templates available for importing spaces.
        Returns a list of dicts specifying labels and template asset file paths.
        """
        return [{
            'label': 'Import Template for Space',
            'template': '/odoo_nhs_estate/static/import_templates/space.xlsx',
        }]
