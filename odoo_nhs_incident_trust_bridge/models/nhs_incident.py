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


class NhsIncident(models.Model):
    """Extends nhs.incident with a Trust link and CQC inspection connections.

    trust_id scopes the location picker to the correct trust's sites and
    departments. cqc_inspection_ids links the incident to formal CQC
    inspection visits for cross-referencing safety events against findings.
    """
    _inherit = 'nhs.incident'

    trust_id = fields.Many2one(
        'nhs.trust',
        string='NHS Trust',
        store=True,
        index=True,
        tracking=True,
        help='The NHS Trust this incident belongs to. Scopes the location '
             'picker to sites and departments registered under this trust.',
    )
    cqc_inspection_ids = fields.Many2many(
        'nhs.trust.cqc.inspection',
        'nhs_incident_cqc_inspection_rel',
        'incident_id',
        'inspection_id',
        string='CQC Inspections',
        help='CQC inspections this incident was raised against or is relevant to.',
    )

    @api.onchange('trust_id')
    def _onchange_trust_id_clear_location(self):
        """Clear the location when trust changes if the selected location
        belongs to a different trust — prevents a cross-trust mismatch."""
        if self.location_id and self.location_id.trust_id:
            if self.location_id.trust_id != self.trust_id:
                self.location_id = False
