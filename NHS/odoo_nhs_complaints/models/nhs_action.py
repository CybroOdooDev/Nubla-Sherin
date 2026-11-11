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
    """Extends nhs.action with links back to the complaint, complaint investigation, or PHSO record that raised it."""
    _inherit = 'nhs.action'

    complaint_id = fields.Many2one('nhs.complaint', string='Source Complaint',
                                   ondelete='restrict',
                                   help='Complaint this action was raised from.')
    complaint_investigation_id = fields.Many2one(
        'nhs.complaint.investigation', string='Source Complaint Investigation',
        ondelete='restrict',
        help='Complaint investigation this action was raised from. Distinct from '
             'investigation_id, which points to the incident-side nhs.investigation.')
    phso_id = fields.Many2one('nhs.complaint.phso', string='Source PHSO Record',
                              ondelete='restrict',
                              help='PHSO recommendation this action was raised from (complaint_id still set for rollup).')

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-populate complaint_id from complaint_investigation_id or phso_id if not explicitly provided."""
        for vals in vals_list:
            if vals.get('complaint_investigation_id') and not vals.get('complaint_id'):
                inv = self.env['nhs.complaint.investigation'].browse(vals['complaint_investigation_id'])
                if inv.complaint_id:
                    vals['complaint_id'] = inv.complaint_id.id
            elif vals.get('phso_id') and not vals.get('complaint_id'):
                phso = self.env['nhs.complaint.phso'].browse(vals['phso_id'])
                if phso.complaint_id:
                    vals['complaint_id'] = phso.complaint_id.id
        return super().create(vals_list)

    @api.model
    def default_get(self, fields_list):
        """Pre-fill complaint_id when creating in a complaint investigation or PHSO context."""
        res = super().default_get(fields_list)
        inv_id = res.get('complaint_investigation_id') or self.env.context.get('default_complaint_investigation_id')
        if inv_id and not res.get('complaint_id'):
            inv = self.env['nhs.complaint.investigation'].browse(inv_id)
            if inv.complaint_id:
                res['complaint_id'] = inv.complaint_id.id
        phso_id = res.get('phso_id') or self.env.context.get('default_phso_id')
        if phso_id and not res.get('complaint_id'):
            phso = self.env['nhs.complaint.phso'].browse(phso_id)
            if phso.complaint_id:
                res['complaint_id'] = phso.complaint_id.id
        return res

    @api.onchange('complaint_investigation_id')
    def _onchange_complaint_investigation_id(self):
        """Pre-fill complaint_id when complaint_investigation_id is selected."""
        if self.complaint_investigation_id and not self.complaint_id:
            self.complaint_id = self.complaint_investigation_id.complaint_id

    @api.onchange('phso_id')
    def _onchange_phso_id(self):
        """Pre-fill complaint_id when phso_id is selected."""
        if self.phso_id and not self.complaint_id:
            self.complaint_id = self.phso_id.complaint_id

    @api.onchange('complaint_id')
    def _onchange_complaint_id(self):
        """Clear mismatched complaint investigation or PHSO record when complaint_id changes."""
        if self.complaint_investigation_id and self.complaint_investigation_id.complaint_id != self.complaint_id:
            self.complaint_investigation_id = False
        if self.phso_id and self.phso_id.complaint_id != self.complaint_id:
            self.phso_id = False

    @api.constrains('incident_id', 'investigation_id', 'risk_id', 'complaint_id',
                    'complaint_investigation_id', 'phso_id')
    def _check_single_parent(self):
        """Ensure an action is linked to at most one parent source domain/record hierarchy.

        - Incident side: allows incident + linked investigation (+ optional linked risk).
        - Complaint side: allows complaint + linked complaint_investigation OR complaint + linked phso.
        - Cross-linking between incident side and complaint side is strictly forbidden.
        """
        for rec in self:
            incident_side = bool(rec.incident_id) or bool(getattr(rec, 'investigation_id', False)) or bool(rec.risk_id)
            complaint_side = bool(rec.complaint_id) or bool(rec.complaint_investigation_id) or bool(rec.phso_id)

            if incident_side and complaint_side:
                raise ValidationError('An action can only be linked to one parent source record.')

            if incident_side:
                # incident + investigation (no risk): allowed if investigation belongs to that incident
                if rec.incident_id and getattr(rec, 'investigation_id', False) and not rec.risk_id:
                    if rec.investigation_id.incident_id == rec.incident_id:
                        continue
                # incident + investigation + risk: allowed when all three form a consistent chain
                if rec.incident_id and getattr(rec, 'investigation_id', False) and rec.risk_id:
                    if (rec.investigation_id.incident_id == rec.incident_id
                            and rec.risk_id in rec.incident_id.risk_ids):
                        continue
                incident_parents = (
                    bool(rec.incident_id)
                    + bool(getattr(rec, 'investigation_id', False))
                    + bool(rec.risk_id)
                )
                if incident_parents > 1:
                    raise ValidationError('An action can only be linked to one parent source record.')

            if complaint_side:
                # Cannot link to both complaint investigation and PHSO
                if rec.complaint_investigation_id and rec.phso_id:
                    raise ValidationError('An action can only be linked to one parent source record.')

                # If linked to both complaint and investigation, they must match
                if rec.complaint_id and rec.complaint_investigation_id:
                    if rec.complaint_investigation_id.complaint_id != rec.complaint_id:
                        raise ValidationError('An action can only be linked to one parent source record.')
                    continue

                # If linked to both complaint and PHSO, they must match
                if rec.complaint_id and rec.phso_id:
                    if rec.phso_id.complaint_id != rec.complaint_id:
                        raise ValidationError('An action can only be linked to one parent source record.')
                    continue

    @api.constrains('complaint_id', 'phso_id', 'complaint_investigation_id')
    def _check_parent_record_state(self):
        """Block creating or modifying actions whose parent complaint, PHSO record, or investigation is in a closed/final state."""
        for rec in self:
            if rec.complaint_id and rec.complaint_id.state in ('closed', 'withdrawn', 'resolved', 'escalated'):
                raise ValidationError('Cannot create or modify actions on a closed complaint or PALS concern.')
            if rec.phso_id and rec.phso_id.state != 'decision_made':
                raise ValidationError('Actions can only be created or modified on a PHSO record in the "Decision Made" state.')
            if rec.complaint_investigation_id and rec.complaint_investigation_id.state == 'complete':
                raise ValidationError('Cannot create or modify actions on a completed investigation.')
