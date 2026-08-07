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
class TestMultiOrg(NhsComplaintCommon):
    """Multi-organisation (joint response) coordination logic."""

    def _new_multi_org(self):
        """Create a formal complaint flagged multi-organisation with the shared partner org attached."""
        return self._new_complaint(
            is_multi_org=True,
            partner_org_ids=[(6, 0, [self.partner_org.id])],
        )

    def test_org_response_synced_on_create(self):
        """Creating a multi-org complaint with partners spawns pending contributions."""
        complaint = self._new_multi_org()
        self.assertEqual(len(complaint.org_response_ids), 1)
        self.assertEqual(complaint.org_response_ids.org_id, self.partner_org)
        self.assertEqual(complaint.org_response_ids.state, 'pending')
        self.assertFalse(complaint.all_orgs_responded)

    def test_org_response_bidirectional_sync(self):
        """Creating an org.response line adds the partner to partner_org_ids."""
        complaint = self._new_complaint(is_multi_org=True)
        self.assertFalse(complaint.partner_org_ids)
        self.OrgResponse.create({
            'complaint_id': complaint.id,
            'org_id': self.partner_org.id,
        })
        self.assertIn(self.partner_org, complaint.partner_org_ids)

    def test_all_orgs_responded_flag(self):
        """all_orgs_responded turns True only once every contribution is submitted."""
        complaint = self._new_multi_org()
        line = complaint.org_response_ids
        self.assertFalse(complaint.all_orgs_responded)
        line.write({'response_text': 'Our part of the response.'})
        line.action_submit()
        self.assertEqual(line.state, 'submitted')
        self.assertTrue(complaint.all_orgs_responded)

    def test_org_response_submit_requires_text(self):
        """A partner cannot submit an empty contribution."""
        complaint = self._new_multi_org()
        with self.assertRaises(UserError):
            complaint.org_response_ids.action_submit()

    def test_signoff_blocked_until_all_orgs_respond(self):
        """Sign-off is gated on partner contributions, deadline agreement, and text."""
        complaint = self._new_multi_org()
        complaint.action_acknowledge()
        complaint.write({'response_text': '<p>Joint response.</p>'})
        complaint.action_submit_response_draft()

        # Deadline not yet agreed -> blocked.
        with self.assertRaises(UserError):
            complaint.action_submit_for_signoff()

        complaint.write({'multi_org_deadline_agreed': True})
        # Partner contribution still pending -> blocked.
        with self.assertRaises(UserError):
            complaint.action_submit_for_signoff()

        # Submit the partner contribution -> sign-off now allowed.
        line = complaint.org_response_ids
        line.write({'response_text': 'Partner content.'})
        line.action_submit()
        complaint.action_submit_for_signoff()
        self.assertEqual(complaint.state, 'awaiting_signoff')

    def test_removing_pending_org_response_unlinks(self):
        """Un-ticking a partner removes only its still-pending contribution line."""
        complaint = self._new_multi_org()
        complaint.write({'partner_org_ids': [(5, 0, 0)]})
        self.assertFalse(complaint.org_response_ids,
                         'Pending contributions should be removed with their partner.')
