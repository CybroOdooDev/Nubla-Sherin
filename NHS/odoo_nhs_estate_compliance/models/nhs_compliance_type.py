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

class NHSComplianceType(models.Model):
    """Model to define compliance types including frequency parameters, lead time warnings, and criticality."""
    _name = 'nhs.compliance.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A specific recurring statutory test/inspection within a discipline'
    _order = 'discipline_id, name'

    name = fields.Char(string='Test Name', required=True,
                    help='The descriptive name of the statutory test or inspection (e.g. Legionella Risk Assessment).')
    discipline_id = fields.Many2one('nhs.compliance.discipline', string='Discipline', required=True,
                                    ondelete='restrict',help='The compliance discipline this test type belongs to.')
    htm_reference = fields.Char(string='HTM Reference', help='Specific HTM/standard reference for this test')
    default_frequency_value = fields.Integer(string='Frequency Value', required=True, default=1,
                            help='The default numeric interval between recurring tests (e.g. 6 for every 6 months).')
    default_frequency_unit = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('year', 'Year')
    ], string='Frequency Unit', required=True, default='month',
       help='The time unit for the default recurrence interval (day, week, month, or year).')
    is_statutory = fields.Boolean(string='Statutory', default=True,
                                  help='True = statutory duty; False = advisory/good-practice',required=True)
    criticality = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('life_safety', 'Life Safety')
    ], string='Criticality', default='medium',
       help='The risk criticality level of this compliance type; life-safety items receive the highest priority.')
    default_lead_days = fields.Integer(string='Default Lead Days', default=14, help='Default "due soon" amber window')
    requires_certificate = fields.Boolean(string='Requires Certificate', default=False,
                help='If checked, tests of this type must include a certificate reference and supporting documents.')
    active = fields.Boolean(string='Active', default=True,
                            help='Uncheck to archive this compliance type without deleting it.')
    item_ids = fields.One2many('nhs.compliance.item', 'compliance_type_id', string='Items',
                               help='All compliance items that use this test type definition.')
    item_count = fields.Integer(string='Live Items', compute='_compute_item_count',
                                help='The number of active compliance items using this test type.')

    @api.depends('item_ids')
    def _compute_item_count(self):
        """Compute the number of active compliance items linked to this type."""
        for comp_type in self:
            comp_type.item_count = len(comp_type.item_ids.filtered(lambda i: i.active))
