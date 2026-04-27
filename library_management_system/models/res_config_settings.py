# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Nublasherin k (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0(OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Model to handle configuration settings for the library management
     system. """
    _inherit = 'res.config.settings'

    return_in_days = fields.Integer(string="Return in",
                                    help='Specify the days that needs to '
                                         'return the book.',
                                    config_parameter='library_management_system.return_in_days')
    daily_due_amount = fields.Integer(string="Daily due", help='Specify the '
                                                               'daily due '
                                                               'amount.',
                                      config_parameter='library_management_system.daily_due_amount')
    is_auto_calc_return = fields.Boolean(string="Automatic return date",
                                      config_parameter='library_management_system.is_auto_calc_return')
    member_id_prefix = fields.Char(string="Prefix",
                                   help="Prefix fro generating member id",
                                   config_parameter='library_management_system.member_id_prefix')
    member_id_suffix = fields.Char(string="Suffix",
                                   help="Suffix for generating member id",
                                   config_parameter='library_management_system.member_id_suffix')
    due_journal_type_id = fields.Many2one('account.journal',
                                       string="Due Journal", required=True,
                                       config_parameter='library_management_system.due_journal_type_id',
                                       help="Due Journal Type")
    membership_journal_type_id = fields.Many2one('account.journal',
                                              string="Membership Journal",
                                              required=True,
                                              config_parameter='library_management_system.membership_journal_type_id',
                                              help="Membership Journal Type")

