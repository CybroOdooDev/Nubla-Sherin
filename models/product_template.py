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
from odoo import api, fields, models


class ProductTemplate(models.Model):
    """ Extend product template for library management """
    _inherit = 'product.template'
    _description = "Library Books"

    author_name = fields.Many2many("book.author", string="Authors",
                                   help="Author name")
    isbn_number = fields.Char(string="ISBN_10", copy=False,
                              help="International Standard Book Number \
                              (ISBN_10)")
    isbn_13_number = fields.Char(string="ISBN_13",
                                 help="International Standard "
                                      "Book Number(ISBN_13)")
    publisher_id = fields.Many2one("book.publisher",
                                   string="Publisher Information",
                                   help="Publisher details of the book")
    copyright = fields.Char(string="Copyright owner",
                            help="Copyright details of the book")
    edition = fields.Char(string="Edition details",
                          help="Edition details")
    book_title = fields.Char(string="Book Title",
                             help="Book title")
    pages = fields.Integer(string="Page Number",
                           help="Page number")
    issue_status = fields.Selection([('available', 'Available'),
                                     ('unavailable', 'Unavailable')],
                                    string="Status", help="Status of issue")
    is_a_book = fields.Boolean(string="Is a Book", default=False,
                               help="Enable to use the product as abook")
    categories = fields.Char(string="Categories", help="Book categories")
    rating = fields.Char(string="Rating", help="Rating for the book")
    web_reader_link = fields.Char(string="Web Reader Link",
                                  help="The link to access the book through"
                                       " a web reader.")
    preview_link = fields.Char(string="Preview Link",
                               help="The link to preview the book.")
    book_language = fields.Char(string="Language",
                                help="The language of the book.")
    is_pricing = fields.Boolean(string="Provide Pricing",
                                help="Select to define rental \
                                    amount for the book")
    rental_price_ids = fields.One2many("book.rental", "book_id",
                                       string="Rental Pricing",
                                       help="The rental pricing details for"
                                            " the book.")
    issued_history_ids = fields.One2many("issued.history",
                                         "book_issued_history_id",
                                         help="History of book issuance's.")
    book_awards_ids = fields.One2many("book.award", "book_awards_id",
                                      string="Book awards",
                                      help="Awards associated with the book.")

    @api.onchange('is_a_book')
    def onchange_is_a_book(self):
        """ Change to product when is a book is selected and also select
        book category"""
        if self.is_a_book:
            category = self.env['product.category'].search(
                [('name', '=', 'Books')], limit=1)
            if category:
                self.categ_id = int(category.id)
            self.type = 'consu'

    @api.model
    def get_data(self):
        """Returns data to the dashboard tiles"""
        late_members_count = self.env['res.partner'].get_late_member_ids()
        return {
            'books_count': self.search_count([('is_a_book', '=', True)]),
            'borrowed_books': self.env['book.register'].search_count([]),
            'returned_books': self.env['book.register'].search_count([('register_status', '=', 'returned')]),
            'issued_books': self.env['book.register'].search_count([('register_status', '=', 'issued')]),
            'members': self.env['res.partner'].search_count([('is_a_member', '=', True)]),
            'expired_books': self.env['book.register'].search_count([('register_status', '=', 'expired')]),
            'late_members': len(late_members_count),
            'authors': self.env['book.author'].search_count([])
        }

    @api.model
    def get_most_issue_books(self):
        """return the most issued books"""
        query = '''SELECT 
                pt.id,
                pt.name ->> 'en_US' as book_name,
                pp.default_code as isbn,
                COUNT(br.id) as issue_count
            FROM 
                book_register br
            INNER JOIN 
                product_product pp ON br.book_id = pp.id
            INNER JOIN 
                product_template pt ON pp.product_tmpl_id = pt.id
            WHERE 
                br.register_status IN ('issued', 'expired', 'returned')
                AND br.company_id = ''' + str(self.env.company.id) + '''
            GROUP BY 
                pt.id, pp.id
            ORDER BY 
                issue_count DESC
            LIMIT 10 '''
        self.env.cr.execute(query)
        top_books = self.env.cr.dictfetchall()
        print(top_books)
        total_quantity = [record.get('issue_count') for record in
                          top_books]
        book_name = [record.get('book_name') for record in top_books]
        book_id = [record.get('id') for record in top_books]
        final = [total_quantity, book_name, book_id]
        return final

    @api.model
    def get_most_popular_books(self):
        query = '''
            SELECT 
                pt.id,
                pt.name ->> 'en_US' as book_name,
                pp.default_code as isbn,
                COUNT(br.id) as issue_count
            FROM 
                book_register br
            INNER JOIN 
                product_product pp ON br.book_id = pp.id
            INNER JOIN 
                product_template pt ON pp.product_tmpl_id = pt.id
            WHERE 
                br.register_status IN ('issued', 'expired', 'returned')
                AND br.company_id = %s
            GROUP BY 
                pt.id, pp.id
            ORDER BY 
                issue_count DESC
            LIMIT 3
        '''
        self.env.cr.execute(query, (self.env.company.id,))
        rows = self.env.cr.dictfetchall()
        return rows

