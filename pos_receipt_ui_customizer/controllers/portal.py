from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError


class POSReceiptPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'receipt_count' in counters:
            partner = request.env.user.partner_id
            receipt_count = request.env['pos.order'].search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['paid', 'done', 'invoiced'])
            ])
            values['receipt_count'] = receipt_count
        return values

    @http.route(['/my/receipts', '/my/receipts/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_receipts(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):

        print("11111111111111111")
        """Display all customer receipts"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id.commercial_partner_id
        PosOrder = request.env['pos.order']

        domain = [
            ('partner_id.commercial_partner_id', '=', partner.id),
            ('session_id', '!=', False),  # ensures POS orders only
            ('state', 'in', ['paid', 'done', 'invoiced'])
        ]

        # Search and sort options
        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'amount': {'label': _('Amount'), 'order': 'amount_total desc'},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Date filter
        if date_begin and date_end:
            domain += [('date_order', '>=', date_begin), ('date_order', '<=', date_end)]

        # Count for pager
        receipt_count = PosOrder.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/receipts",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=receipt_count,
            page=page,
            step=self._items_per_page
        )

        # Get receipts
        receipts = PosOrder.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'receipts': receipts,
            'page_name': 'receipt',
            'pager': pager,
            'default_url': '/my/receipts',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return request.render("pos_receipt_ui_customizer.portal_my_receipts", values)

    @http.route(['/my/receipt/<string:token>'], type='http', auth='user', website=True)
    def portal_receipt_detail(self, token, **kw):
        """Display single receipt detail"""
        try:

            order = request.env['pos.order'].search([
                ('receipt_token', '=', token)
            ], limit=1)
            print("222222222", order)

            if not order:
                return request.redirect('/my/receipts?error=notfound')

            # Check access rights
            partner = request.env.user.partner_id
            print("USER",partner)
            if order.partner_id != partner:
                raise AccessError(_("You don't have access to this receipt"))

            values = {
                'order': order,
                'company': order.company_id,
                'page_name': 'receipt',
            }
            print("VALUE",values)

            return request.render("pos_receipt_ui_customizer.portal_receipt_detail", values)

        except (AccessError, MissingError):
            return request.redirect('/my/receipts?error=access')

    @http.route(['/my/receipt/<string:token>/pdf'], type='http', auth='user')
    def portal_receipt_pdf(self, token, **kw):
        """Download receipt as PDF"""
        try:
            order = request.env['pos.order'].search([
                ('receipt_token', '=', token)
            ], limit=1)

            if not order:
                return request.not_found()

            # Check access rights
            partner = request.env.user.partner_id
            if order.partner_id != partner:
                raise AccessError(_("You don't have access to this receipt"))

            # Generate PDF (you can create custom PDF report)
            pdf_content = request.env.ref('point_of_sale.pos_invoice_report').sudo()._render_qweb_pdf(order.ids)[0]

            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', f'attachment; filename="Receipt-{order.name}.pdf"')
            ]

            return request.make_response(pdf_content, headers=pdfhttpheaders)

        except (AccessError, MissingError):
            return request.redirect('/my/receipts?error=access')

    # Public receipt access (for QR code scans)
    @http.route('/receipt/<string:token>', type='http', auth='public', website=True)
    def public_receipt_view(self, token, **kwargs):
        """Public access to receipt via QR code"""
        order = request.env['pos.order'].sudo().search([
            ('receipt_token', '=', token)
        ], limit=1)

        if not order:
            return request.render('pos_receipt_ui_customizer.receipt_not_found')

        values = {
            'order': order,
            'company': order.company_id,
        }

        return request.render('pos_receipt_ui_customizer.public_receipt_template', values)