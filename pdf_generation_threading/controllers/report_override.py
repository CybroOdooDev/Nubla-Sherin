from odoo import http
from odoo.http import request

class BackgroundReportController(http.Controller):

    @http.route('/report/background_generate', type='json', auth='user')
    def background_generate(self, report_name, docids):
        print("hdddddddd")
        request.env['ir.actions.report'].generate_in_background(
            report_name,
            docids,
        )
        return {"status": "started"}
