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
import threading
import base64
from odoo import models, api
from odoo.modules.registry import Registry
import logging

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def generate_in_background(self, report_name, docids, request_id=False,tab_id=False):
        """
            Start PDF generation in a background thread.
            This method creates a new daemon thread that calls
            `_generate_pdf_thread` to render the report PDF
            without blocking the main user request.
         """
        thread = threading.Thread(
            target=self._generate_pdf_thread,
            args=(report_name, docids, None, request_id),
        )
        thread.daemon = True
        thread.start()

    def _generate_pdf_thread(self, report_ref, res_ids, data=None, request_id=False, tab_id=False):
        """
            Generate the PDF in a background thread using a new database cursor,
            create it as an attachment, and send a notification for download.
        """
        db_name = self.env.cr.dbname
        uid = self.env.uid

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

                    else:
                        filename = f"{clean_name}.pdf"

                    attach_in_chatter = env['ir.config_parameter'].sudo().get_param(
                        'custom_report.attach_pdf_in_chatter'
                    )

                    attachment = env['ir.attachment'].create({
                        'name': filename,
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': record._name,
                        'res_id': record.id,
                        'mimetype': 'application/pdf',
                        'is_background_pdf': True,
                    })

                    if attach_in_chatter == 'True':
                        record.message_post(
                            body="PDF generated successfully.",
                            attachment_ids=[attachment.id],
                        )

                    download_url = f"/web/content/{attachment.id}?download=true"

                    env['bus.bus']._sendone(
                        env.user.partner_id,
                        "pdf_download",
                        {
                            "url": download_url,
                            "name": attachment.name,
                            "order_ref": record.name,
                            "request_id": request_id,
                        }
                    )

                new_cr.commit()



            except Exception as e:
                new_cr.rollback()
                error_msg = str(e)
                if hasattr(e, 'name'):
                    error_msg = e.name
                env['bus.bus']._sendone(
                    env.user.partner_id,
                    "pdf_error",
                    {
                        "message": error_msg,
                        "title": "PDF Generation Failed",
                        "tab_id": tab_id,
                    }
                )
