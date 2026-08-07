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
#    You should have received a copy of the GNU LESSER PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models
from odoo.exceptions import UserError


class NhsAgendaItem(models.Model):
    _name = 'nhs.agenda.item'
    _description = 'Agenda Item & Paper'
    _order = 'meeting_id, sequence, id'
    _rec_name = 'title'

    meeting_id = fields.Many2one('nhs.meeting', string='Meeting', required=True,
                                 ondelete='cascade', help='Owning meeting.')
    committee_id = fields.Many2one(related='meeting_id.committee_id', string='Committee', store=True,
                                   help='Committee owning the meeting, for filtering/grouping.')
    sequence = fields.Integer(string='Sequence', default=10, help='Ordering of this item within the agenda.')
    item_number = fields.Char(string='Item No.', help='Agenda item number (e.g. "4.1").')
    title = fields.Char(string='Title', required=True, help='Agenda item title.')
    purpose = fields.Selection([
        ('decision', 'Decision'),
        ('assurance', 'Assurance'),
        ('information', 'Information'),
        ('discussion', 'Discussion'),
    ], string='Purpose', default='information', help='The purpose of this agenda item.')
    presenter_director_ids = fields.Many2many(
        'nhs.director', compute='_compute_presenter_director_ids',
        string='Allowed Presenters',
        help='Committee members eligible to be selected as Presenter, used to restrict the domain.'
    )
    presenter_id = fields.Many2one(
        'nhs.director', string='Presenter',
        domain="[('id', 'in', presenter_director_ids)]",
        help='Who presents this item, selected from committee members.'
    )
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
    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('deferred', 'Deferred'),
    ], string='Status', default='draft', required=True, help='Lifecycle status of this agenda item.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    @api.depends('committee_id', 'committee_id.member_ids.director_id')
    def _compute_presenter_director_ids(self):
        """Restrict allowed presenters to the owning committee's members."""
        for rec in self:
            if rec.committee_id and rec.committee_id.member_ids:
                rec.presenter_director_ids = rec.committee_id.member_ids.mapped('director_id')
            else:
                rec.presenter_director_ids = self.env['nhs.director'].search([])

    @api.constrains('state', 'deferred_to_id')
    def _check_deferred_to_id(self):
        """Keep state and Deferred To consistent, however the record was written.

        Checks both directions so this holds even for records created/updated
        via code or import, not just through the form's onchange:
        - Deferred state always needs a target meeting.
        - A target meeting always implies Deferred state.
        """
        for rec in self:
            if rec.state == 'deferred' and not rec.deferred_to_id:
                raise UserError('Please set "Deferred To" before marking an agenda item as Deferred.')
            if rec.deferred_to_id and rec.state != 'deferred':
                raise UserError('An agenda item with "Deferred To" set must be in the Deferred status.')

    @api.onchange('deferred_to_id')
    def _onchange_deferred_to_id(self):
        """Switch the item to Deferred as soon as a Deferred To meeting is set."""
        if self.deferred_to_id:
            self.state = 'deferred'

    def action_mark_complete(self):
        """Mark the agenda item as completed."""
        self.write({'state': 'completed'})

    def action_reset_draft(self):
        """Reset the agenda item back to draft and clear any deferral."""
        self.write({'state': 'draft', 'deferred_to_id': False})

    def action_defer_to_next(self):
        """Defer the agenda item by copying it onto the next scheduled meeting."""
        for rec in self:
            next_meeting = self.env['nhs.meeting'].search([
                ('committee_id', '=', rec.committee_id.id),
                ('meeting_date', '>', rec.meeting_id.meeting_date),
                ('state', 'not in', ['cancelled']),
            ], order='meeting_date', limit=1)
            if not next_meeting:
                raise UserError(
                    'No future meeting was found to defer "%s" to. '
                    'Schedule the next meeting first, or set "Deferred To" manually.' % rec.title
                )
            self.env['nhs.agenda.item'].create({
                'meeting_id': next_meeting.id,
                'title': rec.title,
                'purpose': rec.purpose,
                'presenter_id': rec.presenter_id.id,
                'cycle_item_id': rec.cycle_item_id.id,
                'is_confidential': rec.is_confidential,
            })
            rec.write({'state': 'deferred', 'deferred_to_id': next_meeting.id})
