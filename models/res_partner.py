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
import logging
from datetime import date
from odoo import api, fields, models, _
from datetime import  timedelta


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """ Extend res_partner for library management """
    _inherit = 'res.partner'

    sex = fields.Selection([('male', 'Male'),
                            ('female', 'Female'),
                            ('other', 'Other')], string="Gender",
                           help="Gender of the Partner")
    member_type = fields.Selection([('life_long', 'Life Long'),
                                    ('monthly', 'Monthly Renewal'),
                                    ('visitor', 'Visitor')],
                                   required=True, string="Member Type",
                                   tracking=True,default='visitor',
                                   help="Type of library membership")
    is_a_member = fields.Boolean(string="Library Member",
                                 help="User is a member of library")
    member_sequence = fields.Char(string="Member ID", default="New",
                                  copy=False)
    is_membership_expired = fields.Boolean(string="Membership Status",
                                           default=True, copy=False,
                                           tracking=True)
    membership_expiry_date = fields.Date(string="Membership Expiry Date",
                                         default=fields.Date.today(),
                                         copy=False, tracking=True,
                                         help="Current membership expiry date")
    last_renewal_date = fields.Date(string="Last Renewal Date")
    membership_history_ids = fields.One2many("membership.history",
                                             "library_member_id", readonly=True)
    book_history_ids = fields.One2many("book.history",
                                       "member_book_history_id", readonly=True)
    due_amount_paid = fields.Integer("Due Amount", default=0)
    membership_type_id = fields.Many2one("membership.type",
                                         "Current Membership",
                                         help="Library Membership Type")
    book_count = fields.Integer(string="Currently holding Books",
                                help="No of books on hand")
    is_block_status = fields.Boolean(string="Block Status", default=False,
                                     help='Block status of member')
    created_company_id = fields.Many2one('res.company', 'Created Company',
                                         default=lambda self: self.env[
                                             'res.users'].browse(
                                             self.env.uid).company_id.id,
                                         help='Company name of member')
    created_user_id = fields.Many2one('res.users', 'User Responsible',
                                      required=True, readonly=True,
                                      default=lambda self: self.env.uid,
                                      help='Created user')
    auto_membership_renewal = fields.Boolean(
        string="Enable Automatic Membership Renewal",
        config_parameter='library_management_system.auto_membership_renewal',
        help="If enabled, all expired memberships will be renewed automatically."
    )

    @api.model_create_multi
    def create(self, vals_list):
        """ Create function supered which set register status as draft"""
        for vals in vals_list:
            try:
                sequence = self.env['ir.sequence'].with_context(
                    force_company=vals['company_id']).next_by_code(
                    'res.partner.member') or _('New')
                prefix = self.env['ir.config_parameter'].sudo().get_param(
                    'library_management_system.member_id_prefix')
                if prefix:
                    sequence = prefix + sequence
                suffix = self.env['ir.config_parameter'].sudo().get_param(
                    'library_management_system.member_id_suffix')
                if suffix:
                    sequence = sequence + suffix
                vals['member_sequence'] = sequence
            except Exception as e:
                _logger.info("# company_id not found %s" % e)
                pass
        return super(ResPartner, self).create(vals_list)

    @api.model
    def _valid_field_parameter(self, field, name):
        if name == 'config_parameter':
            return True
        return super()._valid_field_parameter(field, name)

    @api.onchange('is_a_member')
    @api.depends('is_a_member')
    def _onchange_is_a_member(self):
        """ Generate a member id when is a member is checked """
        if self.member_sequence == 'New' and self.is_a_member:
            company_id = self.company_id.id
            sequence = self.env['ir.sequence'].with_context(
                with_company=company_id).next_by_code(
                'res.partner.member') or _('New')
            prefix = self.env['ir.config_parameter'].sudo().get_param(
                'library_management_system.member_id_prefix')
            if prefix:
                sequence = prefix + sequence
            suffix = self.env['ir.config_parameter'].sudo().get_param(
                'library_management_system.member_id_suffix')
            if suffix:
                sequence = sequence + suffix
            self.member_sequence = sequence

    def action_renew_membership_wizard(self):
        """ Function to call action to view renew membership wizard """
        ctx = {
            'default_member_id': self.id,
            'default_membership_type_id': self.membership_type_id.id,
        }
        return {
            'name': _('Renew Membership'),
            'view_mode': 'form',
            'res_model': 'renew.membership',
            'type': 'ir.actions.act_window',
            'edit': False,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def _cron_mark_expired_members(self):
        """ Mark expired members and send notification """
        member_list = self.search([('is_a_member', '=', True)])
        for member in member_list:
            if not member.membership_type_id.is_do_not_expire:
                if not member.is_membership_expired and \
                        member.membership_expiry_date <= date.today():
                    # send email to customer
                    context = member._context.copy()
                    template_id = self.env.ref(
                        'library_management_system.email_template_membership_expiry')
                    template_id.with_context(context).sudo().send_mail(
                        member.id,
                        force_send=True)
                    member.is_membership_expired = True

    def action_view_book(self):
        """ View book on hand  """
        reg_items = self.env['book.register'].search([])
        reg_ids = []
        for each in reg_items:
            if each.register_member_id.id == self.id:
                reg_ids.append(each.id)
        action = \
        self.env.ref('library_management_system.book_register_action').read()[0]
        if len(reg_ids) > 1:
            action['domain'] = [('id', 'in', reg_ids),
                                ('register_status', 'in',
                                 ('issued', 'expired'))]
        elif len(reg_ids) == 1:
            action['views'] = [(self.env.ref(
                'library_management_system.book_register_view_form').id,
                                'form')]
            action['res_id'] = reg_ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def _get_late_members(self):
        """ Action late returning members """
        book_register = self.env['book.register'].search([])
        member_ids = []
        for reg in book_register:
            if reg.register_status == 'expired':
                member_ids.append(reg.register_member_id.id)
        value = {
            'domain': str([('id', 'in', member_ids)]),
            'view_mode': 'kanban,form',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'name': 'Late Members',
            'target': 'current',
            'context': {
                'default_is_a_member': True,
                'create': False,
                'edit': False,
            }
        }
        return value

    def action_block_member(self):
        """ Block members """
        self.is_block_status = True

    def action_unblock_member(self):
        """ Unblock members """
        self.is_block_status = False

    @api.model
    def get_late_member_ids(self):
        book_register = self.env['book.register'].search([('register_status', '=', 'expired')])
        member_ids = book_register.mapped('register_member_id.id')
        return member_ids

    @api.model
    def get_membership_expires_today(self):
        """Return the issued books expires tomorrow"""
        query = '''
            SELECT rp.id, rp.name AS member_name, 1 AS member_count
            FROM res_partner rp
            WHERE rp.membership_expiry_date = CURRENT_DATE
			  AND rp.is_a_member = True
              AND rp.is_membership_expired = TRUE
        '''
        self.env.cr.execute(query)
        membership_expires_today = self.env.cr.dictfetchall()
        member_name = [record.get('member_name') for record in
                       membership_expires_today]
        member_count = [record.get('member_count') for record in
                        membership_expires_today]
        member_id = [record.get('id') for record in
                     membership_expires_today]
        final = [member_count, member_name, member_id]
        return final

    def auto_renew_membership(self):
        self.ensure_one()
        print("AUto.....")
        membership_type = self.membership_type_id
        if not membership_type or not membership_type.expires_in:
            return False

        product = membership_type.membership_product_id
        if not product:
            return False

        journal_id = int(self.env['ir.config_parameter'].sudo()
                         .get_param('library_management_system.membership_journal_type_id') or 0)
        if not journal_id:
            return False

        # Create invoice
        inv_data = {
            'move_type': 'out_invoice',
            'partner_id': self.id,
            'journal_id': journal_id,
            'invoice_date_due': date.today(),
            'invoice_date': date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': product.name,
                'price_unit': membership_type.renewal_amount,
                'quantity': 1,
                'product_id': product.id,
            })]
        }
        invoice = self.env['account.move'].create(inv_data)
        print(invoice)
        invoice.action_post()

        # Extend expiry
        self.last_renewal_date = date.today()
        base_date = self.membership_expiry_date or date.today()
        new_expiry_date = base_date + timedelta(days=self.membership_type_id.expires_in)
        print(new_expiry_date)
        self.membership_expiry_date = new_expiry_date
        self.is_membership_expired = False


        # Create membership history
        self.env['membership.history'].create({
            'renewal_date': date.today(),
            'new_expiry_date': self.membership_expiry_date,
            'renewal_plan_id': membership_type.id,
            'library_member_id': self.id,
            'renewal_invoice_id': invoice.id,
        })


        return invoice

    def _cron_auto_membership_renewal(self):
        today = date.today()
        members = self.search([
            ('auto_membership_renewal', '=', True),
            ('membership_expiry_date', '<=', today),
            ('is_membership_expired', '=', True),
            ('membership_type_id', '!=', False)
        ])
        print("Memebrs",members)
        for member in members:
            template = self.env.ref(
                'library_management_system.mail_template_auto_membership_renewal',
                raise_if_not_found=False
            )
            if template:
                template.send_mail(member.id, force_send=True)
                member.auto_renew_membership()

