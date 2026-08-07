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
from odoo import fields, models

class NHSComplianceRescheduleWizard(models.TransientModel):
    """Transient wizard for bulk-rescheduling compliance item due dates.
    Allows a compliance officer to select a new due date and provide a
    rescheduling reason for a batch of compliance items selected from the
    list view.  Each selected item's next_due_date is updated and the change
    is logged in the item's chatter.  Open preventive maintenance requests
    linked to the item are also rescheduled to match.
    """
    _name = 'nhs.compliance.reschedule.wizard'
    _description = 'Bulk Reschedule Compliance Items'

    new_due_date = fields.Date(string='New Due Date', required=True,
                               help='The new target due date to apply to all selected compliance items.')
    reason = fields.Text(string='Rescheduling Reason', required=True,
            help='The business justification for rescheduling (e.g. contractor unavailability, planned shutdown).')

    def action_apply(self):
        """Apply the new due date to all selected compliance items.
        Retrieves items via the ``active_ids`` context key, updates each item's
        next_due_date, posts a chatter message explaining the reason, and
        reschedules any open preventive maintenance requests to match.
        """
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return {'type': 'ir.actions.act_window_close'}
        items = self.env['nhs.compliance.item'].browse(active_ids)
        for item in items:
            item.write({'next_due_date': self.new_due_date})
            msg = "Rescheduled next due date to %s. Reason: %s" % (self.new_due_date, self.reason)
            item.message_post(body=msg)
            open_requests = self.env['maintenance.request'].search([
                ('equipment_id', '=', item.equipment_id.id),
                ('maintenance_type', '=', 'preventive'),
                ('stage_id.done', '=', False)
            ])
            if open_requests:
                open_requests.with_context(skip_maintenance_sync=True).write({
                    'schedule_date': self.new_due_date
                })
        return {'type': 'ir.actions.act_window_close'}
