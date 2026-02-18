import threading
import base64
from odoo import models, api, registry, SUPERUSER_ID

class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def generate_in_background(self, report_name, docids):
        thread = threading.Thread(
            target=self._generate_pdf_thread,
            args=(report_name, docids)
        )
        thread.daemon = True
        thread.start()

    def _generate_pdf_thread(self, report_name, docids):
        db_name = self.env.cr.dbname

        with registry(db_name).cursor() as new_cr:
            env = api.Environment(new_cr, SUPERUSER_ID, {})

            report = env["ir.actions.report"]._get_report_from_name(report_name)

            pdf_content, _ = report._render_qweb_pdf(
                report_name,
                res_ids=docids,
                data=None,
            )

            records = env[report.model].browse(docids)

            for record in records:
                attachment = env["ir.attachment"].create({
                    "name": f"{report.name}_{record.id}.pdf",
                    "type": "binary",
                    "datas": base64.b64encode(pdf_content),
                    "res_model": record._name,
                    "res_id": record.id,
                    "mimetype": "application/pdf",
                })

                record.message_post(
                    body="✅ PDF generated successfully.",
                    attachment_ids=[attachment.id],
                )

            new_cr.commit()
