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

class NHSDutyRole(models.Model):
    """Model to define statutory duty roles such as Responsible Person or Duty Holder and their configuration."""
    _name = 'nhs.duty.role'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Duty-Role Definition'
    _order = 'name'

    name = fields.Char(string='Role Name', required=True,help='Duty Holder, Designated Person, Responsible Person,'
                                                        ' Authorised Person, Competent Person, Authorising Engineer')
    code = fields.Char(string='Code', required=True, help='DH / DP / RP / AP / CP / AE')
    description = fields.Text(string='Description', help='What the role is accountable for')
    requires_authorisation = fields.Boolean(string='Requires Authorisation', default=False,
                                             help='Whether the role needs a formal, expiring authorisation')
    active = fields.Boolean(string='Active', default=True,
                            help='Uncheck to archive this duty role without deleting it.')
