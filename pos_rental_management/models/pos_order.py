from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = "pos.order"

    is_rented = fields.Boolean(
        string="Rented",
        compute="_compute_is_rented",
        store=True
    )

    is_partial_payment = fields.Boolean(
        string="Is Partial Payment",
    )
    state = fields.Selection(
        selection_add=[('partial', 'Partially Paid')],
        ondelete={'partial': 'set default'}
    )
    due_amount = fields.Float(string="Amount Due",
                              compute='_compute_due_amount',
                              store=True,
                              help="The amount remaining to be paid for this"
                                   "POS order.")

    @api.depends('amount_total', 'amount_paid', 'account_move')
    def _compute_due_amount(self):
        """
        Compute the due amount for the POS order.

        If an invoice is linked to the POS order, take the paid amount from the
        invoice instead of the POS payment records.
        """
        for order in self:
            paid_amount = order.amount_paid
            invoice = order.account_move
            if invoice:
                invoice_paid = invoice.amount_total - invoice.amount_residual
                paid_amount = invoice_paid
                order.amount_paid = invoice_paid
            order.due_amount = order.amount_total - paid_amount

    def _order_fields(self, ui_order):
        """
        Prepare dictionary for create method

        This method prepares a dictionary of order fields for creating a POS order based
        on the data from the user interface (UI) order.
        """
        result = super()._order_fields(ui_order)
        result['is_partial_payment'] = ui_order.get('is_partial_payment')
        return result

    def action_pos_order_paid(self):
        """
        Mark the POS order as paid. This method marks the POS order as
        paid and ensures that it is fully paid based on the partial
        payment.
        """
        self.ensure_one()
        # TODO: add support for mix of cash and non-cash payments when both cash_rounding and only_round_cash_method are True
        if not self.config_id.cash_rounding \
                or self.config_id.only_round_cash_method \
                and not any(
            p.payment_method_id.is_cash_count for p in self.payment_ids):
            total = self.amount_total
        else:
            total = float_round(self.amount_total,
                                precision_rounding=self.config_id.rounding_method.rounding,
                                rounding_method=self.config_id.rounding_method.rounding_method)
        isPaid = float_is_zero(total - self.amount_paid,
                               precision_rounding=self.currency_id.rounding)

        if not isPaid:
            pos_config = self.env['pos.config'].search([])
            for shop in pos_config:
                if shop.partial_payment:
                    isPaid = True
        if not isPaid and not self.config_id.cash_rounding:
            raise UserError(_("Order %s is not fully paid.", self.name))
        elif not isPaid and self.config_id.cash_rounding:
            currency = self.currency_id
            if self.config_id.rounding_method.rounding_method == "HALF-UP":
                maxDiff = currency.round(
                    self.config_id.rounding_method.rounding / 2)
            else:
                maxDiff = currency.round(
                    self.config_id.rounding_method.rounding)

            diff = currency.round(self.amount_total - self.amount_paid)
            if not abs(diff) <= maxDiff:
                raise UserError(_("Order %s is not fully paid.", self.name))
        self.write({'state': 'paid'})
        return True

    @api.model
    def search_partial_order_ids(self, config_id, domain, limit, offset):

        default_domain = [
            ('config_id', '=', config_id),
            ('is_partial_payment', '=', True),
            ('state', 'not in', ['draft', 'cancel']),
        ]

        real_domain = AND([domain, default_domain])

        orders = self.search(real_domain, limit=limit, offset=offset, order='date_order DESC')
        totalCount = self.search_count(real_domain)

        return {
            'orders': [[order.id, order.write_date.isoformat()] for order in orders],
            'totalCount': totalCount
        }

    @api.depends('lines.product_id')
    def _compute_is_rented(self):
        for order in self:
            order.is_rented = any(line.product_id.is_rental for line in order.lines)



class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    is_rented = fields.Boolean(string="Is Rented", default=False)

    rental_tenure_id = fields.Many2one(
        'rental.product.tenure',
        string="Rental Tenure"
    )

    rental_tenure_name = fields.Char(
        compute='_compute_rental_tenure_name',
        store=True
    )

    is_partial_payment = fields.Boolean('Partial Payment')
    partial_invoice_id = fields.Many2one('account.move', 'Partial Invoice')
    remaining_amount = fields.Float('Remaining Amount', compute='_compute_remaining')

    def _compute_remaining(self):
        for order in self:
            order.remaining_amount = order.amount_total - order.amount_paid

    @api.depends('rental_tenure_id.name')
    def _compute_rental_tenure_name(self):
        for line in self:
            line.rental_tenure_name = (
                line.rental_tenure_id.name if line.rental_tenure_id else ""
            )
