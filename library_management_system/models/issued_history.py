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


class IssuedHistory(models.Model):
    """ Class for storing issued book history """
    _name = "issued.history"
    _description = "Book Issued History"
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env[
                                     'res.users'].browse(
                                     self.env.uid).company_id.id,
                                 help="The company associated with the record.")
    created_user_id = fields.Many2one('res.users', 'User Responsible',
                                      required=True, readonly=True,
                                      default=lambda self: self.env.uid,
                                      help="The user responsible for creating "
                                           "the record.")
    register_reference_id = fields.Many2one("book.register", "Register",
                                            required=True,
                                            help="The book register associated"
                                                 " with the record.")
    register_sequence = fields.Char(string="Register ID", required=True,
                                    help="The identification number of the"
                                         " book register.")
    book_name_id = fields.Many2one("product.product", string="Book Name",
                                   required=True,
                                   help="The book associated with the record.")
    issued_date = fields.Date(string="Issued Date", required=True,
                              help="The date on which the book was issued.")
    expiry_date = fields.Date(string="Expiry Date", required=True,
                              help="The date on which the book's"
                                   " membership expires.")
    book_isbn = fields.Char(string="ISBN 10", required=True,
                            help="The International Standard Book Number"
                                 " (ISBN) of the book (10-digit).")
    edition = fields.Char(string="Edition", help="The edition of the book.")
    member_book_history_id = fields.Many2one('res.partner',
                                             string="Member Name",
                                             help="The member associated"
                                                  " with the book history.")
    book_issued_history_id = fields.Many2one('product.template',
                                             string="Issued Book",
                                             help="The book associated "
                                                  "with the issued history.")

    def action_view_register(self):
        """ Function to view details of the register """
        value = {'name': ('Register'),
                 'view_mode': 'form',
                 'res_id': int(self.register_reference_id),
                 'res_model': 'book.register',
                 'type': 'ir.actions.act_window',
                 'target': 'new'}
        return value
