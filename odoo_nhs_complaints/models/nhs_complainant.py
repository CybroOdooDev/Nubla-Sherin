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


class NhsComplainant(models.Model):
    _name = 'nhs.complainant'
    _description = 'Person Making a Complaint (may be a representative)'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True,
                       help="Complainant's full name.")
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone')
    address = fields.Text(string='Postal Address')
    relationship_to_patient = fields.Selection([
        ('self', 'Patient (self)'),
        ('relative', 'Relative'),
        ('carer', 'Carer'),
        ('advocate', 'Advocate'),
        ('mp', 'MP / Elected Representative'),
        ('solicitor', 'Solicitor'),
        ('other', 'Other'),
    ], string='Relationship to Patient', required=True, default='self', tracking=True,
       help="'self' means the patient is complaining for themselves.")
    partner_id = fields.Many2one('res.partner', string='Linked Contact',
                                 help='Optional link to an existing contact in the system.')
    is_vexatious = fields.Boolean(string='Vexatious / Habitual Complainant', tracking=True,
                                  help='Flag for habitual or vexatious complainants — reveals the handling policy note '
                                       'and restricts access to manager group.')
    vexatious_note = fields.Text(string='Vexatious Handling Policy',
                                 help='Documented rationale and agreed handling approach. Required when flagged vexatious.')
    complaint_ids = fields.One2many('nhs.complaint', 'complainant_id', string='Complaints')
    complaint_count = fields.Integer(string='Complaint Count', compute='_compute_complaint_count',
                                     store=True)

    @api.depends('complaint_ids')
    def _compute_complaint_count(self):
        for rec in self:
            rec.complaint_count = len(rec.complaint_ids)

    @api.constrains('is_vexatious', 'vexatious_note')
    def _check_vexatious_note(self):
        for rec in self:
            if rec.is_vexatious and not rec.vexatious_note:
                raise ValidationError('A vexatious handling policy note is required when flagging a complainant as vexatious.')

    def action_view_complaints(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Complaints',
            'res_model': 'nhs.complaint',
            'view_mode': 'list,form',
            'domain': [('complainant_id', '=', self.id)],
            'context': {'default_complainant_id': self.id},
        }
