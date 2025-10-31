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
from odoo import api, models


class LibraryMemberReport(models.AbstractModel):
    """ Abstract model for generating PDF report value and send to template """
    _name = 'report.library_management_system.member_report'
    _description = "library management Member Report"

    @api.model
    def _get_report_values(self,docids,data=None):
        """ Provide report values to template """
        membership = self.env['membership.type'].sudo().browse(data['form']['membership_id'])
        query = """select * from res_partner where is_a_member=True and 
                created_company_id=%s""" % self.env.user.company_id.id
        if membership:
            query += """ and membership_type_id=%s """ % \
                     data['form']['membership_id']
        if data['form']['is_block_status']:
            query += """ and is_block_status=True """
        self.env.cr.execute(query)
        members = self.env.cr.dictfetchall()
        lst = []
        for memb in members:
            membership = self.env['membership.type'].sudo().browse(memb['membership_type_id'])
            print(membership)
            lst.append({
                'memb_id': memb['member_sequence'] or '',
                'member_name': memb['name'] or '',
                'address': memb['street'] or '',
                'mobile': memb.get('phone', '') or '',
                'email': memb['email'] or '',
                'cur_membership': membership.membership_name or '',
                'exp_date': memb['membership_expiry_date'] or '',
                'book_on_hand': memb['book_count'] or '',
                'due_paid': memb['due_amount_paid'] or ''
            })
        return {
            'values': lst,
            'rep_date': data['form']['date_today'] or False,
            'membership_name': membership.membership_name,
            'is_block_status': data['form']['is_block_status'],
        }
