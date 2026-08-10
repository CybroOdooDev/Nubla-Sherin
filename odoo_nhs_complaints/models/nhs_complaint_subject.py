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


class NhsComplaintSubject(models.Model):
    _name = 'nhs.complaint.subject'
    _description = 'Complaint Subject (KO41a-aligned, two-level)'
    _parent_store = True
    _parent_name = 'parent_id'
    _order = 'complete_name'

    name = fields.Char(string='Subject', required=True,
                       help='Subject or sub-subject (e.g. Communication / Communication with relatives).')
    parent_id = fields.Many2one('nhs.complaint.subject', string='Parent Subject',
                                index=True, ondelete='restrict')
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many('nhs.complaint.subject', 'parent_id', string='Sub-subjects')
    complete_name = fields.Char(string='Full Name', compute='_compute_complete_name',
                                store=True, recursive=True)
    ko41a_code = fields.Char(string='KO41a Code',
                             help='The KO41a return field/category this subject maps to — makes the annual return automatic.')
    provider_types = fields.Char(string='Provider Types',
                                 help='Comma-separated provider_type keys this subject applies to; empty = universal.')
    active = fields.Boolean(default=True, string='Active')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f'{rec.parent_id.complete_name} / {rec.name}'
            else:
                rec.complete_name = rec.name

    @api.constrains('parent_id')
    def _check_two_levels(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.parent_id:
                raise ValidationError('Complaint subjects are limited to two levels (subject and sub-subject).')

    def name_get(self):
        return [(rec.id, rec.complete_name) for rec in self]
