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


class BookHistory(models.Model):
    """ Model for storing issued book history """
    _name = "book.history"
    _description = "Issued Book History"

    register_reference_id = fields.Many2one("book.register", "Register",
                                            required=True,
                                            help='Register reference id')
    register_sequence = fields.Char(string="Register ID", required=True,
                                    help='Register sequence')
    book_name_id = fields.Many2one("product.product", string="Book Name",
                                   help='Name of the book',
                                   required=True)
    issued_date = fields.Date(string="Issued Date", required=True,
                              help='Book issue date')
    expiry_date = fields.Date(string="Expiry Date", required=True,
                              help='Book expiry date')
    book_isbn = fields.Char(string="ISBN 10", required=True,
                            help='Book isbn 10')
    edition = fields.Char(string="Edition", help='Book edition')

    member_book_history_id = fields.Many2one('res.partner',
                                             string="Book History",
                                             help='History of the book')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env[
                                     'res.users'].browse(
                                     self.env.uid).company_id.id,
                                 help='Name of the company')
    created_user_id = fields.Many2one('res.users', 'User Responsible',
                                      required=True, readonly=True,
                                      default=lambda self: self.env.uid,
                                      help='Responsible User')

    def action_view_register(self):
        """ Function to view details of the register """
        value = {'name': ('Register'),
                 'view_mode': 'form',
                 'res_id': int(self.register_reference_id),
                 'res_model': 'book.register',
                 'type': 'ir.actions.act_window',
                 'target': 'new'}
        return value
