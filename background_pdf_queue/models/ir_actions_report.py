import base64
import logging

from odoo import models, _

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, docids, data=None):
        print("PDF RENDER INTERCEPTED")

        report = self._get_report_from_name(report_ref)

        print("REAL REPORT:", report)
        print("REAL TYPE:", report.report_type)

        if report.report_type == 'qweb-pdf':
            print("QUEUE JOB HERE")

            report.with_delay()._generate_pdf_job(docids, data)

            # Return empty response so browser doesn't crash
            return b"", 'pdf'

        return super()._render_qweb_pdf(report_ref, docids, data=data)

    def _queue_pdf_job(self, docids, data=None):
        self.ensure_one()
        print("QUEUE JOB")

        if hasattr(docids, 'ids'):
            doc_ids = docids.ids
        elif isinstance(docids, int):
            doc_ids = [docids]
        else:
            doc_ids = list(docids)

        # enqueue background job
        self.with_delay(
            channel='root.pdf_reports',
            priority=10,
            max_retries=3,
        )._generate_pdf_job(doc_ids, data)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('PDF Started'),
                'message': _('PDF is generating in background.'),
                'type': 'info',
            },
        }

    # NO decorator here
    def _generate_pdf_job(self, doc_ids, data=None):
        self.ensure_one()

        _logger.info("Generating PDF in background for %s", doc_ids)

        pdf_content, _ = self._render_qweb_pdf(
            self.report_name,
            doc_ids,
            data=data,
        )

        records = self.env[self.model].browse(doc_ids)

        for record in records:
            attachment = self.env['ir.attachment'].create({
                'name': f'{record.display_name}.pdf',
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': self.model,
                'res_id': record.id,
                'mimetype': 'application/pdf',
            })

            record.message_post(
                body=_(" PDF generated in background."),
                attachment_ids=[attachment.id],
            )

        _logger.info("PDF generation completed.")