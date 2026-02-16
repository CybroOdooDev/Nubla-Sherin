from odoo import models
import base64


class Report(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)

        if not res_ids:
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        # Only cache single record (safe approach)
        if len(res_ids) == 1:
            attachment_name = f"{report.report_name}_{res_ids[0]}.pdf"

            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', report.model),
                ('res_id', '=', res_ids[0]),
                ('name', '=', attachment_name)
            ], limit=1)

            if attachment:
                return base64.b64decode(attachment.datas), 'pdf'

            # Generate PDF
            pdf_content, content_type = super()._render_qweb_pdf(
                report_ref, res_ids=res_ids, data=data
            )

            # Store attachment
            self.env['ir.attachment'].create({
                'name': attachment_name,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': report.model,
                'res_id': res_ids[0],
                'mimetype': 'application/pdf',
            })

            return pdf_content, content_type

        # For multiple records → fallback normal behavior
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)