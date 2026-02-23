#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def print_quotation(self):
        """
             Triggered when the Print RFQ/Quotation button is clicked.
             This method updates the purchase order state to 'sent'
             and starts the quotation PDF generation in the background
             using a threaded process. A success notification is shown
             immediately while the PDF is generated.
        """
        self.ensure_one()

        self.write({'state': "sent"})

        report = self.env.ref('purchase.report_purchase_quotation')

        self.env['ir.actions.report'].generate_in_background(
            report.report_name,
            [self.id],
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Success",
                "message": "Purchase Quotation PDF generation started in background.",
                "type": "success",
                "sticky": False,
            },
        }