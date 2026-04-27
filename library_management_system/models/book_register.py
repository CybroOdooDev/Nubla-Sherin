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
import logging
from datetime import date, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class BookRegister(models.Model):
    """ Class for library management book register"""
    _name = "book.register"
    _description = "Library Book Register"
    _rec_name = 'register_sequence'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_default_return_date(self):
        """ Function to get the default return date """
        auto_calc_return = self.env['ir.config_parameter'].sudo().get_param(
            'library_management_system.is_auto_calc_return')
        if auto_calc_return:
            days_count = self.env['ir.config_parameter'].sudo().get_param(
                'library_management_system.return_in_days')
            date = fields.Date.today() + timedelta(
                days=int(days_count))
        else:
            date = False
        return date

    register_sequence = fields.Char(string='Register ID', copy=False,
                                    default="New",
                                    help="Sequence for the register")
    book_image = fields.Binary(
        "Image", attachment=True,
        help="This field holds the image used as image "
             "for the product, product_template_action limited to 1024x1024px.")
    book_id = fields.Many2one("product.product",
                              string="Book name",
                              help="Name of the book",
                              required=True,
                              domain="[('is_a_book', '=', True)]")
    register_book_title = fields.Char(string="Title", help="Book title",
                                      readonly=True)
    author_ids = fields.Many2many("book.author", string="Authors",
                                  help="Author name",
                                  readonly=True)
    register_isbn_number = fields.Char(string="ISBN_10",
                                       help="International Standard "
                                            "Book Number")
    register_isbn_13_number = fields.Char(string="ISBN_13",
                                          help="International Standard "
                                               "Book Number")
    register_edition = fields.Char(string="Edition details",
                                   help="Edition details", readonly=True)
    register_member_id = fields.Many2one("res.partner",
                                         string="Book holder",
                                         required=True, tracking=True,
                                         domain="[('is_a_member', '=', True), ('is_membership_expired', '=', False)]",
                                         help="The member who holds the book.")
    register_member_nn = fields.Char(string="Member Id", help="The "
                                                              "identification "
                                                              "number of the"
                                                              " member.")
    issued_date = fields.Date(string="Book issued date", required=True,
                              default=fields.Date.context_today,
                              help="The date when the book was issued.")
    calc_return_date = fields.Date(string="Expected return date",
                                   required=True,
                                   readonly=False,
                                   help="Calculated return date, after \
                                   the issued book become expired",
                                   tracking=True, default=lambda self: self._get_default_return_date())
    returned_date = fields.Date(string="Returned date", readonly=False,
                                help="Actual returned date after \
                                becoming due ", copy=False)
    register_status = fields.Selection([('draft', 'Draft'),
                                        ('issued', 'Issued'),
                                        ('expired', 'Expired'),
                                        ('returned', 'Returned')],
                                       default="draft",
                                       string="Register status",
                                       tracking=True, help="Status of "
                                                           "Registration")
    register_note = fields.Text(string="Notes", help="Extra notes")
    book_qty_available = fields.Integer(string="Available book quantity",
                                        copy=False,
                                        compute="get_available_qty",
                                        help="Quantity Available for Book")
    is_book_selected = fields.Boolean(string="Book selected", default=False,
                                      help="Indicates whether a book is "
                                           "selected.")
    is_membership_expired = fields.Boolean(string="Membership Status",
                                           default=False,
                                           help="Indicates the membership "
                                                "status.")
    responsive_person_id = fields.Many2one('res.users',
                                           'Responsible',
                                           required=True, readonly=True,
                                           default=lambda self: self.env.uid,
                                           help="The responsible person for "
                                                "the record.")
    company_id = fields.Many2one('res.company',
                                 'Company',
                                 default=lambda self: self.env['res.users']
                                 .browse(self.env.uid).company_id.id,
                                 help="The company associated with the record.")
    book_due = fields.Integer("Due amount", required=True, default=0,
                              copy=False, tracking=True,
                              help="The amount due for books.")
    invoiced_due = fields.Integer("Invoiced", required=True, default=0,
                                  copy=False, tracking=True,
                                  help="The invoiced amount.")
    current_book_count = fields.Integer(string="Currently holding Books",
                                        help="No of books on hand",
                                        compute="compute_cur_book_count")
    is_block_status = fields.Boolean(string="Member Block Status",
                                     default=False,
                                     help="Indicates the block status of the"
                                          " member.")

    fine_ids = fields.One2many(
        "library.fine", "book_register_id", string="Fines"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """ Create function supered which set register status as draft and
        also get register sequence number and change state if expired """
        for vals in vals_list:
            vals['company_id'] = self.env['res.users'].browse(
                self.env.uid).company_id.id
            vals['register_status'] = 'draft'
            vals['register_sequence'] = self.env['ir.sequence'].with_context(
                with_company=vals['company_id']).next_by_code(
                'book.register') or _('New')
        return super().create(vals_list)

    @api.onchange('book_id')
    def _change_book_id(self):
        """ Function works when book name changes which finds available
                 quantity of the book and also get book properties"""
        if self.book_id:
            self.is_book_selected = True
            book = self.book_id
            self.author_ids = book.author_name
            self.register_isbn_number = book.isbn_number
            self.register_isbn_13_number = book.isbn_13_number
            self.register_book_title = book.book_title
            self.register_edition = book.edition
            self.book_image = book.image_1920
            self.book_qty_available = book.qty_available or 0

    def get_available_qty(self):
        """ Compute book available """
        if self.book_id:
            self.book_qty_available = self.book_id.qty_available
        else:
            self.book_qty_available = 0

    def compute_cur_book_count(self):
        """ Compute currently holding book count of member """
        if self.register_member_id:
            self.current_book_count = self.register_member_id.book_count
        else:
            self.current_book_count = 0

    @api.onchange('issued_date')
    def _onchange_issued_date(self):
        """ Function works when issued date changes which calculate return
        date and set to corresponding field """
        if self.register_status == 'draft':
            auto_calc_return = self.env['ir.config_parameter'].sudo().get_param('library_management_system.is_auto_calc_return')
            if auto_calc_return:
                days_count = self.env['ir.config_parameter'].sudo().get_param('library_management_system.return_in_days')
                self.calc_return_date = self.issued_date + timedelta(
                    days=int(days_count))

    @api.onchange('register_member_id')
    def _onchange_register_member_id(self):
        """ Function to get membership id and expired status
        when a member is selected """
        self.register_member_nn = self.register_member_id.member_sequence
        self.is_membership_expired = self.register_member_id.is_membership_expired
        self.current_book_count = self.register_member_id.book_count
        self.is_block_status = self.register_member_id.is_block_status

    def action_find_book(self):
        """ Function to search book by ISBN """
        if not self.register_isbn_number:
            raise UserError(
                "ISBN number not found, please check the ISBN number you have "
                "entered")
        book_rec = self.env['product.product'].search([
            ('isbn_number', '=', self.register_isbn_number)
        ], limit=1)
        if not book_rec:
            raise UserError(
                "ISBN number not found, please check the ISBN number "
                "you have entered")
        self.book_id = book_rec.id
        if self.book_id:
            self.is_book_selected = True
            self.author_ids = book_rec.author_name
            self.register_isbn_number = book_rec.isbn_number
            self.register_book_title = book_rec.book_title
            self.register_edition = book_rec.edition
            self.book_image = book_rec.image_1920
            self.book_qty_available = book_rec.qty_available or 0

    def action_find_member(self):
        """ Function to search member by id """
        if not self.register_member_nn:
            raise UserError(
                "Member ID not found, please check the ID you have entered")
        member = self.env['res.partner'].search(
            [('member_sequence', '=', self.register_member_nn)], limit=1)
        if not member:
            raise UserError(
                "Member ID not found, please check the ID you have entered")
        self.register_member_id = member.id
        self.register_member_nn = self.register_member_id.member_sequence
        self.is_membership_expired = self.register_member_id.is_membership_expired
        self.current_book_count = self.register_member_id.book_count

    def action_issue_book(self):
        """ Issue book if copy available and membership is not expired """
        if self.book_qty_available > 0:
            if self.register_member_id.membership_type_id.is_restrict_books and \
                    self.register_member_id.book_count + 1 > \
                    self.register_member_id.membership_type_id.no_of_books:
                raise UserError(
                    "Selected member has reached no of on hand book count")
            try:
                self.action_post_move()
                if str(date.today()) > str(self.calc_return_date):
                    self.register_status = 'expired'
                else:
                    self.register_status = 'issued'
                val = {
                    'book_name_id': int(self.book_id),
                    'member_book_history_id': int(self.register_member_id),
                    'register_sequence': self.register_sequence,
                    'register_reference_id': int(self.id),
                    'issued_date': self.issued_date,
                    'expiry_date': self.calc_return_date,
                    'book_isbn': self.register_isbn_number,
                    'edition': self.register_edition,
                }
                self.env['book.history'].create(val)
                issued_obj = self.env['issued.history'].create(val)
                issued_obj.update(
                    {'book_issued_history_id': self.book_id.product_tmpl_id.id})
                self.register_member_id.book_count += 1
            except Exception as e:
                raise UserError("Error %s" % e)
        else:
            raise UserError(
                "Cannot Issue book check whether\n"
                "- Check Available book copies for issuing \n"
                "- Membership expired for the selected member")

    def action_renew_book(self):
        """ Renew issued book """
        self.issued_date = date.today()
        auto_calc_return = self.env['ir.config_parameter'].sudo().get_param \
            ('library_management_system.is_auto_calc_return')
        if auto_calc_return:
            days_count = self.env['ir.config_parameter'].sudo().get_param \
                ('library_management_system.return_in_days')
            self.calc_return_date = self.issued_date + timedelta(
                days=int(days_count))
        else:
            self.calc_return_date = date.today()
        self.register_status = 'issued'

    def action_return_book(self):
        """ Mark book return and update available book quantity """
        if self.book_due > self.invoiced_due:
            raise UserError(
                "The selected book is on due please clear the due \
                amount to return.")
        self.action_post_move()
        self.returned_date = date.today()
        self.register_status = 'returned'
        self.register_member_id.book_count -= 1

    def action_view_book(self):
        """ Function to view book details from the register """
        value = {'name': _('Book details'),
                 'view_mode': 'form',
                 'res_id': int(self.book_id),
                 'res_model': 'product.product',
                 'type': 'ir.actions.act_window',
                 'target': 'new'}
        return value

    @api.model
    def _cron_mark_expired_register(self):
        """ Mark expired register book and send notification and also
        calculate due amount"""
        book_register = self.env['book.register'].search([])
        due_amount = self.env['ir.config_parameter'].sudo().get_param(
            'library_management_system.daily_due_amount', default=0)
        for reg_item in book_register:
            if reg_item.register_status == 'issued' \
                    and date.today() > reg_item.calc_return_date:
                reg_item.register_status = 'expired'
                context = self._context.copy()
                template_id = self.env.ref(
                    'library_management_system.email_template_book_expiry')
                template_id.with_context(context).sudo().send_mail(reg_item.id,
                                                                   force_send=True)
                _logger.info("book expired with id-%s on-%s",
                             reg_item.register_sequence,
                             reg_item.calc_return_date)
            if reg_item.register_status == 'expired':
                old_due = reg_item.book_due
                today_due = int(
                    (date.today() - reg_item.calc_return_date).days
                ) * int(due_amount)
                reg_item.book_due += (today_due - old_due)
                reg_item.register_member_id.due_amount_paid += \
                    (today_due - old_due)

    def action_invoice_due_amount(self):
        """ Function to create invoice if the issued book is expired and due
        and show created invoice """
        if self.book_due <= 0:
            raise UserError(
                _("No due amount to invoice"))
        if self.invoiced_due < self.book_due:
            if not self.env['product.product'].search(
                    [("name", "=", "Library Due")]):
                context = self.prepare_advance_product()
                due_product = self.env['product.product'].sudo().create(
                    context)
            else:
                due_product = self.env['product.product'].search(
                    [("name", "=", "Library Due")])
            due_journal = self.env['ir.config_parameter'].sudo().get_param(
                'library_management_system.due_journal_type_id') or False
            if not due_journal:
                raise UserError(
                    _("Please select a due journal from configuration"))
            if due_product.property_account_income_id.id:
                income_account = due_product.property_account_income_id.id
            elif due_product.categ_id.property_account_income_categ_id.id:
                income_account = (due_product.categ_id
                                  .property_account_income_categ_id.id)
            else:
                raise UserError(
                    'Please define income account for this product: '
                    '"%s" (id:%d).' %
                    (due_product.name, due_product.id))
            inv_line_data = [(0, 0, {
                'name': due_product.name,
                'account_id': income_account,
                'price_unit': self.book_due - self.invoiced_due,
                'quantity': 1,
                'product_id': due_product.id,
            })]
            inv_data = {
                'name': '/',
                'move_type': 'out_invoice',
                'partner_id': self.register_member_id.id,
                'journal_id': int(due_journal),
                'invoice_origin': self.register_sequence,
                'invoice_date_due': date.today(),
                'invoice_date': date.today(),
                'invoice_line_ids': inv_line_data
            }
            invoice_obj = self.env['account.move'].create(inv_data)
            invoice_obj.action_post()
            self.invoiced_due += self.book_due - self.invoiced_due
            value = {'name': _('Invoice'),
                     'view_mode': 'form',
                     'res_id': int(invoice_obj.id),
                     'res_model': 'account.move',
                     'type': 'ir.actions.act_window',
                     'target': 'new'}
            return value
        raise UserError(
            _("No due amount to invoice"))

    def prepare_advance_product(self):
        """ Returns context for creating product for invoicing due amount """
        return {
            'name': 'Library Due',
            'type': 'service',
            'invoice_policy': 'order',
            'company_id': self.env['res.users'].browse(
                self.env.uid).company_id.id,
        }

    def action_view_due_invoice(self):
        """ View all invoices associated with a register book """
        inv_obj = self.env['account.move'].search(
            [('invoice_origin', '=', self.register_sequence)])
        inv_ids = []
        for each in inv_obj:
            inv_ids.append(each.id)
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(inv_ids) > 1:
            action['domain'] = [('id', 'in', inv_ids)]
        elif len(inv_ids) == 1:
            action['views'] = [
                (self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = inv_ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def unlink(self):
        """ Super unlink function to prevent deletion of record which is not
         in draft state """
        for i in self:
            if i.register_status != 'draft':
                raise UserError(
                    _('You cannot delete an issued register item.'))
        return super(BookRegister, self).unlink()

    @api.model
    def _default_picking_transfer(self):
        """ default picking transfer for issuing book """
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get(
            'company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'outgoing'),
                                 ('warehouse_id.company_id', '=', company_id)],
                                limit=1)
        if not types:
            types = type_obj.search(
                [('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
        return types[:4]

    @api.model
    def _default_picking_transfer_return(self):
        """ default picking transfer for return book """
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get(
            'company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'incoming'),
                                 ('warehouse_id.company_id', '=', company_id)],
                                limit=1)
        if not types:
            types = type_obj.search(
                [('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return types[:4]

    def action_post_move(self):
        """ Function to post book stock move when issuing  and
        returning books"""
        if self.register_status == "draft":
            picking_transfer_id = self._default_picking_transfer()
            origin = self.register_sequence
            src_loc = self.register_member_id.property_stock_customer.id
            dest_loc = picking_transfer_id.default_location_src_id.id
        else:
            picking_transfer_id = self._default_picking_transfer_return()
            origin = "Ret " + self.register_sequence
            src_loc = picking_transfer_id.default_location_dest_id.id
            dest_loc = self.register_member_id.property_stock_customer.id
        pick = {
            'picking_type_id': picking_transfer_id.id,
            'partner_id': self.register_member_id.id,
            'origin': origin,
            'location_dest_id': src_loc,
            'location_id': dest_loc,
        }
        picking = self.env['stock.picking'].create(pick)
        move = self._create_stock_moves_transfer(picking, src_loc, dest_loc)
        picking.action_assign()
        for move in move:
            move.quantity = move.product_qty
        picking.button_validate()

    def _create_stock_moves_transfer(self, picking, src_loc, dest_loc):
        """ Create book move transfer to partner location when a book
        is issued """
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        book_obj = self.book_id
        if book_obj.type != 'service':
            price_unit = book_obj.list_price
            template = {
                'display_name': book_obj.name or '',
                'product_id': book_obj.id,
                'product_uom': book_obj.uom_id.id,
                'location_id': dest_loc,
                'location_dest_id': src_loc,
                'picking_id': picking.id,
                'state': 'draft',
                'company_id': self.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': picking.picking_type_id.id,
                'route_ids': 1 and [
                    (6, 0, [x.id for x in
                            self.env['stock.route'].search(
                                [('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
            }
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': int(1),
            })
            template['product_uom_qty'] = int(1)
            done += moves.create(template)
        return done

    @api.model
    def get_books_expires_today(self):
        """return the issued books expires today"""
        query = '''SELECT  br.book_id, pt.name ->> 'en_US' AS book_name, COUNT(*) AS expired_count
            FROM book_register br
            JOIN product_product pp ON br.book_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE br.register_status = 'issued'
            AND br.calc_return_date = CURRENT_DATE
            GROUP BY br.book_id, pt.name ->> 'en_US'
        '''
        self.env.cr.execute(query)
        expire_books = self.env.cr.dictfetchall()
        total_quantity = [record.get('expired_count') for record in
                          expire_books]
        book_name = [record.get('book_name') for record in expire_books]
        book_id = [record.get('book_id') for record in expire_books]
        final = [total_quantity, book_name, book_id]
        return final

    @api.model
    def get_books_expire_tomorrow(self):
        """return the issued books expires tomorrow"""
        query = '''
            SELECT pt.name ->> 'en_US' AS book_name, COUNT(*) AS book_count
            FROM book_register br
            JOIN product_product pp ON br.book_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE br.register_status = 'issued'
              AND br.calc_return_date = CURRENT_DATE + INTERVAL '1 day'
            GROUP BY pt.name ->> 'en_US'
        '''
        self.env.cr.execute(query)
        expire_books_tomorrow = self.env.cr.dictfetchall()
        book_count = [record.get('book_count') for record in
                      expire_books_tomorrow]
        book_name = [record.get('book_name') for record in expire_books_tomorrow]
        final = [book_count, book_name]
        return final

    @api.model
    def get_top_readers(self, limit=5, active_only=False):
        """
        Returns top readers (members who borrowed the most books).
        :param limit: number of top members to return
        :param active_only: if True, only count currently issued books
        """
        where_clause = ""
        if active_only:
            where_clause = "WHERE register_status = 'issued'"

        query = f"""
                SELECT register_member_id, COUNT(id) AS total_borrows
                FROM book_register
                {where_clause}
                GROUP BY register_member_id
                ORDER BY total_borrows DESC
                LIMIT  3
            """

        self.env.cr.execute(query, [limit])
        result = self.env.cr.dictfetchall()
        print(result)

        partners = self.env['res.partner'].browse([r['register_member_id'] for r in result])
        partner_map = {p.id: p for p in partners}

        return [
            {
                "id": r["register_member_id"],
                "name": partner_map[r["register_member_id"]].name,
                "image_1920": partner_map[r["register_member_id"]].image_1920,
                "total_borrows": r["total_borrows"],
            }
            for r in result if r["register_member_id"] in partner_map
        ]
