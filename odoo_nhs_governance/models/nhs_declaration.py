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


class NhsDeclaration(models.Model):
    _name = 'nhs.declaration'
    _description = 'Declaration of Interest'
    _inherit = ['mail.thread']
    _order = 'date_from desc, id desc'

    partner_id = fields.Many2one('res.partner', string='Declared By', required=True,
                                 tracking=True, help='The director/officer/member who declared.')
    company_id = fields.Many2one(related='partner_id.company_id', string='Company', store=True)
    category_id = fields.Many2one('nhs.gov.interest.category', string='Interest Category', required=True,
                                  help='Financial / non-financial professional / non-financial personal / '
                                       'loyalty / indirect / nil return.')
    category_code = fields.Selection(related='category_id.code', string='Category Code', store=True)
    nature = fields.Text(string='Nature of Interest', help='Description of the interest declared.')
    related_org = fields.Char(string='Related Organisation',
                              help='The organisation the interest relates to.')
    date_from = fields.Date(string='Date From', default=fields.Date.context_today,
                            help='Start of the period the interest applies.')
    date_to = fields.Date(string='Date To', help='End of the period the interest applies, if it has ended.')
    event = fields.Selection([
        ('appointment', 'On Appointment'),
        ('annual', 'Annual Refresh'),
        ('at_meeting', 'At Meeting'),
        ('ad_hoc', 'Ad-hoc'),
    ], string='Declaration Trigger', required=True, default='ad_hoc', tracking=True,
       help='What triggered this declaration: on appointment, the annual refresh, at a specific '
            'meeting/agenda item, or an ad-hoc update.')
    meeting_id = fields.Many2one('nhs.meeting', string='Meeting',
                                 help='For at-meeting declarations, the meeting this was declared at.')
    agenda_item_id = fields.Many2one('nhs.agenda.item', string='Agenda Item',
                                     domain="[('meeting_id', '=', meeting_id)]",
                                     help='The agenda item the conflict relates to.')
    conflict_management = fields.Selection([
        ('noted', 'Noted'),
        ('withdrew_from_item', 'Withdrew From Item'),
        ('left_room', 'Left The Room'),
        ('no_action', 'No Action Required'),
    ], string='Conflict Management', tracking=True,
       help='How a declared conflict was managed for this item.')
    is_published = fields.Boolean(string='Include In Published Register', default=True,
                                  help='Whether this declaration is included in the published Declarations '
                                       'of Interest register output. Untick to exclude a draft/incomplete entry.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag — declarations are archived, '
                            'never hard-deleted, to preserve the governance record.')

    @api.onchange('category_code')
    def _onchange_category_nil(self):
        if self.category_code == 'nil':
            self.nature = False
            self.related_org = False

    def unlink(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Declarations of interest cannot be deleted — archive them instead '
                            'to preserve the governance record.')
        return super().unlink()
