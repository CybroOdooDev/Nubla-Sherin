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
from odoo.exceptions import UserError


class NhsComplaintLinkIncidentWizard(models.TransientModel):
    """Wizard to link an existing incident to a complaint or create a new incident from a complaint."""
    _name = 'nhs.complaint.link.incident.wizard'
    _description = 'Link or Create Incident from Complaint Wizard'

    complaint_id = fields.Many2one('nhs.complaint', string='Complaint', required=True)
    action = fields.Selection([
        ('link', 'Link an Existing Incident'),
        ('create', 'Create a New Incident from this Complaint'),
    ], string='Action', required=True, default='link')
    incident_ids = fields.Many2many('nhs.incident', string='Incidents to Link',
                                    domain="[('id', 'not in', existing_incident_ids)]")
    existing_incident_ids = fields.Many2many('nhs.incident', string='Already Linked',
                                             related='complaint_id.linked_incident_ids',
                                             readonly=True)
    new_incident_description = fields.Text(string='What Happened')
    new_incident_occurred_at = fields.Datetime(
        string='Date/Time of Incident', default=fields.Datetime.now)
    new_incident_location_id = fields.Many2one(
        'nhs.location', string='Location',
        help='Ward, department or site where the incident occurred.')
    new_incident_category_id = fields.Many2one(
        'nhs.incident.category', string='Category',
        help='Incident category for reporting and trend analysis.')

    @api.onchange('complaint_id')
    def _onchange_complaint_id(self):
        """Pre-fill the new-incident description and location from the selected complaint."""
        if self.complaint_id:
            self.new_incident_description = self.complaint_id.description
            self.new_incident_location_id = self.complaint_id.location_id

    def action_confirm(self):
        """Link the selected incidents to the complaint, or create a new incident from the entered details and link it."""
        self.ensure_one()
        complaint = self.complaint_id

        if self.action == 'link':
            if not self.incident_ids:
                raise UserError('Please select at least one incident to link.')
            complaint.write({'linked_incident_ids': [(4, inc.id) for inc in self.incident_ids]})

        else:
            if not self.new_incident_location_id:
                raise UserError('Please select a location for the new incident.')
            if not self.new_incident_category_id:
                raise UserError('Please select a category for the new incident.')
            if not self.new_incident_occurred_at:
                raise UserError('Please enter the date and time of the incident.')

            incident = self.env['nhs.incident'].create({
                'incident_kind': 'incident',
                'occurred_at': self.new_incident_occurred_at,
                'reported_at': fields.Datetime.now(),
                'description': self.new_incident_description or complaint.description or '(See linked complaint)',
                'location_id': self.new_incident_location_id.id,
                'category_id': self.new_incident_category_id.id,
                'company_id': complaint.company_id.id,
                'harm_grade': 'no_harm',
            })
            complaint.write({'linked_incident_ids': [(4, incident.id)]})
            return {
                'type': 'ir.actions.act_window',
                'name': 'New Incident',
                'res_model': 'nhs.incident',
                'res_id': incident.id,
                'view_mode': 'form',
                'target': 'current',
            }

        return {'type': 'ir.actions.act_window_close'}
