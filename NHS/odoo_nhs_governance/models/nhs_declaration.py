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


class NhsDeclaration(models.Model):
    _name = 'nhs.declaration'
    _description = 'Declaration of Interest'
    _inherit = ['mail.thread']
    _order = 'date_from desc, id desc'

    director_id = fields.Many2one('nhs.director', string='Declared By', required=True,
                                  tracking=True, help='The director/officer who declared.')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company,
                                 help='The company this declaration of interest belongs to.')
    name = fields.Char(string='Reference', compute='_compute_name', store=True,
                       help='Auto-generated label combining the declarant, category and year.')

    @api.depends('director_id', 'category_id', 'date_from')
    def _compute_name(self):
        """Build the declaration reference label from director, category and year."""
        for rec in self:
            if rec.director_id and rec.category_id:
                year = rec.date_from.strftime('%Y') if rec.date_from else ''
                rec.name = f"{rec.director_id.name} - {rec.category_id.name} {year}".strip()
            else:
                rec.name = 'New Declaration'

    category_id = fields.Many2one('nhs.gov.interest.category', string='Interest Category', required=True,
                                  help='Financial / non-financial professional / non-financial personal / '
                                       'loyalty / indirect / nil return.')
    category_code = fields.Selection(related='category_id.code', string='Category Code', store=True,
                                     help='Related interest category code, used for nil-return logic.')
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
        """Clear the interest details when the category is a nil return."""
        if self.category_code == 'nil':
            self.nature = False
            self.related_org = False

    @api.constrains('category_code', 'nature', 'related_org')
    def _check_nil_has_no_interest(self):
        """Block interest details on a nil return, however the record was written.

        The onchange above only helps in the form view; this enforces the same
        rule for records created/updated via code or import, so the published
        register can't end up with a nil return that still carries interest
        details.
        """
        for rec in self:
            if rec.category_code == 'nil' and (rec.nature or rec.related_org):
                raise UserError('A nil return cannot carry Nature of Interest or Related Organisation details.')

    @api.model_create_multi
    def create(self, vals_list):
        """Create declarations and confirm receipt by email for the Annual Refresh trigger only —
        On Appointment, At Meeting and Ad-hoc declarations don't get this confirmation."""
        records = super().create(vals_list)
        template = self.env.ref('odoo_nhs_governance.mail_template_doi_annual_confirmed',
                                raise_if_not_found=False)
        if template:
            for rec in records.filtered(lambda d: d.event == 'annual' and d.director_id.email):
                template.send_mail(rec.id, force_send=False)
        return records

    def unlink(self):
        """Prevent deletion of declarations unless the user is a system admin."""
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Declarations of interest cannot be deleted — archive them instead '
                            'to preserve the governance record.')
        return super().unlink()

    def action_set_noted(self):
        """Record that the conflict was noted with no further action."""
        self.write({'conflict_management': 'noted'})

    def action_set_withdrew(self):
        """Record that the declarant withdrew from the agenda item."""
        self.write({'conflict_management': 'withdrew_from_item'})

    def action_set_left_room(self):
        """Record that the declarant left the room for this item."""
        self.write({'conflict_management': 'left_room'})

    def action_set_no_action(self):
        """Record that no conflict management action was required."""
        self.write({'conflict_management': 'no_action'})
