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
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import NhsComplaintCommon


@tagged('post_install', '-at_install')
class TestComplaintLifecycle(NhsComplaintCommon):
    """State-machine / workflow behaviour of nhs.complaint."""

    def test_sequence_on_create_pals_and_complaint(self):
        """PALS and formal complaints get their own prefixed sequence reference."""
        pals = self._new_pals()
        complaint = self._new_complaint()
        self.assertTrue(pals.name.startswith('PALS/'),
                        f'PALS reference should start with PALS/, got {pals.name}')
        self.assertTrue(complaint.name.startswith('COMP/'),
                        f'Complaint reference should start with COMP/, got {complaint.name}')

    def test_state_change_requires_workflow_context(self):
        """Writing `state` directly (outside the action buttons) is refused."""
        pals = self._new_pals()
        with self.assertRaises(UserError):
            pals.write({'state': 'resolved'})
        # …but the workflow context makes it succeed.
        pals.with_context(nhs_workflow=True).write({'state': 'resolved'})
        self.assertEqual(pals.state, 'resolved')

    def test_pals_pathway(self):
        """A PALS concern flows received → in_progress → resolved (de-escalated)."""
        pals = self._new_pals()
        self.assertEqual(pals.state, 'received')
        pals.action_pals_in_progress()
        self.assertEqual(pals.state, 'in_progress')
        pals.action_pals_resolve()
        self.assertEqual(pals.state, 'resolved')
        self.assertTrue(pals.deescalated,
                        'Resolving a PALS concern should mark it de-escalated (KPI).')

    def test_pals_actions_reject_formal_complaint(self):
        """PALS-only buttons raise on a formal complaint."""
        complaint = self._new_complaint()
        with self.assertRaises(UserError):
            complaint.action_pals_in_progress()
        with self.assertRaises(UserError):
            complaint.action_pals_resolve()

    def test_acknowledge_only_for_formal(self):
        """Acknowledgement applies to formal complaints only."""
        pals = self._new_pals()
        with self.assertRaises(UserError):
            pals.action_acknowledge()

    def test_acknowledge_requires_complainant(self):
        """A non-anonymous formal complaint needs a complainant name to acknowledge."""
        complaint = self._new_complaint(complainant_name=False,
                                        complainant_email=False)
        with self.assertRaises(UserError):
            complaint.action_acknowledge()

    def test_acknowledge_autocreates_complainant(self):
        """Acknowledging a formal complaint creates the nhs.complainant record,
        stamps the timestamp, and logs an outbound acknowledgement correspondence."""
        complaint = self._new_complaint()
        self.assertFalse(complaint.complainant_id)
        complaint.action_acknowledge()
        self.assertEqual(complaint.state, 'acknowledged')
        self.assertTrue(complaint.acknowledged)
        self.assertTrue(complaint.acknowledged_at)
        self.assertTrue(complaint.complainant_id,
                        'A complainant record should be auto-created on acknowledge.')
        self.assertEqual(complaint.complainant_id.name, 'Alex Patient')
        ack = complaint.correspondence_ids.filtered(
            lambda c: c.correspondence_type == 'acknowledgement')
        self.assertEqual(len(ack), 1,
                         'Exactly one acknowledgement correspondence should be logged.')

    def test_full_formal_happy_path(self):
        """End-to-end statutory pathway: received → acknowledged → investigation
        → response_draft → awaiting_signoff → signed off → response_sent → closed."""
        complaint = self._new_complaint()
        complaint.action_acknowledge()
        self.assertEqual(complaint.state, 'acknowledged')

        complaint.action_start_investigation()
        self.assertEqual(complaint.state, 'investigation')
        self.assertTrue(complaint.investigation_id,
                        'Starting an investigation auto-creates the investigation record.')
        self.assertTrue(complaint.investigation_id.name.startswith('CINV/'))

        complaint.write({'response_text': '<p>Our full written response.</p>'})
        complaint.action_submit_response_draft()
        self.assertEqual(complaint.state, 'response_draft')

        complaint.action_submit_for_signoff()
        self.assertEqual(complaint.state, 'awaiting_signoff')

        complaint.action_sign_off()
        self.assertTrue(complaint.signed_off_by_id)
        self.assertTrue(complaint.signed_off_at)

        complaint.action_send_response()
        self.assertEqual(complaint.state, 'response_sent')
        self.assertTrue(complaint.response_sent_at)
        response_corr = complaint.correspondence_ids.filtered(
            lambda c: c.correspondence_type == 'response')
        self.assertEqual(len(response_corr), 1)

        complaint.action_close()
        self.assertEqual(complaint.state, 'closed')
        self.assertTrue(complaint.closed_at)

    def test_send_response_requires_signoff(self):
        """A response cannot be sent before it is signed off."""
        complaint = self._new_complaint()
        complaint.action_acknowledge()
        complaint.write({'response_text': '<p>Draft.</p>'})
        complaint.action_submit_response_draft()
        complaint.action_submit_for_signoff()
        with self.assertRaises(UserError):
            complaint.action_send_response()

    def test_submit_draft_requires_text(self):
        """Submitting a draft with no response text is rejected."""
        complaint = self._new_complaint()
        complaint.action_acknowledge()
        with self.assertRaises(UserError):
            complaint.action_submit_response_draft()

    def test_close_formal_requires_response_sent(self):
        """A formal complaint cannot be closed before the response is sent."""
        complaint = self._new_complaint()
        complaint.action_acknowledge()
        with self.assertRaises(UserError):
            complaint.action_close()

    def test_close_blocked_by_open_actions(self):
        """Open learning actions block closure of a complaint."""
        complaint = self._new_complaint()
        complaint.action_acknowledge()
        complaint.write({'response_text': '<p>Response.</p>'})
        complaint.action_submit_response_draft()
        complaint.action_submit_for_signoff()
        complaint.action_sign_off()
        complaint.action_send_response()
        self.env['nhs.action'].create({
            'name': 'Retrain reception staff',
            'due_date': self._days_ago(-7).date(),
            'complaint_id': complaint.id,
        })
        with self.assertRaises(UserError):
            complaint.action_close()

    def test_reopen_increments_counter(self):
        """Re-opening a complaint bumps the reopened counter and posts a note."""
        complaint = self._new_complaint()
        self.assertEqual(complaint.reopened_count, 0)
        complaint.action_reopen(reason='New information received')
        self.assertEqual(complaint.state, 're_opened')
        self.assertEqual(complaint.reopened_count, 1)

    def test_withdraw(self):
        """A complaint can be withdrawn."""
        complaint = self._new_complaint()
        complaint.action_withdraw()
        self.assertEqual(complaint.state, 'withdrawn')

    def test_escalate_phso_creates_record(self):
        """Escalating to the Ombudsman creates a PHSO record and moves state."""
        complaint = self._new_complaint()
        complaint.action_escalate_phso()
        self.assertEqual(complaint.state, 'phso')
        self.assertTrue(complaint.phso_id)
        self.assertEqual(complaint.phso_id.state, 'referred')

    def test_unlink_is_blocked(self):
        """Statutory records cannot be deleted."""
        complaint = self._new_complaint()
        with self.assertRaises(UserError):
            complaint.unlink()
