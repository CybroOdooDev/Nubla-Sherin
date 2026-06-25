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
#############################################################################
from odoo import api, fields, models


class NhsComplaintLinkIncidentWizard(models.TransientModel):
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
    # Pre-fill fields for new incident
    new_incident_description = fields.Text(string='Incident Description')
    new_incident_occurred_at = fields.Datetime(string='Incident Date/Time',
                                               default=fields.Datetime.now)

    @api.onchange('complaint_id')
    def _onchange_complaint_id(self):
        if self.complaint_id:
            self.new_incident_description = self.complaint_id.description

    def action_confirm(self):
        self.ensure_one()
        complaint = self.complaint_id
        if self.action == 'link':
            complaint.write({'linked_incident_ids': [(4, inc.id) for inc in self.incident_ids]})
            for incident in self.incident_ids:
                incident.write({'complaint_ids': [(4, complaint.id)]})
        else:
            incident = self.env['nhs.incident'].create({
                'incident_kind': 'incident',
                'occurred_at': self.new_incident_occurred_at,
                'reported_at': fields.Datetime.now(),
                'description': self.new_incident_description or complaint.description,
                'location_id': complaint.location_id.id if complaint.location_id else False,
                'company_id': complaint.company_id.id,
                'harm_grade': 'no_harm',
                'category_id': self.env['nhs.incident.category'].search([], limit=1).id,
            })
            complaint.write({'linked_incident_ids': [(4, incident.id)]})
            incident.write({'complaint_ids': [(4, complaint.id)]})
            return {
                'type': 'ir.actions.act_window',
                'name': 'New Incident',
                'res_model': 'nhs.incident',
                'res_id': incident.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}
