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
import uuid


PROVIDER_TYPES = [
    ('nhs_trust', 'NHS Trust'),
    ('gp_practice', 'GP Practice / PCN'),
    ('care_home', 'Care Home'),
    ('domiciliary_care', 'Domiciliary Care'),
    ('independent_hospital', 'Independent Hospital'),
    ('hospice', 'Hospice'),
    ('pharmacy', 'Pharmacy'),
    ('dental', 'Dental Practice'),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    provider_type = fields.Selection(PROVIDER_TYPES, string='Provider Type',
                                     default='nhs_trust',
                                     help='The type of CQC-registered provider. This setting controls which incident '
                                          'categories are visible, which notification rules apply, and which '
                                          'terminology pack is used across the system.')
    public_form_enabled = fields.Boolean(string='Public Incident Report Form Enabled',
                                         default=True,
                                         help='When enabled, a public-facing URL allows staff or members of the public '
                                              'to submit incident reports without logging in to Odoo.')
    public_form_token = fields.Char(string='Public Form Token', copy=False,
                                    help='The unique security token appended to the public reporting URL. '
                                         'Regenerate if the URL is compromised.')
    anonymous_reporting_allowed = fields.Boolean(string='Allow Anonymous Reporting', default=True,
                                                  help='When enabled, reporters may choose to submit incidents without '
                                                       'providing their name or contact details.')
    doc_trigger_grade = fields.Selection([
        ('moderate', 'Moderate Harm'),
        ('severe', 'Severe Harm'),
        ('death', 'Death'),
    ], string='Duty of Candour Trigger Grade', default='moderate',
       help='Incidents graded at or above this harm level will automatically trigger a '
            'Duty of Candour obligation under CQC Regulation 20.')
    default_handler_id = fields.Many2one('res.users', string='Default Incident Handler',
                                          help='The fallback handler assigned to new incidents when no location-specific '
                                               'default handler has been set.')
    board_pack_recipient_ids = fields.Many2many(
        'res.users', 'company_board_pack_recipients_rel',
        string='Board Pack Recipients',
        help='Users who should receive the monthly board-pack quality and safety report.')

    def _get_public_form_token(self):
        self.ensure_one()
        if not self.public_form_token:
            self.sudo().write({'public_form_token': str(uuid.uuid4()).replace('-', '')[:20]})
        return self.public_form_token


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    provider_type = fields.Selection(
        related='company_id.provider_type', readonly=False)
    public_form_enabled = fields.Boolean(
        related='company_id.public_form_enabled', readonly=False)
    public_form_token = fields.Char(
        related='company_id.public_form_token', readonly=True)
    anonymous_reporting_allowed = fields.Boolean(
        related='company_id.anonymous_reporting_allowed', readonly=False)
    doc_trigger_grade = fields.Selection(
        related='company_id.doc_trigger_grade', readonly=False)
    company_handler_id = fields.Many2one(
        related='company_id.default_handler_id', readonly=False)
    board_pack_recipient_ids = fields.Many2many(
        related='company_id.board_pack_recipient_ids', readonly=False)

    def action_regenerate_token(self):
        self.company_id.sudo().write(
            {'public_form_token': str(uuid.uuid4()).replace('-', '')[:20]})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_public_form(self):
        self.ensure_one()
        token = self.company_id._get_public_form_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return {
            'type': 'ir.actions.act_url',
            'url': '%s/incident/report/%s' % (base_url, token),
            'target': 'new',
        }
