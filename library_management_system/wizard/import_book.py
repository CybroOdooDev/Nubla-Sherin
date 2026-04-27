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
import base64
import certifi
import json
import logging
import urllib3
from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ImportBook(models.TransientModel):
    """Wizard to import book details using Google Books API."""
    _name = 'import.book'
    _description = "Import Book"

    isbn_value = fields.Char(string="ISBN_13 / ISBN_10", required=True,
                             help="13 Digit ISBN number")

    book_found = fields.Boolean("Book Found", default=False,
                                help='Is book found or not')

    def import_book_wizard(self):
        """ Action showing wizard for importing book """
        return {
            'name': _('Import Book'),
            'view_mode': 'form',
            'res_model': 'import.book',
            'type': 'ir.actions.act_window',
            'edit': True,
            'target': 'new',
        }

    def get_book_details(self):
        """Get book details from API call using the ISBN number and book
        image from the thumbnail URL."""
        isbn = str(self.isbn_value)
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        ctx = {}

        try:
            # Make the API request
            response = http.request('GET', url)
            res = json.loads(response.data.decode("utf-8"))
            # Check if the quota is exceeded
            if res.get('error', {}).get('code') == 429:
                raise UserError(_("Quota exceeded. Please try again later or contact the administrator."))

            # Handle no results found
            if res['totalItems'] == 0:
                raise UserError(_("ISBN number not found. Please check the ISBN number you entered."))

            # Parse API response
            volume_info = res['items'][0]['volumeInfo']
            access_info = res['items'][0]['accessInfo']

            # Get book image
            image_thumbnail = None
            if 'imageLinks' in volume_info:
                image_response = http.request('GET', volume_info['imageLinks']['thumbnail'])
                image_thumbnail = base64.b64encode(image_response.data)

            # Process authors
            authors = []
            if 'authors' in volume_info:
                authors_obj = self.env['book.author'].search([])
                for author in volume_info['authors']:
                    existing_author = authors_obj.filtered(lambda a: a.author_name == author)
                    if existing_author:
                        authors.append(existing_author.id)
                    else:
                        new_author = self.env['book.author'].create({'author_name': author})
                        authors.append(new_author.id)

            # Process publisher
            publisher_obj = None
            if 'publisher' in volume_info:
                publisher_name = volume_info['publisher']
                publisher_obj = self.env['book.publisher'].search([("publisher_name", "=", publisher_name)], limit=1)
                if not publisher_obj:
                    publisher_obj = self.env['book.publisher'].create({'publisher_name': publisher_name})

            # Process categories
            categories = ", ".join(volume_info.get('categories', []))

            # Update context
            ctx.update({
                'default_name': volume_info.get('title', ""),
                'default_title': volume_info.get('title', ""),
                'default_authors_ids': [(6, 0, authors)],
                'default_description': volume_info.get('description', ""),
                'default_isbn_13': next(
                    (identifier['identifier'] for identifier in volume_info.get('industryIdentifiers', [])
                     if identifier.get('type') == 'ISBN_13'), ""),
                'default_isbn_10': next(
                    (identifier['identifier'] for identifier in volume_info.get('industryIdentifiers', [])
                     if identifier.get('type') == 'ISBN_10'), ""),
                'default_pageCount': volume_info.get('pageCount', 0),
                'default_webReaderLink': access_info.get('webReaderLink', ""),
                'default_previewLink': volume_info.get('previewLink', ""),
                'default_book_language': volume_info.get('language', ""),
                'default_image_medium': image_thumbnail or "",
                'default_categories': categories,
                'default_publisher_id': publisher_obj.id if publisher_obj else False,
                'default_averageRating': volume_info.get('averageRating', 0),
            })

        except json.JSONDecodeError:
            raise UserError(_("Failed to decode API response. Please check the API or your connection."))
        except urllib3.exceptions.HTTPError as e:
            raise UserError(_("Failed to connect to the Google Books API. Error: %s") % e)
        except Exception as e:
            raise UserError(_("An unexpected error occurred: %s") % e)

        # Return action for creating a book
        return {
            'name': _('Import Book'),
            'view_mode': 'form',
            'res_model': 'create.book',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
            'params': {'edit': False},
        }

