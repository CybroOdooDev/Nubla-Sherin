# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Nublasherin k (odoo@cybrosys.com)
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
from datetime import datetime
import io
import json
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.json import json_default

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class IssuedBookReport(models.TransientModel):
    """ Model for issued book report """
    _name = 'issued.book.report'
    _description = "Issued Book Report"

    date_start = fields.Date(string="Start Date", help='Select start date of '
                                                       'report')
    date_end = fields.Date(string="End Date", default=fields.Date.today,
                           required=True, help='Select end date of report')
    book_name_id = fields.Many2one("product.template",
                                   string="Book name",
                                   help="Name of the book",
                                   domain=[('is_a_book', '=', True)])
    status = fields.Selection([('draft', 'Draft'),
                               ('issued', 'Issued'),
                               ('expired', 'Expired'),
                               ('returned', 'Returned')],
                              string="Register status",
                              help='Select status of report.')
    member_id = fields.Many2one("res.partner",
                                string="Book holder", help='Select Member')
    user_id = fields.Many2one('res.users', 'Responsible', help='Select user')

    def get_report(self):
        """ Function to print pdf report """
        if self.date_start:
            date_start = datetime.strftime(self.date_start, "%Y-%m-%d")
        else:
            date_start = False
        date_end = datetime.strftime(self.date_end, "%Y-%m-%d")
        if date_start:
            if date_start > date_end:
                raise UserError("Start date should be less than end date")
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': date_start,
                'date_end': date_end,
                'book_name_id': self.book_name_id.id,
                'status': self.status,
                'member_id': self.member_id.id,
                'user_id': self.user_id.id,
            },
        }
        return self.env.ref(
            'library_management_system.book_issue_report').report_action(
            self, data=data)

    def get_xlsx_report(self):
        """ Print xlsx report """
        if self.date_start:
            date_start = datetime.strftime(self.date_start, "%Y-%m-%d")
        else:
            date_start = False
        date_end = datetime.strftime(self.date_end, "%Y-%m-%d")
        if date_start:
            if date_start > date_end:
                raise UserError("Start date should be less than end date")
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': date_start,
                'date_end': date_end,
                'book_name_id': self.book_name_id.id,
                'status': self.status,
                'member_id': self.member_id.id,
                'user_id': self.user_id.id,
            },
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'library_xlsx',
            'data': {'model': 'issued.book.report',
                     'name': json.dumps(data, default=json_default),
                     'output_format': 'xlsx', },
        }

    def generate_xlsx_report(self, data, response):
        """ Function generate report and write to excel sheet """
        output = io.BytesIO()
        data = json.loads(data)
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        member_obj = self.env['res.partner'].sudo()
        responsive_obj = self.env['res.users'].sudo()
        book_obj = self.env['product.product'].sudo()
        member = member_obj.browse(data['form']['member_id'])
        responsive = responsive_obj.browse(data['form']['user_id'])
        book_name_id = book_obj.search(
            [('product_tmpl_id', '=', data['form']['book_name_id'])])
        query = """select * from book_register where issued_date<='%s' """ \
                % (data['form']['date_end'],)
        if data['form']['date_start']:
            query += """ and issued_date>='%s' """ % data['form']['date_start']
        if book_name_id:
            query += """ and book_id=%s """ % book_name_id.id
        if member:
            query += """ and register_member_id=%s """ % member.id
        if responsive:
            query += """ and responsive_person_id=%s """ % responsive.id
        if data['form']['status']:
            query += """ and register_status='%s' """ % data['form']['status']
        self.env.cr.execute(query)
        book_reg = self.env.cr.dictfetchall()
        sheet = workbook.add_worksheet('Report')
        bold = workbook.add_format(
            {'bold': True, 'font_size': '10px', 'border': 1})
        date = workbook.add_format({'bold': True, 'font_size': '10px'})
        date_to = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '20px',
             'border': 1})
        txt = workbook.add_format({'font_size': '10px', 'border': 1})
        sheet.merge_range('C2:K3', 'ISSUED BOOK REPORT', head)
        sheet.write('C5', "FROM", date)
        sheet.write('C6', data['form']['date_start'], date)
        sheet.write('D5', "TO", date_to)
        sheet.write('D6', data['form']['date_end'], date)
        sheet.write('E5', "BOOK", date_to)
        sheet.write('E6', book_name_id.name, date)
        sheet.write('F5', "STATUS", date_to)
        sheet.write('F6', data['form']['status'], date)
        sheet.write('G5', "MEMBER", date_to)
        sheet.write('G6', member.name, date)
        sheet.write('H5', "RESPONSIBLE", date_to)
        sheet.write('H6', responsive.name, date)
        sheet.write('C8', 'REG NO.', bold)
        sheet.write('D8', 'BOOK', bold)
        sheet.write('E8', 'ISBN 10', bold)
        sheet.write('F8', 'ISBN 13', bold)
        sheet.write('G8', 'MEMBER', bold)
        sheet.write('H8', 'ISSUED DATE', bold)
        sheet.write('I8', 'EXP RET DATE', bold)
        sheet.write('J8', 'STATUS', bold)
        sheet.write('K8', 'RESPONSIBLE', bold)
        sheet.set_column(2, 7, 15)
        sheet.set_column(3, 7, 15)
        sheet.set_column(4, 7, 15)
        sheet.set_column(5, 7, 15)
        sheet.set_column(6, 7, 15)
        sheet.set_column(7, 7, 15)
        sheet.set_column(8, 7, 15)
        sheet.set_column(9, 7, 15)
        sheet.set_column(10, 7, 15)
        row_num = 7
        col_num = 2
        for reg in book_reg:
            member_name = member_obj.browse(reg['register_member_id'])
            responsive_name = responsive_obj.browse(
                reg['responsive_person_id'])
            book = book_obj.browse(reg['book_id'])
            sheet.write(row_num + 1, col_num, reg['register_sequence'], txt)
            sheet.write(row_num + 1, col_num + 1, book.name, txt)
            sheet.write(row_num + 1, col_num + 2, reg['register_isbn_number'],
                        txt)
            sheet.write(row_num + 1, col_num + 3,
                        reg['register_isbn_13_number'], txt)
            sheet.write(row_num + 1, col_num + 4, member_name.name, txt)
            sheet.write(row_num + 1, col_num + 5, str(reg['issued_date']), txt)
            sheet.write(row_num + 1, col_num + 6, str(reg['calc_return_date']),
                        txt)
            sheet.write(row_num + 1, col_num + 7, reg['register_status'], txt)
            sheet.write(row_num + 1, col_num + 8, responsive_name.name, txt)
            row_num = row_num + 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


class LibraryIssuedReportPdf(models.AbstractModel):
    """ Abstract model for generating PDF report value and send to template """

    _name = 'report.library_management_system.issued_book_report'
    _description = "Issued book report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """ Provide report values to template """
        member_obj = self.env['res.partner'].sudo()
        responsive_obj = self.env['res.users'].sudo()
        book_obj = self.env['product.product'].sudo()
        member = member_obj.browse(data['form']['member_id'])
        responsive = responsive_obj.browse(data['form']['user_id'])
        book_name = book_obj.search(
            [('product_tmpl_id', '=', data['form']['book_name_id'])])
        company_id = self.env.user.company_id.id

        query = """select * from book_register where issued_date<='%s' 
                and company_id = %s""" % (
            data['form']['date_end'], company_id)

        if data['form']['date_start']:
            query += """ and issued_date>='%s' """ % data['form'][
                'date_start']
        if book_name:
            query += """ and book_id=%s """ % book_name.id
        if member:
            query += """ and register_member_id=%s """ % member.id
        if responsive:
            query += """ and responsive_person_id=%s """ % responsive.id
        if data['form']['status']:
            query += """ and register_status='%s' """ % data['form'][
                'status']
        self.env.cr.execute(query)
        book_reg = self.env.cr.dictfetchall()
        lst = []
        for reg in book_reg:
            member_name = member_obj.browse(reg['register_member_id'])
            responsive_name = responsive_obj.browse(
                reg['responsive_person_id'])
            book = book_obj.browse(reg['book_id'])
            lst.append({
                'reg_seq': reg['register_sequence'] or '',
                'book_name': book.name or '',
                'isbn_10': reg['register_isbn_number'] or '',
                'isbn_13': reg['register_isbn_13_number'] or '',
                'member_name': member_name.name or '',
                'issue_date': reg['issued_date'] or '',
                'exp_ret': reg['calc_return_date'] or '',
                'status': reg['register_status'] or '',
                'responsible': responsive_name.name or '',

            })
        return {
            'values': lst,
            'start_date': data['form']['date_start'] or False,
            'date_end': data['form']['date_end'] or False,
            'book_name': book_name.name or False,
            'status': data['form']['status'] or False,
            'member_id': member.name or False,
            'responsive': responsive.name or False,
        }
