# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import base64
from odoo import api, fields, models


class NHSContractorVisitCompleteWizardLine(models.TransientModel):
    """Line item for completing a compliance item test from a contractor visit."""
    _name = 'nhs.contractor.visit.complete.wizard.line'
    _description = 'Contractor Visit Item Completion Line'

    wizard_id = fields.Many2one('nhs.contractor.visit.complete.wizard', string='Wizard', ondelete='cascade',
                                help='Wizard to record compliance test outcomes.')
    selected = fields.Boolean(string='Complete', default=True, help='Select to record completion for this item.')
    item_id = fields.Many2one('nhs.compliance.item', string='Compliance Item', required=True,
                              help="The compliance item to record compliance test outcomes.")
    discipline_id = fields.Many2one('nhs.compliance.discipline', related='item_id.discipline_id',
                                    help="The discipline of the compliance item", readonly=True)
    outcome = fields.Selection([
        ('pass', 'Pass'),
        ('pass_with_observations', 'Pass with Observations'),
        ('fail', 'Fail'),
        ('remedial_required', 'Remedial Action Required')
    ], string='Outcome', default='pass', required=True, help="Set a default outcome to apply to test.")
    certificate_ref = fields.Char(string='Certificate Reference', help='Certificate reference for  test.')
    certificate_date = fields.Date(string='Certificate Date', default=fields.Date.today,
                                   help='Certificate date for all selected items.')
    certificate_expiry = fields.Date(string='Certificate Expiry', help='Certificate expiry date for  test.')
    issuing_body = fields.Char(string='Issuing Body', help='Body or organisation issuing the certificate.')
    certificate_file = fields.Binary(string='Certificate Attachment', help='Certificate attachment to tests.')
    certificate_filename = fields.Char(string='Certificate Filename', help="Certificate attachment file name.")
    notes = fields.Text(string='Test Notes / Findings', help="Notes about the visits and tests.")


class NHSContractorVisitCompleteWizard(models.TransientModel):
    """Wizard to record compliance test outcomes for multiple covered items during a contractor visit."""
    _name = 'nhs.contractor.visit.complete.wizard'
    _description = 'Complete Multiple Compliance Items from Visit'

    visit_id = fields.Many2one('nhs.contractor.visit', string='Contractor Visit', required=True,
                               help="The contractor visit record", readonly=True)
    contractor_id = fields.Many2one('nhs.compliance.contractor', related='visit_id.contractor_id',
                                    help="The contractor visiting", readonly=True)
    visit_date = fields.Date(string='Visit Date', related='visit_id.visit_date', readonly=True,
                             help="Date of the visit ")
    common_outcome = fields.Selection([
        ('pass', 'Pass'),
        ('pass_with_observations', 'Pass with Observations'),
        ('fail', 'Fail'),
        ('remedial_required', 'Remedial Action Required')
    ], string='Common Outcome', default='pass', help='Set a default outcome to apply to all selected items.')
    common_certificate_ref = fields.Char(string='Common Certificate Ref',
                                         help='Common certificate reference for all selected items.')
    common_certificate_date = fields.Date(string='Common Certificate Date', default=fields.Date.today,
                                          help='Date of certificate issue.')
    common_certificate_expiry = fields.Date(string='Common Expiry Date', help='Expiry date for the certificate.')
    common_issuing_body = fields.Char(string='Common Issuing Body',
                                      help='Body or organisation issuing the certificate.')
    common_certificate_file = fields.Binary(string='Common Certificate File', help='Common certificate attachment '
                                                                                   'to apply to all tests.')
    common_certificate_filename = fields.Char(string='Common Certificate Filename')
    line_ids = fields.One2many('nhs.contractor.visit.complete.wizard.line', 'wizard_id',
                               help="The items covered during this visit",
                               string='Compliance Items Covered')

    @api.onchange('common_outcome', 'common_certificate_ref', 'common_certificate_file',
                  'common_certificate_filename', 'common_certificate_date',
                  'common_certificate_expiry', 'common_issuing_body')
    def _onchange_common_fields(self):
        """Propagate common field values to all wizard item lines upon change."""
        for line in self.line_ids:
            if self.common_outcome:
                line.outcome = self.common_outcome
            if self.common_certificate_ref:
                line.certificate_ref = self.common_certificate_ref
            if self.common_certificate_file:
                line.certificate_file = self.common_certificate_file
                line.certificate_filename = self.common_certificate_filename
            if self.common_certificate_date:
                line.certificate_date = self.common_certificate_date
            if self.common_certificate_expiry:
                line.certificate_expiry = self.common_certificate_expiry
            if self.common_issuing_body:
                line.issuing_body = self.common_issuing_body

    def action_complete_items(self):
        """Process test completion for all selected compliance items and roll schedules forward."""
        self.ensure_one()
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Items Selected',
                    'message': 'Please select at least one compliance item to complete.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        for line in selected_lines:
            cert_ref = line.certificate_ref or self.common_certificate_ref or False
            cert_file = line.certificate_file or self.common_certificate_file
            if cert_ref and not cert_file:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Validation Error',
                        'message': f'Please attach the certificate document when providing a certificate reference.',
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        created_tests = self.env['nhs.compliance.test']
        default_issuing_body = self.common_issuing_body or (self.visit_id.contractor_id.name
                                                            if self.visit_id.contractor_id else False)
        test_vals_list = []
        for line in selected_lines:
            cert_ref = line.certificate_ref or self.common_certificate_ref or False
            cert_date = (line.certificate_date or self.common_certificate_date or
                         self.visit_id.visit_date or fields.Date.today()) if cert_ref else False
            cert_expiry = line.certificate_expiry or self.common_certificate_expiry or False if cert_ref else False
            issuing_body = line.issuing_body or default_issuing_body if cert_ref else False
            test_vals_list.append({
                'item_id': line.item_id.id,
                'visit_id': self.visit_id.id,
                'test_date': self.visit_id.visit_date or fields.Date.today(),
                'outcome': line.outcome or self.common_outcome or 'pass',
                'certificate_ref': False,  # Set to False initially to avoid constraint
                'certificate_date': cert_date,
                'certificate_expiry': cert_expiry,
                'issuing_body': issuing_body,
                'notes': line.notes or self.visit_id.notes or False,
                'active': True,
            })
        tests = self.env['nhs.compliance.test'].create(test_vals_list)
        for idx, (line, test) in enumerate(zip(selected_lines, tests)):
            cert_ref = line.certificate_ref or self.common_certificate_ref or False
            if cert_ref:
                cert_file = line.certificate_file or self.common_certificate_file
                cert_filename = (line.certificate_filename or self.common_certificate_filename or
                                 f"Certificate_{cert_ref}.pdf")
                cert_date = (line.certificate_date or self.common_certificate_date or
                             self.visit_id.visit_date or fields.Date.today())
                cert_expiry = line.certificate_expiry or self.common_certificate_expiry or False
                issuing_body = line.issuing_body or default_issuing_body
                attachment = self.env['ir.attachment'].create({
                    'name': cert_filename,
                    'datas': cert_file,
                    'res_model': 'nhs.compliance.test',
                    'res_id': test.id,
                    'type': 'binary',
                })
                update_vals = {
                    'certificate_ref': cert_ref,
                    'certificate_date': cert_date,
                    'certificate_expiry': cert_expiry,
                    'issuing_body': issuing_body,
                    'attachment_ids': [(4, attachment.id)],
                }
                test.write(update_vals)
            line.item_id._compute_last_completed_date()
            line.item_id._compute_next_due()
            line.item_id._compute_status()
            created_tests |= test
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Compliance Items Completed',
                'message': f"Successfully recorded tests and updated {len(created_tests)} compliance item(s).",
                'type': 'success',
                'sticky': False,
            }
        }
