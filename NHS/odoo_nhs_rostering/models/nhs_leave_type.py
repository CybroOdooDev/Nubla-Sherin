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


class NhsLeaveType(models.Model):
    """Reference data: a category of leave/absence - annual, study, maternity/
    paternity/parental, TOIL, other. Configurable per organisation."""
    _name = 'nhs.leave.type'
    _description = 'Leave Type'
    _order = 'sequence, name'

    name = fields.Char(string='Leave Type', required=True, translate=True, help="Leave Type")
    code = fields.Char(string='Code', help="Code")
    sequence = fields.Integer(string='Sequence', default=10, help="Sequence")
    is_paid = fields.Boolean(string='Paid', default=True, help="Paid")
    counts_as_worked_hours = fields.Boolean(
        string='Counts as Worked Hours',
        help="If on, hours on this leave type count toward the 48-hour average week"
             " (rare - most leave does not)."
    )
    requires_approval = fields.Boolean(string='Requires Approval', default=True, help="Requires Approval")
    color = fields.Integer(string='Colour Index', default=1, help="Colour Index")
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company,
        help="Leave blank to make this leave type available to every company.")
    active = fields.Boolean(string='Active', default=True, help="Active")
