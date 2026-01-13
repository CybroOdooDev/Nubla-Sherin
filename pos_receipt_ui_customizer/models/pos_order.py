from odoo import models, fields,api
import uuid


class PosOrder(models.Model):
    _inherit = "pos.order"

    receipt_token = fields.Char(
        string='Receipt Token',
        readonly=True,
        copy=False,
        index=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('receipt_token'):
                vals['receipt_token'] = str(uuid.uuid4())
        return super(PosOrder, self).create(vals_list)

    def get_receipt_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/my/receipt/{self.receipt_token}"

    def get_receipt_qr_code(self):
        """Generate QR code for receipt URL"""
        try:
            import qrcode
            import base64
            from io import BytesIO

            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(self.get_receipt_url())
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_str}"
        except ImportError:
            return False
