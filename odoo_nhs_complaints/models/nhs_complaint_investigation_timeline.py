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
from odoo import fields, models


class NhsComplaintInvestigationTimeline(models.Model):
    _name = 'nhs.complaint.investigation.timeline'
    _description = 'Complaint Investigation Chronology Entry'
    _order = 'happened_at'

    investigation_id = fields.Many2one('nhs.complaint.investigation', string='Investigation',
                                       required=True, ondelete='cascade',
                                       help='The investigation this chronology entry belongs to.')
    happened_at = fields.Datetime(string='Date / Time', required=True,
                                  help='The exact date and time this event occurred.')
    entry = fields.Text(string='Entry', required=True,
                        help='A factual description of what happened at this point in time.')
    source = fields.Char(string='Evidence Source',
                         help='e.g. Staff statement, CCTV, care notes')
