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


class LibraryMembershipType(models.Model):
    """ Model for storing library membership details """

    _name = "membership.type"
    _description = "Membership Type"
    _rec_name = "membership_name"

    membership_name = fields.Char(string="Membership Name", required=True,
                                  help="Name of the membership.")
    membership_product_id = fields.Many2one("product.product",
                                            "Renewal Product",
                                            help="If not selected automatically \
                                         create a product of this name",
                                            domain="[('is_a_book', '=', False)]")
    renewal_amount = fields.Float(string="Renewal Amount", required=True,
                                  help="Membership renewal amount")
    expires_in = fields.Integer(string="Expiry In Days", default=0,
                                help="Membership duration in days")
    is_expiry_email = fields.Boolean(string="Expiry email",
                                     help="Send email on membership expiry")
    is_do_not_expire = fields.Boolean(string="Do Not Expire",
                                      help="Will not expire membership")
    email_template_id = fields.Many2one("mail.template", default=lambda
        self: self._get_report_template(),
                                        help="Email template for membership"
                                             " actions.",
                                        string="Email Template")
    note = fields.Text(string="Extra notes",
                       help="Additional notes for the membership.")
    no_of_books = fields.Integer(string="No of books",
                                 help="No of books a user can hold at a time",
                                 default=0)
    is_restrict_books = fields.Boolean(string="Restrict book count",
                                       help="Restrict ni of book that can hold\
                                    at a time for a member")
    terms_conditions_ids = fields.One2many("membership.term", "membership_id",
                                           string="Terms and Conditions",
                                           help="Terms and conditions"
                                                " associated with the"
                                                " membership.")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env[
                                     'res.users'].browse(
                                     self.env.uid).company_id.id,
                                 help="The company associated with the record")
    created_user_id = fields.Many2one('res.users', 'User Responsible',
                                      required=True, readonly=True,
                                      default=lambda self: self.env.uid,
                                      help="The user responsible for creating"
                                           " the record.")



    @api.model_create_multi
    def create(self, vals_list):
        """ Create a product if no membership product selected """
        for vals in vals_list:
            if not vals.get('membership_product_id'):
                context = {
                    'name': vals['membership_name'],
                    'type': 'service',
                    'invoice_policy': 'order',
                    'company_id': self.env['res.users'].browse(
                        self.env.uid).company_id.id, }
                product = self.env['product.template'].create(context)
                vals['membership_product_id'] = product.id
        return super(LibraryMembershipType, self).create(vals_list)

    def _get_report_template(self):
        """ Get default email template for membership expiry """
        template = self.env.ref(
            'library_management_system.email_template_membership_expiry',
            raise_if_not_found=False)
        return template.id if template else False
