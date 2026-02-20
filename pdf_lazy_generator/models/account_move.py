from odoo import models

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_print_pdf(self):
        self.ensure_one()

        invoice_template = self.env['account.move.send']._get_default_pdf_report_id(self)
        print("ACCOUNT MOVEEEEEEE PDF GENERATING")

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
