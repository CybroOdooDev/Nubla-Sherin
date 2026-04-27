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


class PublisherAward(models.Model):
    """ Class for storing publisher awards """
    _name = "publisher.award"
    _description = "Publisher Award"
    _rec_name = "award_name"

    award_id = fields.Many2one("library.award", string="Award Id",
                               required=True, help="Select the award for"
                                                   " the book.")
    award_name = fields.Char(string="Award Name", help="Name of the award.")
    awarded_on = fields.Date(string="Awarded On", help="Date when the award "
                                                       "was received.")
    image_medium = fields.Binary(help="image for award", string="Image")
    country_id = fields.Many2one("res.country", string="Country",
                                 help="Country for award")
    awarded_by = fields.Char(string="Awarded by ", help="Name or entity that "
                                                        "awarded the prize.")
    ribbon = fields.Binary(string="Ribbon", help="Ribbon for the award")
    next = fields.Char(string="Next (higher)", help="Next higher award")
    lower = fields.Char(string="Next (lower)", help="Next lower award")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env[
                                     'res.users'].browse(
                                     self.env.uid).company_id.id,
                                 help="Default Company Id")
    created_user_id = fields.Many2one('res.users', 'User Responsible',
                                      required=True, readonly=True,
                                      default=lambda self: self.env.uid,
                                      help="Default user id")
    publisher_id = fields.Many2one("book.publisher",
                                   string="Publisher", help="Publisher"
                                                            " associated with"
                                                            "the award.")

    @api.onchange("award_id")
    @api.depends("award_id")
    def _onchange_award_id(self):
        """ Get award details on award id change """
        self.image_medium = self.award_id.image_medium
        self.country_id = self.award_id.country_id
        self.awarded_by = self.award_id.awarded_by
        self.ribbon = self.award_id.ribbon
        self.next = self.award_id.next
        self.lower = self.award_id.lower
        self.award_name = self.award_id.award_name
