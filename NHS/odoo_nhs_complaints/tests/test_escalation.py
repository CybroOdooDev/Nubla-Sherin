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
class TestEscalation(NhsComplaintCommon):
    """PALS → formal complaint escalation wizard."""

    def _run_wizard(self, pals):
        """Create an escalation wizard pre-filled from the given PALS concern."""
        return self.env['nhs.complaint.escalate.wizard'].create({
            'pals_id': pals.id,
            'subject_summary': pals.subject_summary,
            'description': pals.description,
            'severity': 'high',
            'timescale_id': self.timescale_standard.id,
            'subject_id': self.subject_child.id,
        })

    def test_escalate_creates_formal_complaint(self):
        """Escalating a PALS concern spawns a linked formal complaint and marks
        the original concern as escalated."""
        pals = self._new_pals(location_id=False)
        wizard = self._run_wizard(pals)
        action = wizard.action_escalate()

        self.assertEqual(pals.state, 'escalated')
        complaint = self.Complaint.browse(action['res_id'])
        self.assertEqual(complaint.record_type, 'complaint')
        self.assertEqual(complaint.severity, 'high')
        self.assertEqual(complaint.pals_origin_ref, pals.name,
                         'The new complaint should retain the originating PALS reference.')
        self.assertTrue(complaint.name.startswith('COMP/'))

    def test_cannot_escalate_closed_pals(self):
        """A concern that is already escalated/closed/withdrawn cannot be escalated."""
        pals = self._new_pals()
        self._run_wizard(pals).action_escalate()
        with self.assertRaises(UserError):
            self._run_wizard(pals).action_escalate()

    def test_wizard_onchange_prefills_from_pals(self):
        """The wizard onchange copies summary/description/subject from the concern."""
        pals = self._new_pals()
        wizard = self.env['nhs.complaint.escalate.wizard'].new({'pals_id': pals.id})
        wizard._onchange_pals_id()
        self.assertEqual(wizard.subject_summary, pals.subject_summary)
        self.assertEqual(wizard.description, pals.description)
        self.assertEqual(wizard.subject_id, pals.subject_id)
