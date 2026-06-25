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
from odoo.exceptions import UserError


class NhsComplaintEscalateWizard(models.TransientModel):
    _name = 'nhs.complaint.escalate.wizard'
    _description = 'PALS Concern → Formal Complaint Escalation Wizard'

    pals_id = fields.Many2one('nhs.complaint', string='PALS Concern',
                              domain=[('record_type', '=', 'pals')], required=True,
                              help='The PALS concern being escalated to a formal complaint.')
    subject_summary = fields.Char(string='Complaint Summary', required=True)
    description = fields.Text(string='Complaint Narrative', required=True)
    severity = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('major', 'Major'),
    ], string='Severity / Complexity', required=True, default='medium')
    timescale_id = fields.Many2one('nhs.complaint.timescale', string='Initial Response Timescale',
                                   required=True)
    complainant_id = fields.Many2one('nhs.complainant', string='Complainant')
    subject_id = fields.Many2one('nhs.complaint.subject', string='KO41a Subject', required=True)

    @api.onchange('pals_id')
    def _onchange_pals_id(self):
        if self.pals_id:
            self.subject_summary = self.pals_id.subject_summary
            self.description = self.pals_id.description
            self.complainant_id = self.pals_id.complainant_id
            self.subject_id = self.pals_id.subject_id

    def action_escalate(self):
        self.ensure_one()
        pals = self.pals_id
        if pals.record_type != 'pals':
            raise UserError('This record is not a PALS concern.')
        if pals.state in ('escalated', 'closed', 'withdrawn'):
            raise UserError(f'Cannot escalate a concern in state: {pals.state}.')

        seq = self.env['ir.sequence'].next_by_code('nhs.complaint.formal') or 'New'
        complaint = self.env['nhs.complaint'].with_context(nhs_workflow=True).create({
            'record_type': 'complaint',
            'name': seq,
            'subject_summary': self.subject_summary,
            'description': self.description,
            'severity': self.severity,
            'timescale_id': self.timescale_id.id,
            'complainant_id': self.complainant_id.id if self.complainant_id else False,
            'subject_id': self.subject_id.id,
            'location_id': pals.location_id.id if pals.location_id else False,
            'received_at': pals.received_at,
            'received_via': pals.received_via,
            'pals_origin_ref': pals.name,
            'company_id': pals.company_id.id,
            'handler_id': pals.handler_id.id if pals.handler_id else False,
            'is_third_party': pals.is_third_party,
            'consent_status': pals.consent_status,
            'patient_name': pals.patient_name,
        })

        pals.with_context(nhs_workflow=True).write({'state': 'escalated'})
        pals.message_post(body=f'Escalated to formal complaint: <a href="/web#id={complaint.id}&model=nhs.complaint">{complaint.name}</a>')

        return {
            'type': 'ir.actions.act_window',
            'name': 'New Formal Complaint',
            'res_model': 'nhs.complaint',
            'res_id': complaint.id,
            'view_mode': 'form',
            'target': 'current',
        }
