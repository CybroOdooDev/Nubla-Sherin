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


class NhsIncidentComplaintsExtension(models.Model):
    """Extends nhs.incident with fields linking an incident to the complaints it originated from or relates to."""
    _inherit = 'nhs.incident'

    complaint_ids = fields.Many2many(
        'nhs.complaint',
        'nhs_complaint_incident_rel', 'incident_id', 'complaint_id',
        string='Linked Complaints',
        help='Complaints linked to this incident (inverse of nhs.complaint.linked_incident_ids).',
    )
    complaint_count = fields.Integer(string='Complaints', compute='_compute_complaint_count')

    @api.depends('complaint_ids')
    def _compute_complaint_count(self):
        """Set the count of complaints linked to this incident."""
        for rec in self:
            rec.complaint_count = len(rec.complaint_ids)

    def action_view_complaints(self):
        """Open the list/form view of complaints linked to this incident."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Linked Complaints',
            'res_model': 'nhs.complaint',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.complaint_ids.ids)],
            'context': {'default_linked_incident_ids': [(4, self.id)]},
        }

    def action_create_complaint_from_incident(self):
        """Open a new complaint form pre-filled with this incident's location, description and link."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Complaint from Incident',
            'res_model': 'nhs.complaint',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_record_type': 'complaint',
                'default_linked_incident_ids': [(4, self.id)],
                'default_location_id': self.location_id.id,
                'default_description': self.description or '',
            },
        }
