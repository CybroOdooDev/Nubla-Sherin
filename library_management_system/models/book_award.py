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
from odoo import api, fields, models


class BookAward(models.Model):
    """ Class for storing book awards """
    _name = "book.award"
    _description = "Book Award"
    _rec_name = "book_award_name"

    book_award_id = fields.Many2one("library.award", string="Award ID",
                               help="Reference to the specific award.")
    book_award_name = fields.Char(string="Award Name",
                             help="Name of the award received by the author.")
    awarded_on = fields.Date(string="Awarded On",
                             help="Date on which the award was received.")
    image_medium = fields.Binary(help="image for award", string="Image")
    country_id = fields.Many2one("res.country", string="Country",
                                 help="Country for award")
    awarded_by = fields.Char(string="Awarded by",
                             help="The entity or organization that presented"
                                  " the award.")
    ribbon = fields.Binary(string="Ribbon", help="Ribbon for the award")
    next = fields.Char(string="Next (higher)", help="Next higher award")
    lower = fields.Char(string="Next (lower)", help="Next lower award")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env[
                                     'res.users'].browse(
                                     self.env.uid).company_id.id,
                                 help="The company to which the record "
                                      "belongs.")
    created_user_id = fields.Many2one('res.users', 'User Responsible',
                                      required=True, readonly=True,
                                      default=lambda self: self.env.uid,
                                      help="The user who created or is "
                                           "responsible for the record.")
    book_awards_id = fields.Many2one("product.template", string="Book",
                                     help="The book associated with the "
                                          "awards.")

    @api.onchange("book_award_id")
    @api.depends("book_award_id")
    def _onchange_award_id(self):
        """ Get award details on award id change """
        self.image_medium = self.book_award_id.image_medium
        self.country_id = self.book_award_id.country_id
        self.awarded_by = self.book_award_id.awarded_by
        self.ribbon = self.book_award_id.ribbon
        self.next = self.book_award_id.next
        self.lower = self.book_award_id.lower
        self.book_award_name = self.book_award_id.award_name
