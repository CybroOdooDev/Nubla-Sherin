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

class MaintenanceRequest(models.Model):
    """Extension of standard maintenance request model to synchronize schedules and outcomes with compliance items."""
    _inherit = 'maintenance.request'

    compliance_item_id = fields.Many2one(
        'nhs.compliance.item',
        string='Compliance Item',
        ondelete='set null',
        help='The compliance item linked to this maintenance request.',
        index=True  # Add index for better performance
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to synchronise the compliance item's next due date."""
        requests = super(MaintenanceRequest, self).create(vals_list)
        for req in requests:
            if req.compliance_item_id and req.maintenance_type == 'preventive' and req.schedule_date:
                if not self.env.context.get('skip_maintenance_sync'):
                    if req.compliance_item_id.next_due_date != req.schedule_date:
                        req.compliance_item_id.with_context(skip_maintenance_sync=True).write({
                            'next_due_date': req.schedule_date
                        })
        return requests

    def write(self, vals):
        """Override write to handle compliance synchronisation on stage/schedule changes."""
        done_stage_ids = self.env['maintenance.stage'].search([('done', '=', True)]).ids
        was_done = {req.id: req.stage_id.id in done_stage_ids for req in self}
        res = super(MaintenanceRequest, self).write(vals)
        if 'stage_id' in vals or 'archive' in vals or 'schedule_date' in vals:
            for req in self:
                if req.compliance_item_id and req.maintenance_type == 'preventive':
                    if ('schedule_date' in vals and req.schedule_date and
                            not self.env.context.get('skip_maintenance_sync')):
                        if req.compliance_item_id.next_due_date != req.schedule_date:
                            req.compliance_item_id.with_context(skip_maintenance_sync=True).write({
                                'next_due_date': req.schedule_date
                            })
                    is_now_done = req.stage_id.id in done_stage_ids
                    if is_now_done and not was_done.get(req.id) and not self.env.context.get('skip_maintenance_sync'):
                        self.env['nhs.compliance.test'].with_context(skip_maintenance_sync=True).create({
                            'item_id': req.compliance_item_id.id,
                            'test_date': req.close_date or fields.Date.today(),
                            'outcome': 'pass',
                            'notes': req.description or 'Completed via Maintenance Request: %s' % req.name,
                        })
        return res

    @api.depends('company_id', 'equipment_id', 'compliance_item_id')
    def _compute_maintenance_team_id(self):
        """Override to ensure compliance maintenance requests are assigned to the Compliance Team."""
        super(MaintenanceRequest, self)._compute_maintenance_team_id()
        compliance_team = self.env['maintenance.team'].sudo().search([('name', '=', 'Compliance Team')], limit=1)
        if compliance_team:
            for request in self:
                if request.compliance_item_id:
                    request.maintenance_team_id = compliance_team.id
