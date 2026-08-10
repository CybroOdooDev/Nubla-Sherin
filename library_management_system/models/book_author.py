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


class BookAuthor(models.Model):
    """ Class for storing book authors """

    _name = "book.author"
    _rec_name = "author_name"
    _description = "Author names for books"

    image_medium = fields.Binary(string="Author Image",
                                 help='Image of the Author.')
    author_name = fields.Char(string="Author name", required=True,
                              help='Name of the author.')
    language = fields.Char(string="Language", help="Language of author.")
    gender = fields.Char(string="Gender", help='Gender of the author.')
    nationality_id = fields.Many2one("res.country",
                                     string="Nationality",
                                     help='Nationality of the author.')
    born = fields.Date(string="Born", help='Date of birth')
    died = fields.Date(string="Died", help='Date of died.')
    author_book_qty = fields.Integer("Written Books",
                                     compute="_compute_author_book_qty",
                                     help="Number of books written by author")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env[
                                     'res.users'].browse(
                                     self.env.uid).company_id.id,
                                 help="Current Company of the User")
    created_user_id = fields.Many2one('res.users', string='User Responsible',
                                      required=True, readonly=True,
                                      default=lambda self: self.env.uid,
                                      help="Created User")
    author_awards_ids = fields.One2many("author.award",
                                        "author_id",
                                        string="Author awards",
                                        help="List of awards received by"
                                             " the author.")

    def _compute_author_book_qty(self):
        """ Compute number of written books. """
        for rec in self:
            rec.author_book_qty = rec.env['product.template'].search_count(
                [('author_name', '=', self.id)])

    def action_view_written_books(self):
        """ Function to view written books """
        book_ids = []
        for book in self.env['product.template'].search([]):
            for author in book.author_name:
                if author.id == self.id:
                    book_ids.append(book.id)
        action = self.env.ref(
            'library_management_system.product_template_action').read()[0]
        if len(book_ids) > 1:
            action['domain'] = [('id', 'in', book_ids)]
        elif len(book_ids) == 1:
            action['views'] = [
                (self.env.ref('product.product_template_form_view').id,
                 'form')]
            action['res_id'] = book_ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
