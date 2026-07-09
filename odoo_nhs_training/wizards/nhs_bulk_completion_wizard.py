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

from ..models.nhs_training_record import METHODS


class NhsBulkCompletionWizard(models.TransientModel):
    _name = 'nhs.bulk.completion.wizard'
    _description = 'Record a training session completion for many members at once'

    subject_id = fields.Many2one(
        'nhs.training.subject',
        string='Subject',
        required=True,
        help="The subject/level everyone in the session completed."
    )
    completion_date = fields.Date(
        string='Completion Date',
        required=True,
        default=fields.Date.context_today,
    )
    method = fields.Selection(
        METHODS,
        string='Method',
        default='classroom',
    )
    provider = fields.Char(
        string='Provider',
    )
    certificate_ref = fields.Char(
        string='Certificate / Session Reference',
    )
    org_unit_id = fields.Many2one(
        'nhs.org.unit',
        string='Filter by Team',
        help="Optional — narrows the member picker below to one team."
    )
    member_ids = fields.Many2many(
        'nhs.workforce.member',
        string='Members Attending',
        required=True,
        domain="[('is_leaver', '=', False)]",
        help="Everyone who attended this session."
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Certificate / Evidence',
    )

    @api.onchange('org_unit_id')
    def _onchange_org_unit_id(self):
        if self.org_unit_id:
            self.member_ids = self.env['nhs.workforce.member'].search([
                ('org_unit_id', 'child_of', self.org_unit_id.id), ('is_leaver', '=', False),
            ])

    def action_confirm(self):
        self.ensure_one()
        if not self.member_ids:
            raise UserError(('Select at least one member who attended.'))
        records = self.env['nhs.training.record'].create([{
            'member_id': member.id,
            'subject_id': self.subject_id.id,
            'completion_date': self.completion_date,
            'method': self.method,
            'provider': self.provider,
            'certificate_ref': self.certificate_ref,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
        } for member in self.member_ids])
        return {
            'name': ('Training Records Created'),
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.training.record',
            'view_mode': 'list,form',
            'domain': [('id', 'in', records.ids)],
        }
