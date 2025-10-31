# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Gayathri V (odoo@cybrosys.com)
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


class BookPublisher(models.Model):
    """ Class for storing book publishers """

    _name = "book.publisher"
    _rec_name = "publisher_name"
    _description = "Publisher for book"

    image_medium = fields.Binary(string="Author Image",
                                 help="The image of the author.")
    publisher_name = fields.Char(string="Publisher name", required=True,
                                 help="The name of the publisher.")
    website = fields.Char(string="Official website",
                          help="The official website of the publisher.")
    founder = fields.Char(string="Founder",
                          help="The founder of the publisher.")
    country_origin_id = fields.Many2one("res.country",
                                        string="Country of origin",
                                        help="The country where the "
                                             "publisher originates.")
    founded = fields.Date(string="Founded",
                          help="The founding date of the publisher.")
    publisher_book_qty = fields.Integer(string="Published Books",
                                        compute="compute_published_book",
                                        help="The number of books published"
                                             " by the publisher.")
    related_author_qty = fields.Integer(string="Authors Related",
                                        help="Authors related to publisher",
                                        compute="compute_related_author")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env[
                                     'res.users'].browse(
                                     self.env.uid).company_id.id,
                                 help="The company to which the record"
                                      " belongs.")
    created_user_id = fields.Many2one('res.users', 'User Responsible',
                                      required=True, readonly=True,
                                      default=lambda self: self.env.uid,
                                      help="The user who created or is "
                                           "responsible for the record.")
    publisher_awards_ids = fields.One2many("publisher.award", "publisher_id",
                                           string="Publisher awards",
                                           help="Awards received by the "
                                                "publisher.")

    def compute_published_book(self):
        """ Compute number of published books """
        self.publisher_book_qty = self.env['product.template'].search_count(
            [('publisher_id', '=', self.id)])

    def compute_related_author(self):
        """ Compute number of related authors """
        self.related_author_qty = len(self.env['product.template'].search(
            [('publisher_id', '=', self.id)]).mapped('author_name.id'))

    def view_published_books(self):
        """ Function to published books """
        books = self.env['product.template'].search([])
        book_ids = []
        for book in books:
            if book.publisher_id.id == self.id:
                book_ids.append(book.id)
        action = \
            self.env.ref(
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

    def view_related_authors(self):
        """ Function view related users to the publisher """
        books = self.env['product.template'].search([])
        author_ids = []
        for book in books:
            if book.publisher_id.id == self.id:
                for author in book.author_name:
                    if author.id not in author_ids:
                        author_ids.append(author.id)
        action = \
            self.env.ref(
                'library_management_system.book_authors_action').read()[0]
        if len(author_ids) > 1:
            action['domain'] = [('id', 'in', author_ids)]
        elif len(author_ids) == 1:
            action['views'] = [
                (self.env.ref(
                    'library_management_system.book_authors_view_form').id,
                 'form')]
            action['res_id'] = author_ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
