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
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import NhsComplaintCommon


@tagged('post_install', '-at_install')
class TestSecurity(NhsComplaintCommon):
    """Access-control model (ir.model.access.csv + ir.rule + Python unlink)."""

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_user_without_group_cannot_read(self):
        """A plain internal user with no complaints group cannot read complaints."""
        complaint = self._new_complaint()
        with self.assertRaises(AccessError):
            complaint.with_user(self.user_no_access).read(['subject_summary'])

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_user_without_group_cannot_create(self):
        """A plain internal user with no complaints group cannot create complaints."""
        with self.assertRaises(AccessError):
            self.Complaint.with_user(self.user_no_access).create({
                'subject_summary': 'Illegitimate',
                'description': 'Should be denied.',
                'subject_id': self.subject_child.id,
            })

    def test_handler_can_create_and_read(self):
        """A complaint handler can create and read complaints (ACL grants R/W/C)."""
        complaint = self.Complaint.with_user(self.user_handler).create({
            'subject_summary': 'Handler-created',
            'description': 'Logged by a handler.',
            'subject_id': self.subject_child.id,
        })
        self.assertTrue(complaint.name.startswith('PALS/'))
        self.assertEqual(
            complaint.with_user(self.user_handler).subject_summary,
            'Handler-created',
        )

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_handler_cannot_delete_reference_data(self):
        """Handlers have perm_unlink=0 on reference models (subject/timescale) —
        deletion is refused at the ACL layer (AccessError)."""
        subject = self.Subject.create({'name': 'Temp subject'})
        with self.assertRaises(AccessError):
            subject.with_user(self.user_handler).unlink()

    def test_complaint_unlink_hits_python_guard(self):
        """nhs.complaint.unlink() raises the statutory UserError before the ACL
        check, so even a quality lead (perm_unlink=1) is blocked from deleting."""
        complaint = self._new_complaint()
        with self.assertRaises(UserError):
            complaint.with_user(self.user_quality_lead).unlink()
