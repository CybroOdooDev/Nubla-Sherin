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


class NhsActionComplaintsExtension(models.Model):
    _inherit = 'nhs.action'

    complaint_id = fields.Many2one('nhs.complaint', string='Source Complaint',
                                   ondelete='restrict',
                                   help='Complaint this action was raised from.')
    phso_id = fields.Many2one('nhs.complaint.phso', string='Source PHSO Record',
                              ondelete='restrict',
                              help='PHSO recommendation this action was raised from (complaint_id still set for rollup).')

    @api.constrains('incident_id', 'investigation_id', 'risk_id', 'complaint_id')
    def _check_single_parent(self):
        for rec in self:
            parents = (
                bool(rec.incident_id)
                + bool(getattr(rec, 'investigation_id', False))
                + bool(rec.risk_id)
                + bool(rec.complaint_id)
            )
            if parents > 1:
                # Allow investigation linked to its own incident
                if rec.incident_id and getattr(rec, 'investigation_id', False) and not rec.risk_id and not rec.complaint_id:
                    if rec.investigation_id.incident_id == rec.incident_id:
                        continue
                raise ValidationError('An action can only be linked to one parent source record.')

    @api.constrains('complaint_id', 'phso_id', 'investigation_id')
    def _check_parent_record_state(self):
        for rec in self:
            if rec.complaint_id and rec.complaint_id.state in ('closed', 'withdrawn', 'resolved', 'escalated'):
                raise ValidationError('Cannot create or modify actions on a closed complaint or PALS concern.')
            if rec.phso_id and rec.phso_id.state != 'decision_made':
                raise ValidationError('Actions can only be created or modified on a PHSO record in the "Decision Made" state.')
            if rec.investigation_id:
                comp_inv = self.env['nhs.complaint.investigation'].search([('id', '=', rec.investigation_id.id)], limit=1)
                if comp_inv and comp_inv.state == 'complete':
                    raise ValidationError('Cannot create or modify actions on a completed investigation.')
