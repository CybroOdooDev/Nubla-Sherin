# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Gayathri V(odoo@cybrosys.com)
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
from odoo.exceptions import UserError


class CreateBook(models.Model):
    """Model to create and manage book details."""
    _name = 'create.book'
    _description = "Create Book"

    name = fields.Char(string="Book Name",
                       help="Enter the name of the book.")
    authors_ids = fields.Many2many(
        "book.author", string="Authors",
        help="Select one or more authors for the book.")
    title = fields.Char(string="Title",
                        help="Enter the title of the book.")
    publisher_id = fields.Many2one("book.publisher",
                                   string="Publisher",
                                   help="Select the publisher of the book.")
    description = fields.Text(string="Description",
                              help="Provide a brief description of the book.")
    isbn_13 = fields.Char(string="ISBN_13",
                          help="Enter the 13-digit ISBN of the book.")

    isbn_10 = fields.Char(string="ISBN_10",
                          help="Enter the 10-digit ISBN of the book.")
    pageCount = fields.Integer(string="PageCount",
                               help="Specify the total number of pages in"
                                    " the book.")
    categories = fields.Char(string="Categories",
                             help="Enter the categories or genres associated"
                                  " with the book.")
    averageRating = fields.Char(string="AverageRating",
                                help="Provide the average rating of the book.")
    webReaderLink = fields.Char(string="WebReaderLink",
                                help="Enter the web reader link for the book.")
    previewLink = fields.Char(string="PreviewLink",
                              help="Enter the preview link for the book.")
    image_medium = fields.Binary(store=True,
                                 attachment=True,
                                 help="Upload the medium-sized image of the"
                                      " book.")
    book_language = fields.Char(string="Language",
                                help="Specify the language in which the book"
                                     " is written.")
    company_id = fields.Many2one('res.company',
                                 'Company',
                                 default=lambda self: self.env[
                                     'res.users'].browse(
                                     self.env.uid).company_id.id,
                                 help="Select the company associated with "
                                      "the book.")

    def _check_isbn(self, isbn_10, isbn_13):
        """ Check whether isbn already exists
        :return book_isbn_found true if found in db
        :argument isbn_10 10 digit isbn number
        :argument isbn_13 13 digit isbn number"""
        product_obj = self.env['product.template'].search([])
        book_isbn_found = False
        for book in product_obj:
            if (isbn_10 and book.isbn_number == isbn_10) or (isbn_13 and book.isbn_13_number == isbn_13):
                book_isbn_found = True
        return book_isbn_found

    def create_book(self):
        """ Create a book with provided datas """
        isbn_found = self._check_isbn(self.isbn_10, self.isbn_13)
        if not isbn_found:
            product_obj = self.env['product.template']
            product_ctx = {
                'is_a_book': True,
                'type': 'consu',
                'name': self.name,
                'image_1920': self.image_medium,
                'book_title': self.title,
                'author_name': [(6, 0, [int(y.id) for y in self.authors_ids])],
                'pages': self.pageCount,
                'company_id': self.env.user.company_id.id,
                'isbn_number': self.isbn_10,
                'isbn_13_number': self.isbn_13,
                'publisher_id': self.publisher_id.id,
                'description': self.description,
                'categories': self.categories,
                'rating': self.averageRating,
                'web_reader_link': self.webReaderLink,
                'preview_link': self.previewLink,
                'book_language': self.book_language,
            }
            new_book = product_obj.create(product_ctx)
            category = self.env['product.category'].search(
                [('name', '=', 'Books')], limit=1)
            if category:
                new_book.update({'categ_id': int(category.id)})
        else:
            raise UserError("Book already exists in database")
