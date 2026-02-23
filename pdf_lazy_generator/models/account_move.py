# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
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

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_print_pdf(self):
        """
             Triggered when the Print button is clicked.
             This method starts invoice PDF generation in the background
             using a threaded process to avoid blocking the user interface.
             A success notification is shown immediately while the PDF
             is generated in the background.
        """
        self.ensure_one()

        invoice_template = self.env['account.move.send']._get_default_pdf_report_id(self)

        self.env['ir.actions.report'].generate_in_background(
            invoice_template.report_name,
            [self.id],
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Success",
                "message": "Invoice PDF generation started in background.",
                "type": "success",
                "sticky": False,
            },
        }