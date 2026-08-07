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
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import NhsComplaintCommon


@tagged('post_install', '-at_install')
class TestResponseWizard(NhsComplaintCommon):
    """nhs.complaint.response.wizard — draft, sign-off and send."""

    def _ready_complaint(self):
        """Create a formal complaint already acknowledged and under investigation, ready for a response."""
        complaint = self._new_complaint()
        complaint.action_acknowledge()
        complaint.action_start_investigation()
        return complaint

    def test_blank_response_rejected(self):
        """An empty HTML body (e.g. <p><br></p>) is treated as blank and rejected."""
        complaint = self._ready_complaint()
        wizard = self.env['nhs.complaint.response.wizard'].create({
            'complaint_id': complaint.id,
            'response_text': '<p><br></p>',
        })
        with self.assertRaises(UserError):
            wizard.action_save_draft()

    def test_save_draft(self):
        """Saving a draft stores the text and moves the complaint to response_draft."""
        complaint = self._ready_complaint()
        wizard = self.env['nhs.complaint.response.wizard'].create({
            'complaint_id': complaint.id,
            'response_text': '<p>Considered response.</p>',
        })
        wizard.action_save_draft()
        self.assertEqual(complaint.state, 'response_draft')
        self.assertIn('Considered response', complaint.response_text)

    def test_submit_for_signoff_without_signing(self):
        """Without sign_off_now the complaint lands in awaiting_signoff."""
        complaint = self._ready_complaint()
        wizard = self.env['nhs.complaint.response.wizard'].create({
            'complaint_id': complaint.id,
            'response_text': '<p>Response body.</p>',
            'sign_off_now': False,
        })
        wizard.action_submit_for_signoff()
        self.assertEqual(complaint.state, 'awaiting_signoff')

    def test_sign_off_and_send_immediately(self):
        """A quality lead can draft, sign off and send in a single wizard step."""
        complaint = self._ready_complaint()
        # self.env.user (admin) is a member of the Quality Lead group.
        self.assertTrue(self.env.user.has_group(
            'odoo_nhs_complaints.group_nhs_complaint_quality_lead'))
        wizard = self.env['nhs.complaint.response.wizard'].create({
            'complaint_id': complaint.id,
            'response_text': '<p>Final response body.</p>',
            'sign_off_now': True,
            'send_immediately': True,
            'response_method': 'email',
        })
        wizard.action_submit_for_signoff()
        self.assertEqual(complaint.state, 'response_sent')
        self.assertTrue(complaint.signed_off_by_id)
        self.assertEqual(complaint.response_method, 'email')


@tagged('post_install', '-at_install')
class TestLinkIncidentWizard(NhsComplaintCommon):
    """nhs.complaint.link.incident.wizard — link existing / create new."""

    def test_create_new_incident(self):
        """The wizard can create a fresh incident and link it to the complaint."""
        complaint = self._new_complaint()
        location = self.env['nhs.location'].create({'name': 'Theatre 1'})
        category = self.env['nhs.incident.category'].create({'name': 'Surgical'})
        wizard = self.env['nhs.complaint.link.incident.wizard'].create({
            'complaint_id': complaint.id,
            'action': 'create',
            'new_incident_description': 'Wrong-site marking near miss.',
            'new_incident_occurred_at': fields.Datetime.now(),
            'new_incident_location_id': location.id,
            'new_incident_category_id': category.id,
        })
        result = wizard.action_confirm()
        self.assertEqual(complaint.incident_count, 1)
        self.assertEqual(result['res_model'], 'nhs.incident')

    def test_create_requires_location(self):
        """Creating a new incident requires a location."""
        complaint = self._new_complaint()
        wizard = self.env['nhs.complaint.link.incident.wizard'].create({
            'complaint_id': complaint.id,
            'action': 'create',
            'new_incident_occurred_at': fields.Datetime.now(),
        })
        with self.assertRaises(UserError):
            wizard.action_confirm()


@tagged('post_install', '-at_install')
class TestKo41aExportWizard(NhsComplaintCommon):
    """nhs.ko41a.export.wizard — annual return CSV export."""

    def test_export_generates_csv(self):
        """The wizard aggregates complaints in range and produces a CSV + summary."""
        self._new_complaint(received_at='2026-05-01 10:00:00')
        wizard = self.env['nhs.ko41a.export.wizard'].create({
            'date_from': '2026-04-01',
            'date_to': '2026-06-30',
            'company_id': self.company.id,
        })
        wizard.action_generate()
        self.assertEqual(wizard.state, 'done')
        self.assertTrue(wizard.export_file, 'A CSV file should be produced.')
        self.assertTrue(wizard.export_filename.endswith('.csv'))
        # subject_child carries ko41a_code CT01, so nothing is unmapped.
        self.assertEqual(wizard.unmapped_count, 0)

    def test_export_no_records_raises(self):
        """Exporting a range with no matching complaints raises a clear error."""
        wizard = self.env['nhs.ko41a.export.wizard'].create({
            'date_from': '2000-04-01',
            'date_to': '2000-06-30',
            'company_id': self.company.id,
        })
        with self.assertRaises(UserError):
            wizard.action_generate()

    def test_unmapped_subject_flagged(self):
        """A complaint whose subject has no KO41a code is counted as unmapped."""
        no_code_subject = self.Subject.create({'name': 'Uncategorised'})
        self._new_complaint(received_at='2026-05-02 10:00:00',
                            subject_id=no_code_subject.id)
        wizard = self.env['nhs.ko41a.export.wizard'].create({
            'date_from': '2026-04-01',
            'date_to': '2026-06-30',
            'company_id': self.company.id,
        })
        wizard.action_generate()
        self.assertGreaterEqual(wizard.unmapped_count, 1)
