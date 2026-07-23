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


class NhsAgendaItem(models.Model):
    _name = 'nhs.agenda.item'
    _description = 'Agenda Item & Paper'
    _order = 'meeting_id, sequence, id'

    meeting_id = fields.Many2one('nhs.meeting', string='Meeting', required=True,
                                 ondelete='cascade', help='Owning meeting.')
    committee_id = fields.Many2one(related='meeting_id.committee_id', string='Committee', store=True)
    sequence = fields.Integer(string='Sequence', default=10)
    item_number = fields.Char(string='Item No.', help='Agenda item number (e.g. "4.1").')
    title = fields.Char(string='Title', required=True, help='Agenda item title.')
    purpose = fields.Selection([
        ('decision', 'Decision'),
        ('assurance', 'Assurance'),
        ('information', 'Information'),
        ('discussion', 'Discussion'),
    ], string='Purpose', default='information', help='The purpose of this agenda item.')
    presenter_partner_ids = fields.Many2many(
        'res.partner', compute='_compute_presenter_partner_ids',
        string='Allowed Presenters'
    )
    presenter_id = fields.Many2one(
        'res.partner', string='Presenter',
        domain="[('id', 'in', presenter_partner_ids)]",
        help='Who presents this item, selected from committee members.'
    )

    @api.depends('committee_id', 'committee_id.member_ids.partner_id')
    def _compute_presenter_partner_ids(self):
        for rec in self:
            if rec.committee_id and rec.committee_id.member_ids:
                rec.presenter_partner_ids = rec.committee_id.member_ids.mapped('partner_id')
            else:
                rec.presenter_partner_ids = self.env['res.partner'].search([])
    time_allocation = fields.Integer(string='Minutes Allocated', help='Time allocated to this item, in minutes.')
    cycle_item_id = fields.Many2one('nhs.cycle.of.business', string='Standing Item',
                                    help='The cycle-of-business standing item this agenda item fulfils, '
                                         'if pulled from the cycle rather than added ad-hoc.')
    is_confidential = fields.Boolean(string='Confidential (Part II)', default=False,
                                     help='Part-II / confidential item — restricted to entitled members '
                                          'and shown in a separate confidential pack section.')
    paper_ids = fields.Many2many('ir.attachment', string='Papers',
                                 help='Papers/reports attached to this agenda item.')
    minute_text = fields.Html(string='Minute', help='The minute recorded for this item.')
    decision_text = fields.Text(string='Decision / Resolution', help='The formal decision or resolution made.')
    deferred_to_id = fields.Many2one('nhs.meeting', string='Deferred To',
                                     help='If this item was carried forward, the meeting it moved to.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    def action_defer_to_next(self):
        for rec in self:
            next_meeting = self.env['nhs.meeting'].search([
                ('committee_id', '=', rec.committee_id.id),
                ('meeting_date', '>', rec.meeting_id.meeting_date),
                ('state', 'not in', ['cancelled']),
            ], order='meeting_date', limit=1)
            if next_meeting:
                self.env['nhs.agenda.item'].create({
                    'meeting_id': next_meeting.id,
                    'title': rec.title,
                    'purpose': rec.purpose,
                    'presenter_id': rec.presenter_id.id,
                    'cycle_item_id': rec.cycle_item_id.id,
                    'is_confidential': rec.is_confidential,
                })
                rec.deferred_to_id = next_meeting.id
