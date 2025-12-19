from odoo import models, api
import qrcode
import base64
from io import BytesIO

class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def generate_receipt_qr_base64(self, text):
        print("hssssssssssssssssssssssssss")
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=2,
        )
        print(qr)
        print("TEXT",text)
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")

        return base64.b64encode(buffer.getvalue()).decode("utf-8")
