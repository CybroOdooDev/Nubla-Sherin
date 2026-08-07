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
"""Shared fixtures for the NHS Complaints & PALS test suite.

Every DB-dependent test class inherits from :class:`NhsComplaintCommon`, which
builds a small but representative graph of seed data in ``setUpClass`` (one
class-level transaction, rolled back to a savepoint per test method).
"""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class NhsComplaintCommon(TransactionCase):
    """Shared base test case providing seeded subjects, timescales, groups, users and factory helpers."""

    @classmethod
    def setUpClass(cls):
        """Create the module's reference records, per-group test users and factory shortcuts used by all subclasses."""
        super().setUpClass()
        cls.Complaint = cls.env['nhs.complaint']
        cls.Complainant = cls.env['nhs.complainant']
        cls.Subject = cls.env['nhs.complaint.subject']
        cls.Timescale = cls.env['nhs.complaint.timescale']
        cls.Phso = cls.env['nhs.complaint.phso']
        cls.Investigation = cls.env['nhs.complaint.investigation']
        cls.OrgResponse = cls.env['nhs.complaint.org.response']
        cls.Correspondence = cls.env['nhs.complaint.correspondence']

        cls.company = cls.env.company

        # ── Seed data shipped by the module (data/*.xml) ──────────────────
        cls.subject_parent = cls.env.ref(
            'odoo_nhs_complaints.subject_clinical_treatment')
        cls.subject_child = cls.env.ref(
            'odoo_nhs_complaints.subject_ct_diagnosis')
        cls.timescale_standard = cls.env.ref(
            'odoo_nhs_complaints.timescale_standard_40')
        cls.timescale_major = cls.env.ref(
            'odoo_nhs_complaints.timescale_major_negotiated')

        # ── Groups ────────────────────────────────────────────────────────
        cls.group_handler = cls.env.ref(
            'odoo_nhs_complaints.group_nhs_complaint_handler')
        cls.group_manager = cls.env.ref(
            'odoo_nhs_complaints.group_nhs_complaint_manager')
        cls.group_quality_lead = cls.env.ref(
            'odoo_nhs_complaints.group_nhs_complaint_quality_lead')

        # ── Users (Odoo 19: res.users.group_ids, NOT groups_id) ──────────
        cls.user_handler = cls.env['res.users'].create({
            'name': 'Test Handler',
            'login': 'nhs_test_handler',
            'email': 'handler@nhs.test',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.group_handler.id,
            ])],
        })
        cls.user_quality_lead = cls.env['res.users'].create({
            'name': 'Test Quality Lead',
            'login': 'nhs_test_quality_lead',
            'email': 'ql@nhs.test',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.group_quality_lead.id,
            ])],
        })
        # A plain internal user with NO complaints access at all.
        cls.user_no_access = cls.env['res.users'].create({
            'name': 'Test No Access',
            'login': 'nhs_test_no_access',
            'email': 'noaccess@nhs.test',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

        # ── A partner used as a partner organisation for multi-org tests ──
        cls.partner_org = cls.env['res.partner'].create({
            'name': 'Neighbouring NHS Trust',
            'email': 'complaints@neighbour.nhs.test',
        })

    # ── Factory helpers ──────────────────────────────────────────────────
    @classmethod
    def _new_pals(cls, **overrides):
        """Create a PALS concern record with sensible defaults, overridable per test."""
        vals = {
            'record_type': 'pals',
            'subject_summary': 'Rude reception staff',
            'description': 'Front desk was unhelpful.',
            'subject_id': cls.subject_child.id,
            'received_via': 'phone',
        }
        vals.update(overrides)
        return cls.Complaint.create(vals)

    @classmethod
    def _new_complaint(cls, **overrides):
        """Create a formal complaint record with sensible defaults, overridable per test."""
        vals = {
            'record_type': 'complaint',
            'subject_summary': 'Delayed diagnosis',
            'description': 'Diagnosis was delayed by several weeks.',
            'subject_id': cls.subject_child.id,
            'received_via': 'letter',
            'severity': 'medium',
            'complainant_name': 'Alex Patient',
            'complainant_email': 'alex@patient.test',
        }
        vals.update(overrides)
        return cls.Complaint.create(vals)

    @staticmethod
    def _days_ago(days):
        """Return a datetime the given number of days before now."""
        return fields.Datetime.now() - timedelta(days=days)
