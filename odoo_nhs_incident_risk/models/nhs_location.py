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


class NhsLocation(models.Model):
    _name = 'nhs.location'
    _description = 'Physical Location (site → unit/ward → room)'
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(string='Name', required=True,
                       help='The short name of this location (e.g. "Ward 7", "Pharmacy", "Main Reception").')
    parent_id = fields.Many2one('nhs.location', string='Parent Location',
                                index=True, ondelete='restrict',
                                help='The parent location in the hierarchy. '
                                     'Supports up to 3 levels: Site → Unit/Ward → Room.')
    parent_path = fields.Char(index=True)
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name',
                                store=True, recursive=True,
                                help='Auto-computed full location path including all parent levels '
                                     '(e.g. "Main Hospital / Ward 7 / Bay 3").')
    location_type = fields.Selection([
        ('site', 'Site'),
        ('unit', 'Unit / Ward'),
        ('room', 'Room'),
        ('external', 'External'),
    ], string='Type', required=True, default='unit',
       help='The level of this location in the hierarchy: Site (top-level campus), '
            'Unit/Ward (department or ward), Room (specific room or bay), '
            'or External (off-site location such as a patient home or ambulance).')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 default=lambda self: self.env.company,
                                 help='The organisation this location belongs to.')
    default_handler_id = fields.Many2one('res.users', string='Default Handler',
                                         help='The staff member automatically assigned as handler for new incidents '
                                              'reported at this location, if no location-specific handler is overridden.')
    active = fields.Boolean(default=True,
                            help='Untick to archive this location. Archived locations are hidden from '
                                 'incident forms but remain on historical records.')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f'{rec.parent_id.complete_name} / {rec.name}'
            else:
                rec.complete_name = rec.name

    @api.constrains('parent_id')
    def _check_depth(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.parent_id and rec.parent_id.parent_id.parent_id:
                raise ValidationError('Locations support a maximum of 3 levels (site → unit → room).')

    def name_get(self):
        return [(r.id, r.complete_name) for r in self]
