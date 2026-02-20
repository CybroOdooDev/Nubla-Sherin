from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attach_pdf_in_chatter = fields.Boolean(
        string="Attach Background PDF in Chatter",
        config_parameter="custom_report.attach_pdf_in_chatter",
    )