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
from odoo import fields, models
from odoo.exceptions import ValidationError


class NhsActionComplaintsExtension(models.Model):
    _inherit = 'nhs.action'

    complaint_id = fields.Many2one('nhs.complaint', string='Source Complaint',
                                   ondelete='restrict',
                                   help='Complaint this action was raised from.')
    phso_id = fields.Many2one('nhs.complaint.phso', string='Source PHSO Record',
                              ondelete='restrict',
                              help='PHSO recommendation this action was raised from (complaint_id still set for rollup).')

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
