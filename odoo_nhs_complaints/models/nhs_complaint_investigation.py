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


class NhsComplaintInvestigation(models.Model):
    _name = 'nhs.complaint.investigation'
    _description = 'Complaint Investigation Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, readonly=True,
                       copy=False, default='New',
                       help='Auto-generated investigation reference (e.g. CINV/2026/00045).')
    complaint_id = fields.Many2one('nhs.complaint', string='Complaint', required=True,
                                   ondelete='restrict',
                                   help='The complaint this investigation relates to (1:1).')
    company_id = fields.Many2one('res.company', string='Organisation',
                                 related='complaint_id.company_id', store=True)
    lead_investigator_id = fields.Many2one('res.users', string='Lead Investigator', required=True,
                                           tracking=True,
                                           help='The person leading this investigation.')
    department_input_ids = fields.Many2many('res.users', string='Staff Providing Input',
                                            help='Staff asked to provide statements or input for this investigation.')
    points_of_complaint = fields.Text(string='Points of Complaint',
                                      help='The discrete points raised — each should be answered in the response.')
    chronology = fields.Text(string='Chronology of Events',
                             help='Sequence of events established during investigation.')
    findings = fields.Text(string='Investigation Findings',
                           help='What the investigation found against each point of complaint.')
    upheld_status = fields.Selection([
        ('upheld', 'Upheld'),
        ('partly_upheld', 'Partly Upheld'),
        ('not_upheld', 'Not Upheld'),
    ], string='Overall Outcome', tracking=True,
       help='The overall investigation outcome; feeds reporting and PHSO tracking.')
    lessons_learned = fields.Text(string='Lessons Learned',
                                  help='Learning identified; feeds corrective actions and the board pack.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
    ], string='Status', required=True, default='draft', tracking=True)
    action_ids = fields.One2many('nhs.action', 'investigation_id', string='Actions',
                                 help='Corrective/preventive actions arising from this investigation.')
    linked_incident_ids = fields.Many2many('nhs.incident', related='complaint_id.linked_incident_ids', readonly=False, string='Linked Incidents')
    linked_risk_ids = fields.Many2many('nhs.risk', related='complaint_id.linked_risk_ids', readonly=False, string='Linked Risks')

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('nhs.complaint.investigation') or 'New'
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'complete'})

    def action_create_incident(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Link / Create Incident',
            'res_model': 'nhs.complaint.link.incident.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_complaint_id': self.complaint_id.id},
        }
