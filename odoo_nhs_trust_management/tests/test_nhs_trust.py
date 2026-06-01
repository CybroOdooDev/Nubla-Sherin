# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo import fields

class TestNhsTrust(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestNhsTrust, cls).setUpClass()
        # Fetch preloaded seed data records for regional geographics
        cls.region_eng = cls.env.ref('odoo_nhs_trust_management.region_england_ney')
        cls.region_sco = cls.env.ref('odoo_nhs_trust_management.region_scotland_n')
        
        # Fetch preloaded trust types
        cls.type_eng = cls.env.ref('odoo_nhs_trust_management.type_england_acute')
        cls.type_sco = cls.env.ref('odoo_nhs_trust_management.type_scotland_territorial')
        
        # Fetch preloaded ICB and Health Board references
        cls.icb_eng = cls.env.ref('odoo_nhs_trust_management.icb_northeast_cumbria')
        cls.hb_sco = cls.env.ref('odoo_nhs_trust_management.hb_grampian')

    def test_01_ods_code_constraints(self):
        """ Test ODS Code formatting, casing, and lengths """
        # Test lower casing auto-capitalizes
        trust = self.env['nhs.trust'].create({
            'name': 'Test Capitalize Trust',
            'ods_code': 'abc',
            'health_system': 'nhs_england',
            'trust_type_id': self.type_eng.id,
            'region_id': self.region_eng.id,
            'icb_id': self.icb_eng.id,
        })
        self.assertEqual(trust.ods_code, 'ABC', "ODS code should be automatically capitalized!")

        # Test too short
        with self.assertRaises(ValidationError):
            self.env['nhs.trust'].create({
                'name': 'Short Code Trust',
                'ods_code': 'AB',
                'health_system': 'nhs_england',
                'trust_type_id': self.type_eng.id,
                'region_id': self.region_eng.id,
                'icb_id': self.icb_eng.id,
            })

        # Test too long
        with self.assertRaises(ValidationError):
            self.env['nhs.trust'].create({
                'name': 'Long Code Trust',
                'ods_code': 'ABCDEF',
                'health_system': 'nhs_england',
                'trust_type_id': self.type_eng.id,
                'region_id': self.region_eng.id,
                'icb_id': self.icb_eng.id,
            })

        # Test non-alphanumeric character
        with self.assertRaises(ValidationError):
            self.env['nhs.trust'].create({
                'name': 'Non-Alphanumeric Trust',
                'ods_code': 'AB-C',
                'health_system': 'nhs_england',
                'trust_type_id': self.type_eng.id,
                'region_id': self.region_eng.id,
                'icb_id': self.icb_eng.id,
            })

    def test_02_geographical_constraints(self):
        """ Test England and Scotland geographical system boundaries """
        # England Trust attempting to set a Scottish Health Board
        with self.assertRaises(ValidationError):
            self.env['nhs.trust'].create({
                'name': 'Conflicted England Trust',
                'ods_code': 'ENGHB',
                'health_system': 'nhs_england',
                'trust_type_id': self.type_eng.id,
                'region_id': self.region_eng.id,
                'icb_id': self.icb_eng.id,
                'health_board_id': self.hb_sco.id,
            })

        # Scotland Trust attempting to set an English ICB
        with self.assertRaises(ValidationError):
            self.env['nhs.trust'].create({
                'name': 'Conflicted Scotland Trust',
                'ods_code': 'SCOIC',
                'health_system': 'nhs_scotland',
                'trust_type_id': self.type_sco.id,
                'region_id': self.region_sco.id,
                'health_board_id': self.hb_sco.id,
                'icb_id': self.icb_eng.id,
            })

        # England Trust missing ICB
        with self.assertRaises(ValidationError):
            self.env['nhs.trust'].create({
                'name': 'Missing ICB Trust',
                'ods_code': 'MISIC',
                'health_system': 'nhs_england',
                'trust_type_id': self.type_eng.id,
                'region_id': self.region_eng.id,
            })

    def test_03_workflow_direct_state_write_blocking(self):
        """ Confirm direct write() to trust state raises UserError """
        trust = self.env['nhs.trust'].create({
            'name': 'State Write Test Trust',
            'ods_code': 'SWRIT',
            'health_system': 'nhs_england',
            'trust_type_id': self.type_eng.id,
            'region_id': self.region_eng.id,
            'icb_id': self.icb_eng.id,
        })
        
        # Directly changing state should raise UserError
        with self.assertRaises(UserError):
            trust.write({'state': 'active'})

    def test_04_wizard_transition_and_logs(self):
        """ Test state changes via wizard and verify logs immutability """
        trust = self.env['nhs.trust'].create({
            'name': 'Wizard Test Trust',
            'ods_code': 'WIZTR',
            'health_system': 'nhs_england',
            'trust_type_id': self.type_eng.id,
            'region_id': self.region_eng.id,
            'icb_id': self.icb_eng.id,
        })
        self.assertEqual(trust.state, 'draft')

        # Test wizard with short justification reason (< 5 chars)
        with self.assertRaises(ValidationError):
            self.env['nhs.trust.state.change.wizard'].create({
                'trust_id': trust.id,
                'new_state': 'under_review',
                'reason': 'Bad',
            })

        # Test valid wizard execution
        wizard = self.env['nhs.trust.state.change.wizard'].create({
            'trust_id': trust.id,
            'new_state': 'under_review',
            'reason': 'Valid justification reason provided.',
        })
        wizard.action_confirm()

        self.assertEqual(trust.state, 'under_review', "Trust state should have updated to under_review!")
        
        # Verify log entry is populated
        logs = self.env['nhs.trust.state.log'].search([('trust_id', '=', trust.id)])
        self.assertEqual(len(logs), 1, "There should be one audit log entry created!")
        log = logs[0]
        self.assertEqual(log.from_state, 'draft')
        self.assertEqual(log.to_state, 'under_review')
        self.assertEqual(log.reason, 'Valid justification reason provided.')

        # Verify log records are strictly immutable (write raises UserError)
        with self.assertRaises(UserError):
            log.write({'reason': 'Attempted change'})

