from odoo import models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def do_print_picking(self):
        self.ensure_one()

        report = self.env.ref("stock.action_report_delivery")

        self.env["ir.actions.report"].generate_in_background(
            report.report_name,
            [self.id],
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Success",
                "message": "Delivery Slip PDF generation started in background.",
                "type": "success",
                "sticky": False,
            },
        }