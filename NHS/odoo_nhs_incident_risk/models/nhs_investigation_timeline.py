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


class NhsInvestigationTimeline(models.Model):
    """A chronological entry in an incident investigation's timeline."""
    _name = 'nhs.investigation.timeline'
    _description = 'Investigation Chronology Entry'
    _order = 'happened_at'

    investigation_id = fields.Many2one('nhs.investigation', string='Investigation',
                                       required=True, ondelete='cascade',
                                       help='The investigation this chronology entry belongs to.')
    happened_at = fields.Datetime(string='Date / Time', required=True,
                                  help='The exact date and time this event occurred. '
                                       'Entries are sorted chronologically to build the incident timeline.')
    entry = fields.Text(string='Entry', required=True,
                        help='A factual description of what happened at this point in time. '
                             'Avoid opinions or conclusions — record observable facts only.')
    source = fields.Char(string='Evidence Source',
                         help='e.g. Staff statement, CCTV, care notes')
