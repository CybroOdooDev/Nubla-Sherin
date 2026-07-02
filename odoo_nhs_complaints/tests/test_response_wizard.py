# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from odoo import fields

class TestNHSComplaintResponseWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Test Trust'})
        cls.subject = cls.env['nhs.complaint.subject'].create({
            'name': 'Clinical Treatment',
            'ko41a_code': '1a',
        })
        cls.group_handler = cls.env.ref('odoo_nhs_complaints.group_nhs_complaint_handler')
        cls.group_manager = cls.env.ref('odoo_nhs_complaints.group_nhs_complaint_manager')
        cls.group_quality_lead = cls.env.ref('odoo_nhs_complaints.group_nhs_complaint_quality_lead')
        cls.group_hc_handler = cls.env.ref('odoo_nhs_incident_risk.group_hc_handler')
        cls.group_hc_quality_lead = cls.env.ref('odoo_nhs_incident_risk.group_hc_quality_lead')

        cls.group_user = cls.env.ref('base.group_user')

        cls.user_handler = cls.env['res.users'].create({
            'name': 'Handler User',
            'login': 'handler_user',
            'email': 'handler@test.nhs.uk',
            'group_ids': [(6, 0, [cls.group_handler.id, cls.group_user.id, cls.group_hc_handler.id])],
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
        })

        cls.user_quality_lead = cls.env['res.users'].create({
            'name': 'Quality Lead User',
            'login': 'quality_lead_user',
            'email': 'qlead@test.nhs.uk',
            'group_ids': [(6, 0, [cls.group_handler.id, cls.group_quality_lead.id, cls.group_user.id, cls.group_hc_quality_lead.id])],
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
        })

    def test_consent_gate_on_wizard_submit(self):
        """Test that third-party complaints with pending/refused consent block submission."""
        complaint = self.env['nhs.complaint'].with_user(self.user_handler).create({
            'record_type': 'complaint',
            'subject_summary': 'Third party issue',
            'description': 'Test description',
            'severity': 'low',
            'received_via': 'email',
            'subject_id': self.subject.id,
            'is_third_party': True,
            'consent_status': 'pending',
            'complainant_name': 'Representative',
        })
        
        complaint.action_acknowledge()
        timescale = self.env['nhs.complaint.timescale'].create({'name': '40 days', 'working_days': 40})
        complaint.action_agree_timescale(timescale_id=timescale.id)
        
        wizard = self.env['nhs.complaint.response.wizard'].with_user(self.user_handler).create({
            'complaint_id': complaint.id,
            'response_text': '<p>This is the response draft.</p>',
        })
        
        with self.assertRaises(UserError):
            wizard.action_submit_for_signoff()

        complaint.write({'consent_status': 'obtained'})
        wizard.action_submit_for_signoff()
        self.assertEqual(complaint.state, 'awaiting_signoff')
        self.assertEqual(complaint.response_text, '<p>This is the response draft.</p>')

    def test_sign_off_permission_and_actions(self):
        """Test sign-off permission checks and immediate sending options in wizard."""
        complaint = self.env['nhs.complaint'].create({
            'record_type': 'complaint',
            'subject_summary': 'Test issue',
            'description': 'Test description',
            'severity': 'low',
            'received_via': 'email',
            'subject_id': self.subject.id,
            'is_third_party': False,
            'consent_status': 'not_required',
            'complainant_name': 'Patient Self',
        })
        complaint.action_acknowledge()
        timescale = self.env['nhs.complaint.timescale'].create({'name': '40 days', 'working_days': 40})
        complaint.action_agree_timescale(timescale_id=timescale.id)

        wizard1 = self.env['nhs.complaint.response.wizard'].with_user(self.user_handler).create({
            'complaint_id': complaint.id,
            'response_text': '<p>Response text</p>',
            'sign_off_now': True,
        })
        with self.assertRaises(UserError):
            wizard1.action_submit_for_signoff()

        wizard2 = self.env['nhs.complaint.response.wizard'].with_user(self.user_quality_lead).create({
            'complaint_id': complaint.id,
            'response_text': '<p>Quality lead response text</p>',
            'sign_off_now': True,
            'send_immediately': True,
            'response_method': 'email',
        })
        wizard2.action_submit_for_signoff()
        
        self.assertEqual(complaint.state, 'response_sent')
        self.assertEqual(complaint.signed_off_by_id, self.user_quality_lead)
        self.assertIsNotNone(complaint.signed_off_at)
        self.assertIsNotNone(complaint.response_sent_at)
        
        correspondence = self.env['nhs.complaint.correspondence'].search([('complaint_id', '=', complaint.id)])
        self.assertEqual(len(correspondence), 2)
        response_corr = correspondence.filtered(lambda c: c.correspondence_type == 'response')
        self.assertTrue(response_corr)
        self.assertEqual(response_corr.direction, 'outbound')
        self.assertEqual(response_corr.channel, 'email')

    def test_investigation_alignment_and_chronology(self):
        """Test that complaint investigations can be aligned and managed with structured chronology."""
        complaint = self.env['nhs.complaint'].create({
            'record_type': 'complaint',
            'subject_summary': 'Test chronology alignment',
            'description': 'Test description',
            'severity': 'low',
            'received_via': 'email',
            'subject_id': self.subject.id,
            'is_third_party': False,
            'consent_status': 'not_required',
            'complainant_name': 'Patient Self',
        })
        complaint.action_acknowledge()
        timescale = self.env['nhs.complaint.timescale'].create({'name': '40 days', 'working_days': 40})
        complaint.action_agree_timescale(timescale_id=timescale.id)
        complaint.action_start_investigation()
        
        # Verify investigation record was created
        self.assertTrue(complaint.investigation_id)
        investigation = complaint.investigation_id
        
        # Write to investigation via related fields on complaint
        complaint.write({
            'investigation_lead_investigator_id': self.user_quality_lead.id,
            'investigation_points_of_complaint': 'Point 1: Delay in appointment.',
            'investigation_findings': 'Findings 1: Delay was due to system outage.',
            'investigation_lessons_learned': 'Lessons: Implement offline backup.',
            'investigation_upheld_status': 'upheld',
        })
        
        # Verify that investigation record was updated correctly
        self.assertEqual(investigation.lead_investigator_id, self.user_quality_lead)
        self.assertEqual(investigation.points_of_complaint, 'Point 1: Delay in appointment.')
        self.assertEqual(investigation.findings, 'Findings 1: Delay was due to system outage.')
        self.assertEqual(investigation.lessons_learned, 'Lessons: Implement offline backup.')
        self.assertEqual(investigation.upheld_status, 'upheld')
        
        # Add chronology entry via timeline
        timeline_entry = self.env['nhs.complaint.investigation.timeline'].create({
            'investigation_id': investigation.id,
            'happened_at': fields.Datetime.now(),
            'entry': 'Patient arrived at clinic.',
            'source': 'Reception log',
        })
        
        # Verify timeline relations
        self.assertIn(timeline_entry, investigation.timeline_ids)
        self.assertIn(timeline_entry, complaint.investigation_timeline_ids)
        
        # Edit timeline entry from complaint related field
        complaint.write({
            'investigation_timeline_ids': [(1, timeline_entry.id, {'entry': 'Patient arrived early at clinic.'})]
        })
        self.assertEqual(timeline_entry.entry, 'Patient arrived early at clinic.')

    def test_response_view_wizard_fields(self):
        """Test that response view wizard populates the signed off values correctly."""
        complaint = self.env['nhs.complaint'].create({
            'record_type': 'complaint',
            'subject_summary': 'Test response view',
            'description': 'Test description',
            'severity': 'low',
            'received_via': 'email',
            'subject_id': self.subject.id,
            'is_third_party': False,
            'consent_status': 'not_required',
            'complainant_name': 'Patient Self',
        })
        complaint.action_acknowledge()
        timescale = self.env['nhs.complaint.timescale'].create({'name': '40 days', 'working_days': 40})
        complaint.action_agree_timescale(timescale_id=timescale.id)
        
        # Submit & Sign-off response
        wizard = self.env['nhs.complaint.response.wizard'].with_user(self.user_quality_lead).create({
            'complaint_id': complaint.id,
            'response_text': '<p>Signed response body.</p>',
            'sign_off_now': True,
            'send_immediately': True,
            'response_method': 'email',
        })
        wizard.action_submit_for_signoff()
        
        # Verify fields on complaint are populated
        self.assertEqual(complaint.state, 'response_sent')
        self.assertEqual(complaint.signed_off_by_id, self.user_quality_lead)
        self.assertEqual(complaint.response_method, 'email')
        self.assertEqual(complaint.response_text, '<p>Signed response body.</p>')
        
        # Initialize the response view wizard
        view_wizard = self.env['nhs.complaint.response.view.wizard'].create({
            'complaint_id': complaint.id,
        })
        
        # Verify the related values are computed/populated on the wizard
        self.assertEqual(view_wizard.signed_off_by_id, self.user_quality_lead)
        self.assertEqual(view_wizard.response_method, 'email')
        self.assertEqual(view_wizard.response_text, '<p>Signed response body.</p>')
        self.assertIsNotNone(view_wizard.signed_off_at)
        self.assertIsNotNone(view_wizard.response_sent_at)

