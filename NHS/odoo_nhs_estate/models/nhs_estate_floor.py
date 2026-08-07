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

class NHSESFloor(models.Model):
    _name = 'nhs.estate.floor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Floor / Level'
    _order = 'building_id, sequence'

    name = fields.Char(
        string='Floor Name',
        required=True,
        tracking=True,
        help="Name or label for the floor (e.g., Ground Floor, First Floor, Basement Level 1)"
    )
    building_id = fields.Many2one(
        'nhs.estate.building',
        string='Building',
        required=True,
        ondelete='restrict',
        help="The building to which this floor belongs"
    )
    site_id = fields.Many2one(
        'nhs.estate.site',
        string='Site',
        related='building_id.site_id',
        store=True,
        help="Site where the building and floor are located (inherited from building)"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='building_id.company_id',
        store=True,
        help="Company associated with this floor (inherited from building)"
    )
    sequence = fields.Integer(
        string='Order',
        default=0,
        help='Sort order for displaying floors (basements as negative numbers, ground floor as 0, upper floors '
             'as positive numbers)'
    )
    gia = fields.Float(
        string='Floor Gross Internal Area (m²)',
        compute='_compute_areas',
        store=True,
        help="Gross Internal Area of this floor in square meters (auto-calculated from spaces)"
    )
    function_id = fields.Many2one(
        'nhs.estate.function',
        string='Predominant Function',
        help="Main primary use or function of this floor"
    )
    floor_plan = fields.Many2many(
        'ir.attachment',
        'nhs_estate_floor_floor_plan_rel',
        'floor_id', 'attachment_id',
        string='Floor Plans',
        help="Floor plan diagrams or layouts for this specific floor (upload as image or PDF)"
    )
    space_ids = fields.One2many(
        'nhs.estate.space',
        'floor_id',
        string='Spaces',
        help="List of spaces/rooms contained within this floor"
    )
    space_count = fields.Integer(
        string='Space Count',
        compute='_compute_space_count',
        store=True,
        help="Total number of spaces on this floor (auto-calculated)"
    )
    active = fields.Boolean(
        default=True,
        help="Whether this floor record is active and visible in the system"
    )

    @api.depends('space_ids')
    def _compute_space_count(self):
        """Compute the total count of spaces defined on this floor.
        Counts the associated space/room records for each floor record.
        """
        for record in self:
            record.space_count = len(record.space_ids)

    @api.depends('space_ids.area')
    def _compute_areas(self):
        """Compute the Gross Internal Area (GIA) of the floor.
        Sums up the area fields of all active spaces associated with this floor.
        """
        for record in self:
            record.gia = sum(space.area for space in record.space_ids if space.area)

    def action_view_spaces(self):
        """Return an action to display all spaces/rooms associated with this floor.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Spaces',
            'res_model': 'nhs.estate.space',
            'view_mode': 'list,form',
            'domain': [('floor_id', '=', self.id)],
            'context': {'default_floor_id': self.id}
        }

    def action_view_documents(self):
        """Return an action to display all attachments/documents linked to this floor.
        Ensures a singleton record before returning the action configuration dict.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.estate.floor'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.estate.floor',
                'default_res_id': self.id,
            }
        }

    @api.model
    def get_import_templates(self):
        """Provide standard templates available for importing floors.
        Returns a list of dicts specifying labels and template asset file paths.
        """
        return [{
            'label': 'Import Template for Floor',
            'template': '/odoo_nhs_estate/static/import_templates/floor.xlsx',
        }]
