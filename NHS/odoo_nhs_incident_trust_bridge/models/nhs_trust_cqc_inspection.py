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


class NhsTrustCqcInspection(models.Model):
    """Extends nhs.trust.cqc.inspection with a reverse Many2many link back to
    patient safety incidents that reference this inspection record.

    The Many2many uses the same relation table as nhs.incident.cqc_inspection_ids
    so both sides of the relationship are automatically kept in sync.
    """
    _inherit = 'nhs.trust.cqc.inspection'

    incident_ids = fields.Many2many(
        'nhs.incident',
        'nhs_incident_cqc_inspection_rel',
        'inspection_id',
        'incident_id',
        string='Linked Incidents',
        help='Patient safety incidents that have been linked to this CQC inspection '
             'by the quality team. Managed from the incident form.',
    )
    incident_count = fields.Integer(
        string='Incident Count',
        compute='_compute_incident_count',
        help='Number of patient safety incidents currently linked to this inspection.',
    )

    @api.depends('incident_ids')
    def _compute_incident_count(self):
        for rec in self:
            rec.incident_count = len(rec.incident_ids)

    def action_view_linked_incidents(self):
        self.ensure_one()
        return {
            'name': f'Incidents — {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.incident',
            'view_mode': 'list,kanban,form',
            'domain': [('cqc_inspection_ids', 'in', [self.id])],
            'context': {'default_cqc_inspection_ids': [(4, self.id)]},
        }
