# -*- coding: utf-8 -*-
"""Access-rights (ir.model.access) and record-rule (ir.rule) enforcement."""
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from .common import NhsCommon


@tagged('post_install', '-at_install')
class TestSecurity(NhsCommon):

    def test_reporter_can_create_but_not_write_incident(self):
        """Reporters may file incidents (create) but not edit them (perm_write=0)."""
        inc = self.env['nhs.incident'].with_user(self.user_reporter).create(
            self._incident_vals())
        self.assertTrue(inc.name.startswith('INC/'))
        with self.assertRaises(AccessError):
            inc.with_user(self.user_reporter).write({'description': 'edited'})

    def test_reporter_sees_only_own_incidents(self):
        """The reporter_own record rule hides incidents created by other users."""
        other = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'rep2', 'login': 'nhs_reporter2', 'email': 'r2@test.com',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('odoo_nhs_incident_risk.group_hc_reporter').id])],
        })
        inc = self.env['nhs.incident'].with_user(self.user_reporter).create(
            self._incident_vals())
        # The owning reporter can read it...
        self.assertTrue(inc.with_user(self.user_reporter).read(['name']))
        # ...another reporter cannot.
        with self.assertRaises(AccessError):
            inc.with_user(other).read(['name'])

    def test_handler_can_write_incident(self):
        """Handlers have write access (perm_write=1) to incidents."""
        inc = self._make_incident()
        inc.with_user(self.user_handler).write({'immediate_action': 'isolated area'})
        self.assertEqual(inc.immediate_action, 'isolated area')

    def test_handler_cannot_close_incident(self):
        """Closing is gated to Quality Lead even though handlers can write."""
        inc = self._make_incident()
        inc.action_accept()
        inc.with_context(nhs_workflow=True).write({'state': 'pending_closure'})
        with self.assertRaises(UserError):
            inc.with_user(self.user_handler).action_close()

    def test_safeguarding_incident_hidden_from_plain_handler(self):
        """A safeguarding-flagged incident is hidden from a plain handler but
        visible to a safeguarding officer (validates the merged record rule)."""
        inc = self._make_incident()
        inc.write({'safeguarding_flag': True})
        with self.assertRaises(AccessError):
            inc.with_user(self.user_handler).read(['name'])
        # Safeguarding officer (also a handler) can see it.
        self.assertTrue(inc.with_user(self.user_safeguarding).read(['name']))

    def test_risk_manager_cannot_unlink_risk(self):
        """No group is granted perm_unlink on nhs.risk (immutable register)."""
        risk = self._make_risk()
        with self.assertRaises(AccessError):
            risk.with_user(self.user_riskmgr).unlink()
