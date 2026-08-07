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


class NhsCqcNotification(models.Model):
    """Extends nhs.cqc.notification with a direct link to a CQC Inspection
    record from odoo_nhs_trust_operations. This lives in the bridge because
    nhs.cqc.notification (incident module) must not reference
    nhs.trust.cqc.inspection (trust operations module) directly."""
    _inherit = 'nhs.cqc.notification'

    cqc_inspection_id = fields.Many2one(
        'nhs.trust.cqc.inspection',
        string='Linked CQC Inspection',
        ondelete='set null',
        help='The CQC inspection where this notification was reviewed or '
             'referenced as evidence. Filtered to inspections for this '
             'incident\'s trust.',
    )
    trust_id = fields.Many2one(
        'nhs.trust',
        related='incident_id.trust_id',
        string='Trust',
        store=False,
        help='Derived from the incident\'s linked trust. Used to scope the '
             'CQC inspection picker to the correct trust.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.cqc_inspection_id and rec.incident_id:
                rec.incident_id.cqc_inspection_ids = [(4, rec.cqc_inspection_id.id)]
        return records

    def write(self, vals):
        old_inspections = {rec.id: rec.cqc_inspection_id for rec in self}
        result = super().write(vals)
        if 'cqc_inspection_id' not in vals:
            return result
        for rec in self:
            incident = rec.incident_id
            if not incident:
                continue
            old_insp = old_inspections[rec.id]
            new_insp = rec.cqc_inspection_id
            if new_insp and new_insp != old_insp:
                incident.cqc_inspection_ids = [(4, new_insp.id)]
            elif not new_insp and old_insp:
                # Only remove from incident if no other notification on this
                # incident still references this inspection.
                still_linked = self.search([
                    ('incident_id', '=', incident.id),
                    ('cqc_inspection_id', '=', old_insp.id),
                    ('id', '!=', rec.id),
                ], limit=1)
                if not still_linked:
                    incident.cqc_inspection_ids = [(3, old_insp.id)]
        return result
