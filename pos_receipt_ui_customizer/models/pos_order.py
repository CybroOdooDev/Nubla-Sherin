import qrcode
import base64
from io import BytesIO
import uuid
from odoo import models, fields
import io


class PosOrder(models.Model):
    _inherit = 'pos.order'

    custom_qr_image = fields.Binary("Custom Receipt QR")
    custom_receipt_token = fields.Char("Receipt Token")

    def generate_custom_qr(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        for order in self:
            token = str(uuid.uuid4())
            qr_data = f"{base_url}/my/receipt/{order.id}?t={token}"
            print("qr_data", qr_data)

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=3,
            )
            print("qr",qr)
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            print("order", order)
            print("order", order.name)
            buf = io.BytesIO()
            img.save(buf, format="PNG")

            order.custom_receipt_token = token
            print("order.custom_receipt_token", order.custom_receipt_token)
            order.custom_qr_image = base64.b64encode(buf.getvalue()).decode()
            print("order.custom_qr_image", order.custom_qr_image)

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        print("res", res)
        print("ssssssssssss")
        self.generate_custom_qr()
        return res
