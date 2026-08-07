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
from odoo.exceptions import UserError


class TestEricWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestEricWorkflow, cls).setUpClass()

        # Create two test users (one manager, one officer)
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Estates Manager',
            'login': 'estates_manager',
            'email': 'manager@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('odoo_nhs_eric.group_nhs_eric_manager').id
            ])]
        })

        cls.officer_user = cls.env['res.users'].create({
            'name': 'Estates Officer',
            'login': 'estates_officer',
            'email': 'officer@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('odoo_nhs_eric.group_nhs_eric_officer').id
            ])]
        })

        cls.other_user = cls.env['res.users'].create({
            'name': 'Other Officer',
            'login': 'other_officer',
            'email': 'other@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('odoo_nhs_eric.group_nhs_eric_officer').id
            ])]
        })

        # Base dataset
        cls.dataset = cls.env['nhs.eric.dataset'].create({
            'name': 'ERIC Workflow Year',
            'year': '2026/27',
            'state': 'active',
        })

        # Two sections
        cls.section_a = cls.env['nhs.eric.section'].create({
            'name': 'Section A',
            'code': 'sec_a',
            'sequence': 10,
            'dataset_id': cls.dataset.id,
        })

        cls.section_b = cls.env['nhs.eric.section'].create({
            'name': 'Section B',
            'code': 'sec_b',
            'sequence': 20,
            'dataset_id': cls.dataset.id,
        })

        # Items in Section A
        cls.item_a1 = cls.env['nhs.eric.item.def'].create({
            'name': 'Required Item A1',
            'code': 'A1',
            'section_id': cls.section_a.id,
            'source_type': 'manual',
            'data_type': 'float',
            'required': True,
        })

        # Items in Section B
        cls.item_b1 = cls.env['nhs.eric.item.def'].create({
            'name': 'Required Item B1',
            'code': 'B1',
            'section_id': cls.section_b.id,
            'source_type': 'manual',
            'data_type': 'float',
            'required': True,
        })

        # Return creation
        cls.company = cls.env.user.company_id
        cls.ret = cls.env['nhs.eric.return'].create({
            'dataset_id': cls.dataset.id,
            'company_id': cls.company.id,
        })

    def test_01_section_lines_creation(self):
        """Test section lines are generated automatically on return creation."""
        self.assertEqual(len(self.ret.section_line_ids), 2)
        sections = self.ret.section_line_ids.mapped('section_id')
        self.assertIn(self.section_a, sections)
        self.assertIn(self.section_b, sections)

    def test_02_section_workflow_and_gaps(self):
        """Test submitting for review fails with gaps, succeeds when filled."""
        sec_line_a = self.ret.section_line_ids.filtered(lambda s: s.section_id == self.section_a)
        sec_line_a.write({
            'reviewer_id': self.manager_user.id,
        })

        # Submitting should fail because A1 is a gap
        with self.assertRaises(UserError):
            sec_line_a.action_submit_for_review()

        # Fill the value
        val_a1 = self.ret.value_ids.filtered(lambda v: v.item_def_id == self.item_a1)
        val_a1.write({'value_number': 123.45, 'status': 'populated'})

        # Now submission should succeed
        sec_line_a.action_submit_for_review()
        self.assertEqual(sec_line_a.state, 'ready_for_review')

    def test_03_ownership_editing_restrictions(self):
        """Test value modification is restricted to the assigned section owner."""
        sec_line_a = self.ret.section_line_ids.filtered(lambda s: s.section_id == self.section_a)
        sec_line_a.write({
            'owner_id': self.officer_user.id,
            'reviewer_id': self.manager_user.id,
        })

        val_a1 = self.ret.value_ids.filtered(lambda v: v.item_def_id == self.item_a1)

        # Other user tries to write -> should fail
        with self.assertRaises(UserError):
            val_a1.with_user(self.other_user).write({'value_number': 100.0})

        # Assigned owner writes -> should succeed
        val_a1.with_user(self.officer_user).write({'value_number': 150.0})
        self.assertEqual(val_a1.value_number, 150.0)

        # Estates manager writes -> should succeed
        val_a1.with_user(self.manager_user).write({'value_number': 200.0})
        self.assertEqual(val_a1.value_number, 200.0)

    def test_04_reviewer_sign_off_and_finalisation(self):
        """Test that only reviewer can sign off section, and finalisation requires all sections signed off."""
        sec_line_a = self.ret.section_line_ids.filtered(lambda s: s.section_id == self.section_a)
        sec_line_b = self.ret.section_line_ids.filtered(lambda s: s.section_id == self.section_b)

        sec_line_a.write({'reviewer_id': self.manager_user.id})
        sec_line_b.write({'reviewer_id': self.officer_user.id})

        # Populate both values to avoid validation blocks
        val_a1 = self.ret.value_ids.filtered(lambda v: v.item_def_id == self.item_a1)
        val_a1.write({'value_number': 10.0, 'status': 'populated'})
        val_b1 = self.ret.value_ids.filtered(lambda v: v.item_def_id == self.item_b1)
        val_b1.write({'value_number': 20.0, 'status': 'populated'})

        # Submit both sections
        sec_line_a.action_submit_for_review()
        sec_line_b.action_submit_for_review()

        # Non-reviewer (officer) tries to sign off section A -> should fail
        with self.assertRaises(UserError):
            sec_line_a.with_user(self.officer_user).action_sign_off()

        # Reviewer signs off section A -> should succeed
        sec_line_a.with_user(self.manager_user).action_sign_off()
        self.assertEqual(sec_line_a.state, 'signed_off')
        self.assertTrue(val_a1.signed_off)

        # Non-manager (officer) tries to finalise return -> should fail
        with self.assertRaises(UserError):
            self.ret.with_user(self.officer_user).action_finalise()

        # Manager tries to finalise but section B is not signed off -> should fail
        with self.assertRaises(UserError):
            self.ret.with_user(self.manager_user).action_finalise()

        # Reviewer signs off section B -> should succeed
        sec_line_b.with_user(self.officer_user).action_sign_off()
        self.assertEqual(sec_line_b.state, 'signed_off')
        self.assertTrue(val_b1.signed_off)

        # Validate the return first
        self.ret.with_user(self.manager_user).action_validate()
        self.assertEqual(self.ret.state, 'validated')

        # Now finalise return -> should succeed
        self.ret.with_user(self.manager_user).action_finalise()
        self.assertEqual(self.ret.state, 'finalised')

    def test_05_dashboard_metrics(self):
        """Test fetching of dashboard metrics returns all required fields and correct aggregation."""
        # Populate return data to test metrics calculations
        val_a1 = self.ret.value_ids.filtered(lambda v: v.item_def_id == self.item_a1)
        val_a1.write({'value_number': 100.0, 'status': 'populated'})
        
        val_b1 = self.ret.value_ids.filtered(lambda v: v.item_def_id == self.item_b1)
        val_b1.write({'value_number': 200.0, 'status': 'populated'})

        # Fetch dashboard metrics
        metrics = self.env['nhs.eric.return'].get_dashboard_metrics(return_id=self.ret.id)

        # Assert presence and structure of metrics keys
        self.assertTrue(metrics['has_data'])
        self.assertEqual(metrics['selected_return_id'], self.ret.id)
        self.assertEqual(metrics['year'], self.ret.year)
        self.assertIn('completeness_pct', metrics)
        self.assertIn('sections_outstanding', metrics)
        self.assertIn('validation_error_count', metrics)
        self.assertIn('gap_count', metrics)

        # Assert section progress mapping
        self.assertEqual(len(metrics['section_lines']), 2)
        sec_names = [s['name'] for s in metrics['section_lines']]
        self.assertIn('Section A', sec_names)
        self.assertIn('Section B', sec_names)

        # Assert source coverage counts
        self.assertIn('coverage', metrics)
        self.assertEqual(metrics['coverage']['total'], 2)
        self.assertEqual(metrics['coverage']['manual'], 2)
        self.assertEqual(metrics['coverage']['auto'], 0)

        # Assert YoY trend presence
        self.assertIn('trends', metrics)
