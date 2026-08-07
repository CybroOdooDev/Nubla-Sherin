# -*- coding: utf-8 -*-
"""Statutory compliance: Duty of Candour deadlines/state, RIDDOR determination
wizard + deadlines, CQC notifications, notification-rule engine, LFPSE export."""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from .common import NhsCommon


@tagged('post_install', '-at_install')
class TestStatutory(NhsCommon):

    # ── Duty of Candour ───────────────────────────────────────────────
    def test_doc_written_deadline_is_10_working_days(self):
        """The written-notification deadline is 10 working days after the trigger."""
        self.env['nhs.holiday'].search([]).unlink()
        inc = self._make_incident()
        doc = self.env['nhs.duty.of.candour'].create({
            'incident_id': inc.id,
            'triggered_at': fields.Datetime.to_datetime('2026-06-01 09:00:00'),  # Mon
        })
        # 10 working days from Mon 1 Jun -> Mon 15 Jun.
        self.assertEqual(doc.written_deadline, fields.Date.to_date('2026-06-15'))

    def test_doc_state_overdue_then_complete(self):
        """DoC is overdue past deadline, and complete once all stages are done."""
        inc = self._make_incident()
        doc = self.env['nhs.duty.of.candour'].create({
            'incident_id': inc.id,
            'triggered_at': fields.Datetime.to_datetime('2020-01-01 09:00:00'),
        })
        self.assertEqual(doc.state, 'overdue')
        doc.write({'verbal_done': True, 'written_done': True,
                   'findings_shared_done': True})
        self.assertEqual(doc.state, 'complete')

    # ── RIDDOR ────────────────────────────────────────────────────────
    def test_riddor_wizard_fatal_is_reportable(self):
        """A fatal injury is RIDDOR-reportable under the 'death' category."""
        inc = self._make_incident()
        wiz = self.env['nhs.riddor.wizard'].create({
            'incident_id': inc.id, 'anyone_injured': True,
            'worker_injured': True, 'fatal': True})
        self.assertTrue(wiz.reportable)
        self.assertEqual(wiz.riddor_category, 'death')
        wiz.action_confirm()
        self.assertTrue(inc.riddor_id)
        self.assertEqual(inc.riddor_id.riddor_category, 'death')
        self.assertFalse(inc.riddor_hint)

    def test_riddor_over_7_day_requires_worker(self):
        """Over-7-day incapacitation is only reportable for a worker."""
        inc = self._make_incident()
        wiz = self.env['nhs.riddor.wizard'].create({
            'incident_id': inc.id, 'anyone_injured': True,
            'worker_injured': False, 'over_7_day': True})
        self.assertFalse(wiz.reportable)
        wiz.worker_injured = True
        self.assertTrue(wiz.reportable)
        self.assertEqual(wiz.riddor_category, 'over_7_day')

    def test_riddor_deadline_computation(self):
        """RIDDOR deadline = 10 days (death/specified) or 15 days (over-7-day)."""
        inc = self._make_incident(
            occurred_at=fields.Datetime.to_datetime('2026-03-02 09:00:00'))
        riddor = self.env['nhs.riddor'].create({
            'incident_id': inc.id, 'reportable': True, 'riddor_category': 'death'})
        self.assertEqual(riddor.report_deadline, fields.Date.to_date('2026-03-12'))
        riddor.riddor_category = 'over_7_day'
        self.assertEqual(riddor.report_deadline, fields.Date.to_date('2026-03-17'))

    # ── CQC ───────────────────────────────────────────────────────────
    def test_cqc_notification_submit_cycle(self):
        """Submitting a CQC notification stamps submitter/date; reopening clears them."""
        inc = self._make_incident()
        ntype = self.env['nhs.cqc.notification.type'].create({'name': 'Death (test)'})
        notif = self.env['nhs.cqc.notification'].create({
            'incident_id': inc.id, 'notification_type_id': ntype.id})
        notif.action_submit()
        self.assertEqual(notif.state, 'submitted')
        self.assertTrue(notif.submitted_at)
        self.assertEqual(notif.submitted_by_id, self.env.user)
        notif.action_required()
        self.assertEqual(notif.state, 'required')
        self.assertFalse(notif.submitted_at)

    # ── Notification rule engine ──────────────────────────────────────
    def test_notification_rule_sets_lfpse_and_safeguarding(self):
        """A matching rule flips LFPSE to pending and sets the safeguarding flag."""
        rule = self.env['nhs.notification.rule'].create({
            'name': 'Moderate -> LFPSE + SG (test)', 'provider_type': 'all',
            'min_harm_grade': 'moderate', 'require_lfpse': True,
            'require_safeguarding': True, 'active': True,
        })
        inc = self._make_incident(harm_grade='moderate')
        rule.evaluate(inc)
        self.assertEqual(inc.lfpse_state, 'pending')
        self.assertTrue(inc.safeguarding_flag)

    def test_notification_rule_below_min_harm_does_not_fire(self):
        """A rule with min_harm 'death' must not fire for a low-harm incident."""
        rule = self.env['nhs.notification.rule'].create({
            'name': 'Death -> LFPSE (test)', 'provider_type': 'all',
            'min_harm_grade': 'death', 'require_lfpse': True, 'active': True,
        })
        inc = self._make_incident(harm_grade='low')
        rule.evaluate(inc)
        self.assertEqual(inc.lfpse_state, 'not_required')

    def test_notification_rule_creates_cqc_notification(self):
        """A require_cqc rule creates the configured CQC notification once (idempotent)."""
        ntype = self.env['nhs.cqc.notification.type'].create({'name': 'DoLS (test)'})
        rule = self.env['nhs.notification.rule'].create({
            'name': 'All -> CQC (test)', 'provider_type': 'all',
            'require_cqc': True, 'cqc_notification_type_id': ntype.id, 'active': True,
        })
        inc = self._make_incident()
        rule.evaluate(inc)
        rule.evaluate(inc)  # second pass must not duplicate
        self.assertEqual(len(inc.cqc_notification_ids.filtered(
            lambda n: n.notification_type_id == ntype)), 1)

    # ── LFPSE export ──────────────────────────────────────────────────
    def test_lfpse_export_batch(self):
        """LFPSE export collects pending incidents and marks them exported."""
        inc = self._make_incident(
            occurred_at=fields.Datetime.to_datetime('2026-04-10 09:00:00'),
            physical_harm='low')
        inc.with_context(nhs_workflow=True).write({'lfpse_state': 'pending'})
        wiz = self.env['nhs.lfpse.export.wizard'].create({
            'date_from': fields.Date.to_date('2026-04-01'),
            'date_to': fields.Date.to_date('2026-04-30'),
            'export_format': 'csv',
        })
        self.assertIn(inc, wiz.incident_ids)
        self.assertGreaterEqual(wiz.incident_count, 1)
        wiz.action_export()
        self.assertEqual(inc.lfpse_state, 'exported')
        batch = self.env['nhs.lfpse.submission'].search(
            [('incident_ids', 'in', inc.id)], limit=1)
        self.assertEqual(batch.state, 'exported')
        self.assertTrue(batch.file_attachment_id)
