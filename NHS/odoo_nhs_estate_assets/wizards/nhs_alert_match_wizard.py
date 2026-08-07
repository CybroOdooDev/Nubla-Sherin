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

class NHSAlertMatchWizard(models.TransientModel):
    """
    Alert Match Wizard
    ==================
    Matches devices by make/model/category and creates alert lines.
    Used to automatically populate affected devices for a safety alert.
    """
    _name = 'nhs.alert.match.wizard'
    _description = 'Alert Match Wizard'

    alert_id = fields.Many2one(
        'nhs.device.alert',
        string='Alert',
        required=True,
        help='The alert to match devices against.'
    )
    affected_make = fields.Char(
        string='Affected Make',
        help='Device manufacturer to match.'
    )
    affected_model = fields.Char(
        string='Affected Model',
        help='Device model to match.'
    )
    affected_category_id = fields.Many2one(
        'nhs.device.category',
        string='Affected Category',
        help='Device category to match.'
    )
    match_mode = fields.Selection(
        selection=[
            ('and', 'Match All (AND)'),
            ('or', 'Match Any (OR)'),
        ],
        string='Match Mode',
        required=True,
        default='and',
        help='AND: All conditions must match. OR: Any condition can match.'
    )
    matched_device_ids = fields.Many2many(
        'nhs.device',
        string='Matched Devices',
        compute='_compute_matched_devices',
        help='Devices that match the criteria.'
    )

    @api.depends('affected_make', 'affected_model', 'affected_category_id', 'match_mode')
    def _compute_matched_devices(self):
        """
        Find matching devices, excluding already linked ones.
        """
        for wizard in self:
            domain = []
            if wizard.affected_make:
                domain.append(('manufacturer', 'ilike', wizard.affected_make))
            if wizard.affected_model:
                domain.append(('model', 'ilike', wizard.affected_model))
            if wizard.affected_category_id:
                domain.append(('category_id', '=', wizard.affected_category_id.id))
            if not domain:
                wizard.matched_device_ids = self.env['nhs.device']
                continue
            if wizard.match_mode == 'or' and len(domain) > 1:
                domain = ['|'] * (len(domain) - 1) + domain
            devices = self.env['nhs.device'].search(domain)
            existing = wizard.alert_id.line_ids.mapped('device_id')
            wizard.matched_device_ids = devices - existing

    def action_apply_matches(self):
        self.ensure_one()
        self.alert_id.write({
            'affected_make': self.affected_make,
            'affected_model': self.affected_model,
            'affected_category_id': self.affected_category_id.id,
        })
        if not self.matched_device_ids:
            raise ValidationError("No devices match the criteria.")
        for device in self.matched_device_ids:
            self.env['nhs.device.alert.line'].create({
                'alert_id': self.alert_id.id,
                'device_id': device.id,
                'action_required': self.alert_id.required_action,
                'action_status': 'pending',
            })
        return {'type': 'ir.actions.act_window_close'}

    def action_apply_and_open(self):
        """
        Apply matches and open the alert form.
        """
        self.action_apply_matches()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'nhs.device.alert',
            'res_id': self.alert_id.id,
            'view_mode': 'form',
        }
