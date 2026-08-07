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


class NhsBoardRole(models.Model):
    _name = 'nhs.board.role'
    _description = 'NHS Board Role (configurable label for res.partner.nhs_board_role)'
    _order = 'sequence, id'

    name = fields.Char(string='Label', required=True, translate=True,
                       help='The label shown in the Board Role dropdown on a Contact. '
                            'Rename this to match your organisation\'s terminology.')
    code = fields.Selection([
        ('chair', 'Chair'),
        ('ceo', 'Chief Executive Officer (CEO)'),
        ('medical_director', 'Medical Director'),
        ('nursing_director', 'Director of Nursing'),
        ('finance_director', 'Director of Finance'),
        ('exec', 'Executive Director'),
        ('non_exec', 'Non-Executive Director'),
        ('other', 'Other Board Member'),
    ], string='Code', required=True, index=True,
       help="The underlying role key. Fixed — chair/ceo/medical_director/nursing_director/"
            "finance_director drive the trust's Chair/CEO/Medical Director/Director of Nursing/"
            "Finance Director auto-assignment (nhs.trust). Only the label, description, order and "
            "active state are configurable; the key itself cannot be changed once code is set.")
    is_ned = fields.Boolean(string='Counts As Non-Executive Director', default=False,
                            help='Whether a person with this role counts as a Non-Executive Director '
                                 '(NED) for governance purposes, e.g. NED-quorum on committees in '
                                 'NHS Governance Management, where that module is installed.')
    sequence = fields.Integer(string='Sequence', default=10,
                              help='Display order in the Board Role dropdown.')
    description = fields.Text(string='Description',
                              help='Guidance shown to administrators when choosing this role.')
    active = fields.Boolean(string='Active', default=True,
                            help='Untick to hide this role from the dropdown without deleting it. '
                                 'Contacts already using it keep their value.')

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'A board role already exists for this code.',
    )
