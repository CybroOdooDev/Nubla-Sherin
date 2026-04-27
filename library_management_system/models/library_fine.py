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
from odoo import models, fields, api
from odoo.exceptions import UserError


class LibraryFine(models.Model):
    """ Class for Storing library fine"""
    _name = 'library.fine'
    _description = "Library Fine"
    _rec_name = 'member_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    member_id = fields.Many2one("res.partner", string="Member",
                                domain="[('is_a_member','=',True)]",
                                required=True)
    book_register_id = fields.Many2one("book.register", string="Book Register")
    rule_id = fields.Many2one("library.fine.rule", string="Fine Rule")
    fine_date = fields.Date("Fine Date", default=fields.Date.context_today,store=True)
    original_amount = fields.Float(
        "Original Fine",
        related="rule_id.fine_amount",
        store=True,
        readonly=False
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True, copy=False)

    waived_amount = fields.Float("Waived Amount", default=0.0, help="Part of fine forgiven")
    adjusted_amount = fields.Float("Adjusted Fine", compute="_compute_adjusted_amount",
                                   inverse="_inverse_adjusted_amount", store=True,
                                   help="Final payable amount after waiver/adjustment" , readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
    ], default='draft',store=True,compute="_compute_state")
    note = fields.Text("Remarks")

    @api.depends('original_amount', 'waived_amount')
    def _compute_adjusted_amount(self):
        for rec in self:
            rec.adjusted_amount = max(rec.original_amount - rec.waived_amount, 0.0)

    def _inverse_adjusted_amount(self):
        for rec in self:
            rec.waived_amount = max(rec.original_amount - rec.adjusted_amount, 0.0)

    @api.depends('invoice_id.payment_state')
    def _compute_state(self):
        for fine in self:
            if fine.invoice_id:
                if fine.invoice_id.payment_state == 'paid':
                    fine.state = 'paid'
                else:
                    fine.state = 'confirmed'
            else:
                fine.state = 'draft'
    @api.model
    def _cron_generate_late_fines(self):
        today = fields.Date.today()
        late_books = self.env["book.register"].search([
            ('register_status', '=', 'expired')
        ])

        late_rule = self.env["library.fine.rule"].search([
            ('fine_type', '=', 'late_return'),

        ], limit=1)

        for book in late_books:
            # Avoid duplicate fines
            existing_fine = self.env["library.fine"].search([
                ('book_register_id', '=', book.id),
                ('rule_id', '=', late_rule.id)
            ], limit=1)
            if existing_fine:
                continue

            # Calculate fine
            fine_amount = late_rule.fine_amount
            if late_rule.amount_type == 'per_day' and book.returned_date:
                days_late = (today - book.returned_date).days
                fine_amount = max(0, days_late) * late_rule.fine_amount  # avoid negative


            fine = self.create({
                'member_id': book.register_member_id.id,
                'book_register_id': book.id,
                'rule_id': late_rule.id,
                'adjusted_amount': fine_amount,
                'waived_amount': 0.0,
                'state': 'draft',
            })

            # Send email if template exists
            template = self.env.ref('library_management_system.email_template_library_fine', raise_if_not_found=False)
            if template and book.register_member_id.email:
                template.send_mail(fine.id, force_send=True)

    def action_create_invoice(self):
        for fine in self:
            if fine.invoice_id:
                raise UserError("An invoice is already created for this fine.")


            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
            if not journal:
                raise UserError("No Sales Journal found. Please configure one in Accounting.")

            # find income account
            account = journal.default_account_id or self.env['account.account'].search([
                ('user_type_id.type', '=', 'income')
            ], limit=1)
            if not account:
                raise UserError("No income account available for fines. Please configure one.")

            # build invoice values
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': fine.member_id.id,
                'invoice_date': fields.Date.today(),
                'journal_id': journal.id,
                'invoice_line_ids': [(0, 0, {
                    'name': f"Library Fine - {fine.rule_id.name}",
                    'quantity': 1,
                    'price_unit': fine.adjusted_amount or fine.original_amount,
                    'account_id': account.id,
                })]
            }

            invoice = self.env['account.move'].create(invoice_vals)
            fine.invoice_id = invoice.id

            fine.state = 'confirmed'

            return {
                'type': 'ir.actions.act_window',
                'name': 'Invoice',
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': invoice.id,
                'target': 'current',
            }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'domain': [('id', 'in', self.invoice_id.ids)],
            'target': 'current',
        }
