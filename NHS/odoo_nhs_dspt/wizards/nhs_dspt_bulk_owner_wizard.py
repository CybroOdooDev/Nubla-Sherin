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
from odoo.exceptions import UserError

BULK_OWNER_MODELS = ('nhs.dspt.evidence', 'nhs.dspt.assertion')


class NhsDsptBulkOwnerWizard(models.TransientModel):
    """Bulk-assign a single owner across several selected evidence items or
    assertions in one action (spec 4.11: 'Bulk assignment of owners on
    setup' / 4.4: 'Reassign ownership in bulk')."""
    _name = 'nhs.dspt.bulk.owner.wizard'
    _description = 'Bulk Assign DSPT Owner'

    active_model = fields.Char(
        string='Target Model',
        default=lambda self: self._default_active_model(),
    )
    record_count = fields.Integer(
        string='Records Selected',
        default=lambda self: len(self.env.context.get('active_ids') or []),
    )
    owner_id = fields.Many2one(
        'res.users',
        string='New Owner',
        required=True,
        help="Every selected item will be reassigned to this owner."
    )

    @api.model
    def _default_active_model(self):
        model = self.env.context.get('active_model')
        if model not in BULK_OWNER_MODELS:
            raise UserError((
                'Bulk owner assignment is only available from the Evidence'
                ' Library or the Assertions list.'
            ))
        return model

    def action_confirm(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids') or []
        if not active_ids:
            raise UserError(('Select at least one record first.'))
        records = self.env[self.active_model].browse(active_ids)
        records.write({'owner_id': self.owner_id.id})
        return {'type': 'ir.actions.act_window_close'}
