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
from datetime import date, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RenewMembership(models.TransientModel):
    _name = 'renew.membership'
    _description = "Renew Membership"

    member_id = fields.Many2one("res.partner", required=True,
                             string="Member", help='Choose member')
    membership_id = fields.Char(string="Membership ID", help='Membership id')
    membership_type_id = fields.Many2one("membership.type",
                                         string="Membership Type",
                                         required=True,
                                         help='Select start date')
    renewal_amount = fields.Integer(string='Renewal Amount',
                                    help='Membership renewal amount')
    expiry_date = fields.Date(string='Next Expiry',
                              help='Expiry date of membership')

    @api.depends('membership_type_id')
    @api.onchange('membership_type_id')
    def _onchange_membership_type_id(self):
        """ Get membership data on change on type """
        self.renewal_amount = self.membership_type_id.renewal_amount
        self.expiry_date = date.today() + timedelta(
            days=int(self.membership_type_id.expires_in))

    @api.depends('member_id')
    @api.onchange('member_id')
    def _onchange_member_id(self):
        """ Get membership id on """
        self.membership_id = self.member_id.member_sequence

    def renew_membership(self):
        """ Renew membership and create invoice for renewal if no product is
         defined for membership create a product and assign value
         to membership and also update next renewal date """
        try:
            active_id = self.env.context.get('active_id')
            member_obj = self.env['res.partner'].browse(active_id)
            membership_journal = self.env['ir.config_parameter'] \
                                     .sudo().get_param(
                'library_management_system.membership_journal_type_id') or False
            if not membership_journal:
                raise UserError(
                    _("Please select a membership journal from configuration."))
            if not self.membership_type_id.membership_product_id:
                membership_product_id = self.env['product.product'].search(
                    [("name", "=", self.membership_type_id.membership_name)])
                if not membership_product_id:
                    context = {
                        'name': self.membership_type_id.membership_name,
                        'type': 'service',
                        'invoice_policy': 'order',
                        'company_id': self.env['res.users'].browse(
                            self.env.uid).company_id.id,
                    }
                    product = self.env['product.product'].sudo().create(
                        context)
                else:
                    product = membership_product_id.sudo()
                self.membership_type_id.membership_product_id = product.id or False
            else:
                product = self.sudo().membership_type_id.membership_product_id
            if product.sudo().property_account_income_id.id:
                income_account = product.sudo().property_account_income_id.id
            elif product.sudo().categ_id.property_account_income_categ_id.id:
                income_account = product.sudo().categ_id.property_account_income_categ_id.id
            else:
                raise UserError(
                    'Please define income account for this \
                    product: "%s" (id:%d).' %
                    (product.name, product.id))
            inv_line_data = [(0, 0, {
                'name': product.name,
                'account_id': income_account,
                'price_unit': self.membership_type_id.renewal_amount,
                'quantity': 1,
                'product_id': product.id,
            })]
            inv_data = {
                'name': '/',
                'move_type': 'out_invoice',
                'partner_id': member_obj.id,
                'journal_id': int(membership_journal),
                'invoice_origin': member_obj.member_sequence,
                'invoice_date_due': date.today(),
                'invoice_date': date.today(),
                'invoice_line_ids': inv_line_data
            }
            invoice_obj = self.env['account.move'].create(inv_data)
            invoice_obj.action_post()
            self.member_id.membership_type_id = self.membership_type_id.id
            self.member_id.last_renewal_date = date.today()
            self.member_id.membership_expiry_date = self.expiry_date
            self.member_id.is_membership_expired = False
            history = {
                'renewal_date': date.today(),
                'new_expiry_date': self.expiry_date,
                'renewal_plan_id': int(self.membership_type_id.id),
                'library_member_id': int(self.member_id.id),
                'renewal_invoice_id': invoice_obj.id,
            }
            self.env['membership.history'].create(history)
            invoice = {
                'name': _('Invoice'),
                'view_mode': 'form',
                'res_id': int(invoice_obj.id),
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'target': 'new'}
            return invoice
        except Exception as e:
            raise UserError("Error %s" % e)



