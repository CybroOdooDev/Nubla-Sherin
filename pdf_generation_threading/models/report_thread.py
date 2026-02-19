import threading
import base64
from odoo import models, api
from odoo.modules.registry import Registry


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def generate_in_background(self, report_name, docids):
        thread = threading.Thread(
            target=self._generate_pdf_thread,
            args=(report_name, docids),
        )
        thread.daemon = True
        thread.start()

    def _generate_pdf_thread(self, report_ref, res_ids, data=None):
        db_name = self.env.cr.dbname
        uid = self.env.uid

        print("THREAD STARTED")
        print("RES IDS:", res_ids)

        with Registry(db_name).cursor() as new_cr:
            env = api.Environment(new_cr, uid, {})

            try:
                report = env['ir.actions.report']._get_report_from_name(report_ref)

                pdf_content, _ = report._render_qweb_pdf(
                    report_ref,
                    res_ids=res_ids,
                    data=data,
                )

                records = env[report.model].browse(res_ids)

                for record in records:
                    record_name = record.name

                    if not record_name or record_name == "/":
                        record_name = "Draft"

                    clean_name = record_name.replace("/", "_")

                    if record._name == "sale.order":
                        filename = f"Order - {clean_name}.pdf"

                    elif record._name == "account.move":
                        filename = f"{clean_name}.pdf"

                    elif record._name == "stock.picking":
                        filename = f"Picking - {clean_name}.pdf"

                    else:
                        filename = f"{clean_name}.pdf"

                    attachment = env['ir.attachment'].create({
                        'name': filename,
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': record._name,
                        'res_id': record.id,
                        'mimetype': 'application/pdf',
                    })

                    record.message_post(
                        body="PDF generated successfully.",
                        attachment_ids=[attachment.id],
                    )

                    download_url = f"/web/content/{attachment.id}?download=true"
                    print("DOWNLOAD URL", download_url)

                    env['bus.bus']._sendone(
                        env.user.partner_id,
                        "pdf_download",
                        {
                            "url": download_url,
                            "name": attachment.name,
                            "order_ref": record.name,
                        }
                    )

                new_cr.commit()
                print("PDF ATTACHED AND BUS NOTIFICATION SENT")

            except Exception as e:
                new_cr.rollback()
                print("THREAD ERROR:", e)