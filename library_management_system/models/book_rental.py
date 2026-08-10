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


class BookRental(models.Model):
    """ Model for book rental details """
    _name = "book.rental"
    _description = "Book Rental details"

    book_id = fields.Many2one("product.template", string="Rental Pricing",
                              help="The book associated with the rental"
                                   " pricing.")
    from_day = fields.Integer(string="From", required=True,
                              help="From day to calculate rent")
    to_day = fields.Integer(string="To", required=True,
                            help="To day to calculate rent")
    duration = fields.Integer(string="Duration in Days", required=True,
                              help="One month is considered as 30 days")
    unit = fields.Selection([('days', 'Days'),
                             ('months', 'Months')], required=True,
                            help="The unit for the duration (days or months).")
    price = fields.Float(string="Price", required=True,
                         help="The price associated with the rental duration.")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env[
                                     'res.users'].browse(
                                     self.env.uid).company_id.id,
                                 help="The company associated with the "
                                      "record.")
    created_user_id = fields.Many2one('res.users', 'User Responsible',
                                      required=True, readonly=True,
                                      default=lambda self: self.env.uid,
                                      help="The user responsible for creating "
                                           "the record.")

    @api.onchange('from_day', 'to_day', 'unit')
    @api.depends('from_day', 'to_day', 'unit')
    def _onchange_from_day(self):
        """ compute number of days when corresponding fields changes """
        if not self.unit:
            self.unit = 'days'
        if self.unit == 'days':
            self.duration = self.to_day - self.from_day
        elif self.unit == 'months':
            months = self.to_day - self.from_day
            self.duration = months * 30
        else:
            self.duration = 0
