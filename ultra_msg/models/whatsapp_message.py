import requests
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class WhatsAppMessage(models.TransientModel):
    _name = 'whatsapp.message'
    _description = 'WhatsApp Message Sender'

    mobile_number = fields.Char(string="Mobile Number", required=True, help="Include country code, e.g. 919876543210")
    message = fields.Text(string="Message", required=True)

    def action_send_message(self):
        """Send WhatsApp message via UltraMsg with hardcoded credentials"""
        print("hello")
        instance_id = "instance115242"
        token = "hu3vsgarne3u341i"

        for wizard in self:
            url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
            payload = {
                "token": token,
                "to": wizard.mobile_number,
                "body": wizard.message,
            }
            print(wizard.message)

            try:
                response = requests.post(url, data=payload, timeout=10)
                if response.status_code == 200:
                    _logger.info("WhatsApp message sent to %s", wizard.mobile_number)
                else:
                    _logger.error("Failed to send WhatsApp message: %s", response.text)
            except Exception as e:
                _logger.exception("Error sending WhatsApp message: %s", e)

        return {'type': 'ir.actions.act_window_close'}
