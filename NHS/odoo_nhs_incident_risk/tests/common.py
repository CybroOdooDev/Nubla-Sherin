# -*- coding: utf-8 -*-
"""Shared fixtures for the NHS Incident & Risk test suite.

Seed notification rules are disabled here so that ``nhs.incident`` creation is
deterministic (the install seeds rules that would otherwise auto-flag
safeguarding / create CQC notifications on every incident). Notification-rule
behaviour is tested explicitly in :mod:`test_statutory` with purpose-built rules.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, new_test_user


class NhsCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({
            'provider_type': 'nhs_trust',
            'doc_trigger_grade': 'moderate',
            'anonymous_reporting_allowed': True,
            'public_form_enabled': True,
        })

        # Deterministic incidents: silence seeded notification rules.
        cls.env['nhs.notification.rule'].search([]).write({'active': False})

        # ── Reference data ────────────────────────────────────────────
        cls.register_local = cls.env['nhs.risk.register'].create({
            'name': 'Local Register (test)', 'tier': 'local',
            'company_id': cls.company.id,
        })
        cls.register_baf = cls.env['nhs.risk.register'].create({
            'name': 'BAF (test)', 'tier': 'baf', 'company_id': cls.company.id,
        })
        cls.risk_cat = cls.env['nhs.risk.category'].create({
            'name': 'Clinical (test)', 'appetite_threshold': 6,
        })
        cls.inc_cat = cls.env['nhs.incident.category'].create({
            'name': 'Slips, Trips & Falls (test)',
        })
        cls.location = cls.env['nhs.location'].create({
            'name': 'Ward A (test)', 'location_type': 'unit',
            'company_id': cls.company.id,
        })

        # ── Users (use new_test_user → correct v19 group wiring) ──────
        cls.user_reporter = new_test_user(
            cls.env, 'nhs_reporter',
            groups='base.group_user,odoo_nhs_incident_risk.group_hc_reporter')
        cls.user_handler = new_test_user(
            cls.env, 'nhs_handler',
            groups='base.group_user,odoo_nhs_incident_risk.group_hc_handler')
        cls.user_quality = new_test_user(
            cls.env, 'nhs_quality',
            groups='base.group_user,odoo_nhs_incident_risk.group_hc_quality_lead')
        cls.user_riskmgr = new_test_user(
            cls.env, 'nhs_riskmgr',
            groups='base.group_user,odoo_nhs_incident_risk.group_hc_risk_manager')
        # Handler who is ALSO a safeguarding officer (should see safeguarding cases).
        cls.user_safeguarding = new_test_user(
            cls.env, 'nhs_safeguarding',
            groups='base.group_user,odoo_nhs_incident_risk.group_hc_handler,'
                   'odoo_nhs_incident_risk.group_hc_safeguarding')

    # ── Builders ──────────────────────────────────────────────────────
    @classmethod
    def _incident_vals(cls, **overrides):
        vals = {
            'incident_kind': 'incident',
            'occurred_at': fields.Datetime.now() - timedelta(hours=2),
            'location_id': cls.location.id,
            'category_id': cls.inc_cat.id,
            'description': 'Patient slipped on a wet floor (test).',
            'reported_via': 'backend',
        }
        vals.update(overrides)
        return vals

    @classmethod
    def _make_incident(cls, **overrides):
        return cls.env['nhs.incident'].create(cls._incident_vals(**overrides))

    @classmethod
    def _risk_vals(cls, **overrides):
        vals = {
            'title': 'Medication error risk (test)',
            'cause': 'IF controls fail',
            'event': 'THEN wrong dose given',
            'effect': 'RESULTING IN patient harm',
            'category_id': cls.risk_cat.id,
            'register_id': cls.register_local.id,
            'risk_owner_id': cls.env.user.id,
            'inherent_consequence': '4',
            'inherent_likelihood': '4',
            'current_consequence': '4',
            'current_likelihood': '3',
        }
        vals.update(overrides)
        return vals

    @classmethod
    def _make_risk(cls, **overrides):
        return cls.env['nhs.risk'].create(cls._risk_vals(**overrides))
