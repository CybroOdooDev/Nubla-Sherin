# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Gayathri V (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0(OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################
import json
from odoo import http
from odoo.http import content_disposition, request
from odoo.http import serialize_exception as _serialize_exception
from odoo.tools import html_escape


class XLSXReportController(http.Controller):
    """Controller for handling XLSX reports in the library management
    system."""
    @http.route('/library_xlsx_reports', type='http', auth='user',
                methods=['POST'], csrf=False)
    def get_report_xlsx(self, model, name, **kw):
        """ Generate and deliver XLSX reports based on the specified model
        and options.
        params:
         model: The type of report model.
         name: The name of the report.
         kw: Additional keyword arguments, including 'output_format'.
        :return: Response with the generated XLSX report."""
        token = 'dummy-because-api-expects-one'
        domain = [('create_uid', '=', request.session.uid)]
        if model == 'issued.book.report':
            report_obj = request.env['issued.book.report'].with_user(
                request.session.uid).search(domain, limit=1)
            options = name
        else:
            report_obj = (request.env['member.report']
                          .with_user(request.session.uid).
                          search(domain, limit=1))
            options = name
        try:
            if model == 'issued.book.report':
                if kw['output_format'] == 'xlsx':
                    response = request.make_response(
                        None,
                        headers=[
                            ('Content-Type', 'application/vnd.ms-excel'),
                            ('Content-Disposition', content_disposition(
                                'Issued Book Report' + '.xlsx'))
                        ]
                    )
                    report_obj.generate_xlsx_report(options, response)
                response.set_cookie('fileToken', token)
                return response
            else:
                if kw['output_format'] == 'xlsx':
                    response = request.make_response(
                        None,
                        headers=[
                            ('Content-Type', 'application/vnd.ms-excel'),
                            ('Content-Disposition',
                             content_disposition('Member Report' + '.xlsx'))
                        ]
                    )
                    report_obj.generate_xlsx_report(options, response)
                response.set_cookie('fileToken', token)
                return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
