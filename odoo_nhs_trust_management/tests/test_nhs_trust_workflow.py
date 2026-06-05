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
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestNhsTrustWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestNhsTrustWorkflow, cls).setUpClass()
        cls.TrustType = cls.env['nhs.trust.type']
        cls.Region = cls.env['nhs.region']
        cls.Icb = cls.env['nhs.icb']
        cls.HealthBoard = cls.env['nhs.health.board']
        cls.Trust = cls.env['nhs.trust']
        cls.Wizard = cls.env['nhs.trust.state.change.wizard']

        # Get or create region for England
        cls.region_england = cls.Region.search([('health_system', '=', 'nhs_england')], limit=1)
        if not cls.region_england:
            cls.region_england = cls.Region.create({
                'name': 'Test Region England',
                'code': 'TRE',
                'health_system': 'nhs_england'
            })

        # Get or create ICB
        cls.icb = cls.Icb.search([('region_id', '=', cls.region_england.id)], limit=1)
        if not cls.icb:
            cls.icb = cls.Icb.create({
                'name': 'Test ICB England',
                'code': 'TIE',
                'region_id': cls.region_england.id
            })

        # Get or create trust type for England
        cls.type_england = cls.TrustType.search([('health_system', 'in', ('nhs_england', 'both'))], limit=1)
        if not cls.type_england:
            cls.type_england = cls.TrustType.create({
                'name': 'Test Type England',
                'health_system': 'nhs_england'
            })

        # Get or create region for Scotland
        cls.region_scotland = cls.Region.search([('health_system', '=', 'nhs_scotland')], limit=1)
        if not cls.region_scotland:
            cls.region_scotland = cls.Region.create({
                'name': 'Test Region Scotland',
                'code': 'TRS',
                'health_system': 'nhs_scotland'
            })

        # Get or create Health Board
        cls.health_board = cls.HealthBoard.search([('region_id', '=', cls.region_scotland.id)], limit=1)
        if not cls.health_board:
            cls.health_board = cls.HealthBoard.create({
                'name': 'Test Health Board Scotland',
                'code': 'TBS',
                'region_id': cls.region_scotland.id
            })

        # Get or create trust type for Scotland
        cls.type_scotland = cls.TrustType.search([('health_system', 'in', ('nhs_scotland', 'both'))], limit=1)
        if not cls.type_scotland:
            cls.type_scotland = cls.TrustType.create({
                'name': 'Test Type Scotland',
                'health_system': 'nhs_scotland'
            })

    def test_england_trust_special_measures(self):
        """Test that an England trust can transition to Special Measures."""
        england_trust = self.Trust.create({
            'name': 'Test England Trust 1',
            'ods_code': 'ENG01',
            'health_system': 'nhs_england',
            'trust_type_id': self.type_england.id,
            'region_id': self.region_england.id,
            'icb_id': self.icb.id,
        })
        # Draft -> Under Review
        self.Wizard.create({
            'trust_id': england_trust.id,
            'new_state': 'under_review',
            'reason': 'Transitioning to Under Review for test'
        }).action_confirm()
        self.assertEqual(england_trust.state, 'under_review')

        # Under Review -> Active
        self.Wizard.create({
            'trust_id': england_trust.id,
            'new_state': 'active',
            'reason': 'Transitioning to Active for test'
        }).action_confirm()
        self.assertEqual(england_trust.state, 'active')

        # Active -> Special Measures
        self.Wizard.create({
            'trust_id': england_trust.id,
            'new_state': 'special_measures',
            'reason': 'Escalating to Special Measures for test'
        }).action_confirm()
        self.assertEqual(england_trust.state, 'special_measures')

    def test_scotland_trust_cannot_special_measures(self):
        """Test that a Scotland trust cannot transition to Special Measures."""
        scotland_trust = self.Trust.create({
            'name': 'Test Scotland Trust 1',
            'ods_code': 'SCT01',
            'health_system': 'nhs_scotland',
            'trust_type_id': self.type_scotland.id,
            'region_id': self.region_scotland.id,
            'health_board_id': self.health_board.id,
        })

        # Draft -> Under Review
        self.Wizard.create({
            'trust_id': scotland_trust.id,
            'new_state': 'under_review',
            'reason': 'Transitioning to Under Review for test'
        }).action_confirm()
        self.assertEqual(scotland_trust.state, 'under_review')

        # Under Review -> Active
        self.Wizard.create({
            'trust_id': scotland_trust.id,
            'new_state': 'active',
            'reason': 'Transitioning to Active for test'
        }).action_confirm()
        self.assertEqual(scotland_trust.state, 'active')

        # Try to transition to Special Measures (should fail)
        with self.assertRaises(ValidationError):
            self.Wizard.create({
                'trust_id': scotland_trust.id,
                'new_state': 'special_measures',
                'reason': 'Escalating to Special Measures (should fail)'
            }).action_confirm()

        # Try writing state directly (should fail constraint check)
        with self.assertRaises(ValidationError):
            scotland_trust.with_context(approved_state_change=True).write({
                'state': 'special_measures'
            })
