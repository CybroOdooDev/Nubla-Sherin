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
from odoo.exceptions import ValidationError


class NhsCycleOfBusiness(models.Model):
    _name = 'nhs.cycle.of.business'
    _description = 'Cycle of Business — Standing Item'
    _order = 'committee_id, sequence, title'
    _rec_name = 'title'

    committee_id = fields.Many2one('nhs.committee', string='Committee', required=True,
                                   ondelete='cascade', help='The committee this standing item belongs to.')
    title = fields.Char(string='Standing Item', required=True,
                        help="The standing item due to come to the committee "
                             "(e.g. 'Annual Accounts', 'Risk Register Review').")
    sequence = fields.Integer(string='Sequence', default=10, help='Ordering of this standing item within the cycle.')
    frequency = fields.Selection([
        ('every_meeting', 'Every Meeting'),
        ('quarterly', 'Quarterly'),
        ('biannual', 'Bi-Annual'),
        ('annual', 'Annual'),
    ], string='Frequency', required=True, default='every_meeting',
       help='How often this standing item comes to the committee.')
    scheduled_months = fields.Many2many(
        'nhs.gov.month', 'nhs_cob_month_rel', 'cob_id', 'month_id',
        string='Scheduled Months',
        help='Which calendar months this item is due, e.g. March/June/September/December for a '
             'quarterly item. Used with Quarterly / Bi-Annual / Annual frequency to know which '
             'specific meetings it should be pulled onto.')
    purpose = fields.Selection([
        ('decision', 'Decision'),
        ('assurance', 'Assurance'),
        ('information', 'Information'),
    ], string='Purpose', default='assurance',
       help='The default purpose of this standing item when it is pulled onto an agenda.')
    owner_partner_ids = fields.Many2many(
        'res.partner', compute='_compute_owner_partner_ids',
        string='Allowed Owners',
        help='Committee members eligible to be selected as Item Owner, used to restrict the domain.'
    )
    owner_id = fields.Many2one(
        'res.partner', string='Item Owner',
        domain="[('id', 'in', owner_partner_ids)]",
        help='The item owner/presenter responsible for bringing this item.'
    )

    @api.depends('committee_id', 'committee_id.member_ids.partner_id')
    def _compute_owner_partner_ids(self):
        """Restrict allowed item owners to the owning committee's members."""
        for rec in self:
            if rec.committee_id and rec.committee_id.member_ids:
                rec.owner_partner_ids = rec.committee_id.member_ids.mapped('partner_id')
            else:
                rec.owner_partner_ids = self.env['res.partner'].search([])

    @api.onchange('frequency')
    def _onchange_frequency(self):
        """Clear Scheduled Months when the frequency is switched to Every Meeting."""
        if self.frequency == 'every_meeting':
            self.scheduled_months = [(5, 0, 0)]

    @api.constrains('frequency', 'scheduled_months')
    def _check_scheduled_months(self):
        """Forbid Scheduled Months on an Every Meeting standing item."""
        for rec in self:
            if rec.frequency == 'every_meeting' and rec.scheduled_months:
                raise ValidationError(
                    'An "Every Meeting" standing item is due at every meeting regardless of month — '
                    'it cannot also have Scheduled Months set. Clear them, or change the Frequency.'
                )
    is_statutory = fields.Boolean(string='Statutory / Mandatory', default=False,
                                  help='Flags this as a statutory or mandatory annual obligation '
                                       '(shown on the governance calendar so nothing mandatory is missed).')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    def is_due_for_month(self, month):
        """Whether this standing item is due for the given calendar month (1-12)."""
        self.ensure_one()
        if self.frequency == 'every_meeting':
            return True
        if not self.scheduled_months:
            return False
        return month in self.scheduled_months.mapped('code')
