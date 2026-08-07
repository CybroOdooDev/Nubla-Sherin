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
from odoo.exceptions import UserError

class NhsEricReturnSection(models.Model):
    _name = 'nhs.eric.return.section'
    _description = 'NHS ERIC Return Section Status'
    _inherit = ['mail.thread']
    _order = 'sequence, id'

    return_id = fields.Many2one(
        'nhs.eric.return',
        string='Return',
        required=True,
        ondelete='cascade',
        help='The return this section status belongs to.'
    )
    section_id = fields.Many2one(
        'nhs.eric.section',
        string='Section',
        required=True,
        ondelete='restrict',
        help='The section definition.'
    )
    sequence = fields.Integer(
        related='section_id.sequence',
        store=True,
        string='Sequence'
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Section Owner',
        tracking=True,
        help='User responsible for completing/populating this section.'
    )
    reviewer_id = fields.Many2one(
        'res.users',
        string='Section Reviewer',
        tracking=True,
        help='User responsible for reviewing and signing off this section.'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('ready_for_review', 'Ready for Review'),
        ('signed_off', 'Signed Off')
    ], string='Status', default='draft', required=True, tracking=True)

    signed_off_by_id = fields.Many2one(
        'res.users',
        string='Signed Off By',
        tracking=True,
        readonly=True
    )
    signed_off_at = fields.Datetime(
        string='Signed Off At',
        tracking=True,
        readonly=True
    )

    def write(self, vals):
        for record in self:
            if record.return_id.state in ('finalised', 'submitted'):
                raise UserError('This return has been finalised/submitted and is locked for editing.')
        return super(NhsEricReturnSection, self).write(vals)

    def action_submit_for_review(self):
        """Submit the section for review."""
        self.ensure_one()
        if not self.reviewer_id:
            raise UserError('Please assign a Section Reviewer before signing off.')
        required_gaps = self.return_id.value_ids.filtered(
            lambda v: v.section_id == self.section_id and v.item_def_id.required and v.status == 'gap'
        )
        if required_gaps:
            raise UserError('Cannot submit for review: there are required fields in this section that have not been populated.')

        self.write({'state': 'ready_for_review'})
        return True

    def action_sign_off(self):
        """Sign off the section."""
        self.ensure_one()
        if self.env.user != self.reviewer_id:
            raise UserError('Only the assigned Section Reviewer is allowed to sign off this section.')

        # Sign off all values in this section on the return
        values = self.return_id.value_ids.filtered(lambda v: v.section_id == self.section_id)
        for val in values:
            if not val.signed_off:
                val.action_sign_off()

        self.write({
            'state': 'signed_off',
            'signed_off_by_id': self.env.user.id,
            'signed_off_at': fields.Datetime.now()
        })
        return True

    def action_reopen(self):
        """Reopen the section for editing."""
        self.ensure_one()
        # Unsign all values in this section
        values = self.return_id.value_ids.filtered(lambda v: v.section_id == self.section_id)
        for val in values:
            if val.signed_off:
                val.action_unsign()

        self.write({
            'state': 'in_progress',
            'signed_off_by_id': False,
            'signed_off_at': False
        })
        return True
