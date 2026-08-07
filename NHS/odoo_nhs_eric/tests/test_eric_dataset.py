# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from odoo import fields

class TestEricDataset(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestEricDataset, cls).setUpClass()

        # Set up a base dataset for 2025/26
        cls.dataset_2025 = cls.env['nhs.eric.dataset'].create({
            'name': 'ERIC 2025/26',
            'year': '2025/26',
            'state': 'active',
        })

        cls.section_profile = cls.env['nhs.eric.section'].create({
            'name': 'Site Profile',
            'code': 'profile',
            'sequence': 10,
            'dataset_id': cls.dataset_2025.id,
        })

        cls.section_backlog = cls.env['nhs.eric.section'].create({
            'name': 'Backlog Maintenance',
            'code': 'backlog',
            'sequence': 20,
            'dataset_id': cls.dataset_2025.id,
        })

        # Base items
        cls.item_gia = cls.env['nhs.eric.item.def'].create({
            'name': 'Total GIA',
            'code': 'E_GIA',
            'section_id': cls.section_profile.id,
            'data_type': 'float',
            'unit': 'm²',
            'source_type': 'auto',
            'source_key': 'estate.total_gia',
            'required': True,
        })

        cls.item_backlog_total = cls.env['nhs.eric.item.def'].create({
            'name': 'Total Backlog Cost',
            'code': 'E_BACKLOG_TOT',
            'section_id': cls.section_backlog.id,
            'data_type': 'currency',
            'unit': '£',
            'source_type': 'manual',
            'required': False,
        })

        cls.item_compliance_pct = cls.env['nhs.eric.item.def'].create({
            'name': 'Overall Compliance %',
            'code': 'C_PCT',
            'section_id': cls.section_profile.id,
            'data_type': 'percent',
            'unit': '%',
            'source_type': 'auto',
            'source_key': 'compliance.pct',
            'required': True,
            'min_value': 0.0,
            'max_value': 100.0,
        })

        cls.item_allowed_check = cls.env['nhs.eric.item.def'].create({
            'name': 'Allowed Values Check',
            'code': 'A_VAL',
            'section_id': cls.section_profile.id,
            'data_type': 'text',
            'source_type': 'manual',
            'required': False,
            'allowed_values': 'Yes, No, Partial',
        })

        # Set default configs using the settings model or config parameter
        cls.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_validation_policy', 'block')
        cls.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_auto_populate_on_create', 'True')
        cls.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_carry_forward_manual', 'True')

    def test_01_clone_and_compare(self):
        """Test cloning a dataset and recalculating comparison changes (new, changed, removed)."""
        # Run new year wizard
        wizard = self.env['nhs.eric.new.year.wizard'].create({
            'dataset_id': self.dataset_2025.id,
            'new_name': 'ERIC 2026/27',
            'new_year': '2026/27',
            'copy_sections': True,
            'copy_items': True,
            'copy_mappings': True,
            'set_change_flags': True,
        })
        action = wizard.action_clone()
        new_dataset = self.env['nhs.eric.dataset'].browse(action['res_id'])

        # Verify new dataset basic fields
        self.assertEqual(new_dataset.prior_dataset_id, self.dataset_2025)
        self.assertEqual(new_dataset.year, '2026/27')

        # Get cloned items
        cloned_items = new_dataset.section_ids.mapped('item_def_ids')
        item_gia_clone = cloned_items.filtered(lambda i: i.code == 'E_GIA')
        item_backlog_clone = cloned_items.filtered(lambda i: i.code == 'E_BACKLOG_TOT')
        item_compliance_clone = cloned_items.filtered(lambda i: i.code == 'C_PCT')

        # Assert initial state (should be unchanged)
        self.assertEqual(item_gia_clone.change_flag, 'unchanged')

        # 1. Test "changed" detection: change name of GIA item
        item_gia_clone.name = 'Total Gross Internal Area'

        # 2. Test "new" detection: create a new item definition
        profile_section_clone = new_dataset.section_ids.filtered(lambda s: s.code == 'profile')
        item_new = self.env['nhs.eric.item.def'].create({
            'name': 'New Site Feature',
            'code': 'E_NEW',
            'section_id': profile_section_clone.id,
            'data_type': 'boolean',
            'source_type': 'manual',
        })

        # 3. Test "removed" detection: delete/unlink the backlog item
        item_backlog_clone.unlink()

        # Run comparison recalculation
        new_dataset.action_compare_with_prior()

        # Refresh items
        cloned_items = new_dataset.section_ids.mapped('item_def_ids')
        item_gia_clone = cloned_items.filtered(lambda i: i.code == 'E_GIA')
        item_new_clone = cloned_items.filtered(lambda i: i.code == 'E_NEW')
        item_backlog_recreated = cloned_items.filtered(lambda i: i.code == 'E_BACKLOG_TOT')

        # Assert correct change flags
        self.assertEqual(item_gia_clone.change_flag, 'changed')
        self.assertEqual(item_new_clone.change_flag, 'new')
        self.assertEqual(item_backlog_recreated.change_flag, 'removed')

        # Also verify that item counts on dataset and sections ignore removed items
        # There should be: E_GIA (changed), C_PCT (unchanged), A_VAL (unchanged), E_NEW (new) = 4 active items.
        # E_BACKLOG_TOT is removed, so it doesn't count.
        new_dataset._compute_item_count()
        self.assertEqual(new_dataset.item_count, 4)

    def test_02_return_creation_and_removed_filter(self):
        """Test that return creation initializes items and filters out removed items."""
        # Run clone wizard to create a 2026/27 dataset
        wizard = self.env['nhs.eric.new.year.wizard'].create({
            'dataset_id': self.dataset_2025.id,
            'new_name': 'ERIC 2026/27',
            'new_year': '2026/27',
            'copy_sections': True,
            'copy_items': True,
            'copy_mappings': True,
            'set_change_flags': True,
        })
        action = wizard.action_clone()
        new_dataset = self.env['nhs.eric.dataset'].browse(action['res_id'])

        # Delete backlog cost and recalculate to mark it removed
        cloned_items = new_dataset.section_ids.mapped('item_def_ids')
        item_backlog_clone = cloned_items.filtered(lambda i: i.code == 'E_BACKLOG_TOT')
        item_backlog_clone.unlink()
        new_dataset.action_compare_with_prior()

        # Create return for new year dataset
        ret = self.env['nhs.eric.return'].create({
            'dataset_id': new_dataset.id,
        })

        # Values should be initialized automatically for all non-removed items
        # Items should be E_GIA, C_PCT, A_VAL
        self.assertEqual(len(ret.value_ids), 3)
        self.assertNotIn('E_BACKLOG_TOT', ret.value_ids.mapped('item_code'))

    def test_03_validation_rules_and_policy(self):
        """Test item validations (required, min/max, allowed_values) and validation policy."""
        # Create a return (disable auto populate for clean validation test)
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_auto_populate_on_create', 'False')
        ret = self.env['nhs.eric.return'].create({
            'dataset_id': self.dataset_2025.id,
        }).with_context(bypass_sign_off_check=True)

        # Get the value records
        val_gia = ret.value_ids.filtered(lambda v: v.item_code == 'E_GIA')
        val_pct = ret.value_ids.filtered(lambda v: v.item_code == 'C_PCT')
        val_allowed = ret.value_ids.filtered(lambda v: v.item_code == 'A_VAL')

        # GIA and PCT are required but blank -> validation should fail
        with self.assertRaises(UserError):
            ret.action_validate()

        # 1. Fill required fields (valid values)
        val_gia.write({'value_number': 500.0, 'status': 'populated', 'is_overridden': True})
        val_pct.write({'value_number': 95.0, 'status': 'populated', 'is_overridden': True})
        ret.action_validate()
        self.assertEqual(ret.state, 'validated')

        # 2. Test range validation: set out-of-range PCT (max is 100)
        ret.write({'state': 'draft'})
        val_pct.write({'value_number': 150.0, 'is_overridden': True})
        with self.assertRaises(UserError):
            ret.action_validate()

        # Revert PCT to valid range
        val_pct.write({'value_number': 98.0, 'is_overridden': True})

        # 3. Test allowed values validation: set invalid allowed value
        val_allowed.write({'value_text': 'Maybe'})
        with self.assertRaises(UserError):
            ret.action_validate()

        # Set valid allowed value (should be case-insensitive: 'yes' -> matches 'Yes')
        val_allowed.write({'value_text': 'yes'})
        ret.action_validate()
        self.assertEqual(ret.state, 'validated')

        # 4. Test validation policy "warn"
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_validation_policy', 'warn')
        ret.write({'state': 'draft'})
        # Introduce validation error (out-of-range PCT)
        val_pct.write({'value_number': -10.0, 'is_overridden': True})
        
        # Validation should NOT raise error now and transition state to validated
        ret.action_validate()
        self.assertEqual(ret.state, 'validated')
        self.assertEqual(val_pct.status, 'invalid')

    def test_04_site_aggregation_and_locking(self):
        """Test site-specific value generation, auto-population resolver, and return locking."""
        # 1. Create site and building data
        site_a = self.env['nhs.estate.site'].create({
            'name': 'Test Site A',
            'code': 'TSITEA',
            'company_id': self.env.company.id,
            'land_area_ha': 2.5,
        })
        site_b = self.env['nhs.estate.site'].create({
            'name': 'Test Site B',
            'code': 'TSITEB',
            'company_id': self.env.company.id,
            'land_area_ha': 3.5,
        })

        building_a = self.env['nhs.estate.building'].create({
            'name': 'Test Building A',
            'code': 'TBLDGA',
            'site_id': site_a.id,
            'gia': 1000.0,
            'nia': 1000.0,
            'occupied_area': 800.0,
            'build_year': 1990,
            'company_id': self.env.company.id,
        })
        building_b = self.env['nhs.estate.building'].create({
            'name': 'Test Building B',
            'code': 'TBLDGB',
            'site_id': site_b.id,
            'gia': 2000.0,
            'nia': 2000.0,
            'occupied_area': 1500.0,
            'build_year': 2010,
            'company_id': self.env.company.id,
        })

        # Set tenures
        tenure_a = self.env['nhs.estate.tenure'].create({
            'building_id': building_a.id,
            'tenure_type': 'freehold',
        })
        building_a.write({'tenure_id': tenure_a.id})

        tenure_b = self.env['nhs.estate.tenure'].create({
            'building_id': building_b.id,
            'tenure_type': 'leasehold',
        })
        building_b.write({'tenure_id': tenure_b.id})

        # 2. Add some site-level item definitions
        item_site_gia = self.env['nhs.eric.item.def'].create({
            'name': 'Site GIA',
            'code': 'S_GIA',
            'section_id': self.section_profile.id,
            'data_type': 'float',
            'reporting_level': 'site',
            'source_type': 'auto',
            'source_key': 'estate.total_gia',
            'required': True,
        })

        item_site_land = self.env['nhs.eric.item.def'].create({
            'name': 'Site Land Area',
            'code': 'S_LAND',
            'section_id': self.section_profile.id,
            'data_type': 'float',
            'reporting_level': 'site',
            'source_type': 'auto',
            'source_key': 'estate.land_area',
            'required': True,
        })

        item_site_tenure_owned = self.env['nhs.eric.item.def'].create({
            'name': 'Site Tenure Owned %',
            'code': 'S_TEN_OWN',
            'section_id': self.section_profile.id,
            'data_type': 'percent',
            'reporting_level': 'site',
            'source_type': 'auto',
            'source_key': 'estate.tenure.owned',
            'required': False,
        })

        # Enable auto-populate config
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_auto_populate_on_create', 'True')

        # 3. Create return
        ret = self.env['nhs.eric.return'].create({
            'dataset_id': self.dataset_2025.id,
        }).with_context(bypass_sign_off_check=True)
        ret.action_populate()

        # Verify that value records were created for both Trust and Site level items
        vals_site_gia = ret.value_ids.filtered(lambda v: v.item_def_id == item_site_gia)
        self.assertTrue(len(vals_site_gia) >= 2, "Should have created site-level values for Site GIA")
        
        val_gia_a = vals_site_gia.filtered(lambda v: v.site_id == site_a)
        val_gia_b = vals_site_gia.filtered(lambda v: v.site_id == site_b)
        self.assertTrue(val_gia_a, "Should have value record for Site A")
        self.assertTrue(val_gia_b, "Should have value record for Site B")

        # 4. Verify auto-populated values on the return
        self.assertEqual(val_gia_a.value_number, 1000.0)
        self.assertEqual(val_gia_b.value_number, 2000.0)

        val_land_a = ret.value_ids.filtered(lambda v: v.item_def_id == item_site_land and v.site_id == site_a)
        val_land_b = ret.value_ids.filtered(lambda v: v.item_def_id == item_site_land and v.site_id == site_b)
        self.assertEqual(val_land_a.value_number, 2.5)
        self.assertEqual(val_land_b.value_number, 3.5)

        val_ten_a = ret.value_ids.filtered(lambda v: v.item_def_id == item_site_tenure_owned and v.site_id == site_a)
        val_ten_b = ret.value_ids.filtered(lambda v: v.item_def_id == item_site_tenure_owned and v.site_id == site_b)
        self.assertEqual(val_ten_a.value_number, 100.0)
        self.assertEqual(val_ten_b.value_number, 0.0)

        # 5. Verify return locking behavior
        # Fill the required manual/auto fields or mock/bypass validation
        for val in ret.value_ids:
            if val.item_def_id.required and not val._has_value():
                val.write({'value_number': 1.0, 'status': 'populated', 'is_overridden': True})

        ret.action_validate()
        ret.with_context(bypass_sign_off_check=True).action_finalise()
        self.assertEqual(ret.state, 'finalised')

        # Attempt to modify a value record -> should raise UserError
        with self.assertRaises(UserError):
            val_gia_a.write({'value_number': 999.0})

        # Attempt to unlink a value record -> should raise UserError
        with self.assertRaises(UserError):
            val_gia_a.unlink()

        # Attempt to modify the return record -> should raise UserError
        with self.assertRaises(UserError):
            ret.write({'dataset_id': self.dataset_2025.id})

    def test_05_eric_extended_features(self):
        """Test the extended ERIC auto-population resolver keys and detailed traceability logs."""
        # 1. Create site and building data with specific age and condition grades
        site = self.env['nhs.estate.site'].create({
            'name': 'Test Site C',
            'code': 'TSITEC',
            'company_id': self.env.company.id,
            'land_area_ha': 5.0,
        })

        # Building 1: pre-1980, Condition A, GIA 1000.0
        building_1 = self.env['nhs.estate.building'].create({
            'name': 'Test Building 1',
            'code': 'TBLDG1',
            'site_id': site.id,
            'gia': 1000.0,
            'nia': 1000.0,
            'build_year': 1970,
            'company_id': self.env.company.id,
        })
        survey_1 = self.env['nhs.estate.condition'].create({
            'name': 'Survey 1',
            'building_id': building_1.id,
            'facet_physical': 'A',
            'facet_statutory': 'A',
            'facet_functional': 'A',
            'facet_utilisation': 'A',
            'facet_quality': 'A',
            'facet_energy': 'A',
            'survey_date': fields.Date.today(),
        })
        building_1._compute_latest_condition_grade()

        # Building 2: 1980-2000, Condition B, GIA 2000.0
        building_2 = self.env['nhs.estate.building'].create({
            'name': 'Test Building 2',
            'code': 'TBLDG2',
            'site_id': site.id,
            'gia': 2000.0,
            'nia': 2000.0,
            'build_year': 1990,
            'company_id': self.env.company.id,
        })
        survey_2 = self.env['nhs.estate.condition'].create({
            'name': 'Survey 2',
            'building_id': building_2.id,
            'facet_physical': 'B',
            'facet_statutory': 'B',
            'facet_functional': 'B',
            'facet_utilisation': 'B',
            'facet_quality': 'B',
            'facet_energy': 'B',
            'survey_date': fields.Date.today(),
        })
        building_2._compute_latest_condition_grade()

        # Building 3: post-2000, Condition C, GIA 3000.0
        building_3 = self.env['nhs.estate.building'].create({
            'name': 'Test Building 3',
            'code': 'TBLDG3',
            'site_id': site.id,
            'gia': 3000.0,
            'nia': 3000.0,
            'build_year': 2015,
            'company_id': self.env.company.id,
        })
        survey_3 = self.env['nhs.estate.condition'].create({
            'name': 'Survey 3',
            'building_id': building_3.id,
            'facet_physical': 'C',
            'facet_statutory': 'C',
            'facet_functional': 'C',
            'facet_utilisation': 'C',
            'facet_quality': 'C',
            'facet_energy': 'C',
            'survey_date': fields.Date.today(),
        })
        building_3._compute_latest_condition_grade()

        # 2. Setup compliance items
        discipline_gas = self.env['nhs.compliance.discipline'].create({
            'name': 'Gas Safety Extra',
            'code': 'GASEXTRA',
        })
        compliance_type = self.env['nhs.compliance.type'].create({
            'name': 'Gas Safety Item 1',
            'discipline_id': discipline_gas.id,
        })
        
        item_compliance = self.env['nhs.compliance.item'].create({
            'name': 'Gas Safety Item 1',
            'discipline_id': discipline_gas.id,
            'compliance_type_id': compliance_type.id,
            'active': True,
            'company_id': self.env.company.id,
            'site_id': site.id,
        })
        self.env['nhs.compliance.test'].create({
            'item_id': item_compliance.id,
            'test_date': fields.Date.today(),
            'outcome': 'pass',
        })

        # 3. Create items to test auto-population
        item_age_pre_1980 = self.env['nhs.eric.item.def'].create({
            'name': 'Pre 1980 Buildings',
            'code': 'E_AGE_PRE_1980',
            'section_id': self.section_profile.id,
            'data_type': 'float',
            'reporting_level': 'site',
            'source_type': 'auto',
            'source_key': 'estate.age_bands.pre_1980',
        })
        item_age_pct_pre_1980 = self.env['nhs.eric.item.def'].create({
            'name': 'Pre 1980 Buildings %',
            'code': 'E_AGE_PCT_PRE_1980',
            'section_id': self.section_profile.id,
            'data_type': 'percent',
            'reporting_level': 'site',
            'source_type': 'auto',
            'source_key': 'estate.age_bands_pct.pre_1980',
        })
        item_cond_pct_a = self.env['nhs.eric.item.def'].create({
            'name': 'Condition A %',
            'code': 'E_COND_PCT_A',
            'section_id': self.section_profile.id,
            'data_type': 'percent',
            'reporting_level': 'site',
            'source_type': 'auto',
            'source_key': 'estate.condition.A',
        })
        item_cond_count_a = self.env['nhs.eric.item.def'].create({
            'name': 'Condition A Count',
            'code': 'E_COND_COUNT_A',
            'section_id': self.section_profile.id,
            'data_type': 'float',
            'reporting_level': 'site',
            'source_type': 'auto',
            'source_key': 'estate.condition.count.A',
        })
        item_comp_gas = self.env['nhs.eric.item.def'].create({
            'name': 'Gas Compliance %',
            'code': 'C_GAS',
            'section_id': self.section_profile.id,
            'data_type': 'percent',
            'reporting_level': 'site',
            'source_type': 'auto',
            'source_key': 'compliance.GASEXTRA',
        })

        # 4. Trigger auto-population
        ret = self.env['nhs.eric.return'].create({
            'dataset_id': self.dataset_2025.id,
        })

        # Let's trigger manual population wizard to make sure it resolves properly
        wizard = self.env['nhs.eric.populate.wizard'].create({
            'return_id': ret.id,
        })
        wizard.action_populate()

        # 5. Assert values resolved correctly
        val_age_pre_1980 = ret.value_ids.filtered(lambda v: v.item_def_id == item_age_pre_1980 and v.site_id == site)
        self.assertEqual(val_age_pre_1980.value_number, 1.0)

        val_age_pct_pre_1980 = ret.value_ids.filtered(lambda v: v.item_def_id == item_age_pct_pre_1980 and v.site_id == site)
        self.assertAlmostEqual(val_age_pct_pre_1980.value_number, 1000.0 / 6000.0 * 100.0, places=2)

        val_cond_pct_a = ret.value_ids.filtered(lambda v: v.item_def_id == item_cond_pct_a and v.site_id == site)
        self.assertAlmostEqual(val_cond_pct_a.value_number, 1000.0 / 6000.0 * 100.0, places=2)

        val_cond_count_a = ret.value_ids.filtered(lambda v: v.item_def_id == item_cond_count_a and v.site_id == site)
        self.assertEqual(val_cond_count_a.value_number, 1.0)

        val_comp_gas = ret.value_ids.filtered(lambda v: v.item_def_id == item_comp_gas and v.site_id == site)
        self.assertEqual(val_comp_gas.value_number, 100.0)

        # 6. Assert detailed traceability note is correctly populated
        self.assertIn("Test Building 1", val_age_pre_1980.source_note)
        self.assertIn("Test Building 1", val_age_pct_pre_1980.source_note)
        self.assertIn("Test Building 1", val_cond_pct_a.source_note)
        self.assertIn("Test Building 1", val_cond_count_a.source_note)
        self.assertIn("Gas Safety Item 1", val_comp_gas.source_note)

    def test_06_manual_entry_and_overrides(self):
        """Test manual entry, auto-override triggers, validation constraints, bulk manual entry actions, and carry-forward with attachments."""
        # 1. Create a return for 2025/26
        ret = self.env['nhs.eric.return'].create({
            'dataset_id': self.dataset_2025.id,
        })
        ret.action_populate()

        # Find a manual value and an auto value
        val_manual = ret.value_ids.filtered(lambda v: v.item_def_id == self.item_allowed_check)
        val_auto = ret.value_ids.filtered(lambda v: v.item_def_id == self.item_gia)

        self.assertFalse(val_manual.is_overridden)
        self.assertFalse(val_auto.is_overridden)

        # 2. Add an attachment to the manual value
        attachment = self.env['ir.attachment'].create({
            'name': 'evidence.pdf',
            'type': 'binary',
            'datas': b'dGVzdA==',
            'res_model': 'nhs.eric.value',
            'res_id': val_manual.id,
        })
        val_manual.write({
            'value_text': 'Yes',
            'attachment_ids': [(4, attachment.id)]
        })
        self.assertEqual(val_manual.value_text, 'Yes')
        self.assertIn(attachment, val_manual.attachment_ids)

        # 3. Modify auto value number, checking that is_overridden is set to True automatically
        # and has a default override_reason
        val_auto.write({
            'value_number': 1500.0
        })
        self.assertTrue(val_auto.is_overridden)
        self.assertEqual(val_auto.override_reason, 'Manual override applied')

        # 4. Enforce that clearing the override reason raises a ValidationError
        with self.assertRaises(ValidationError):
            val_auto.write({
                'override_reason': False
            })

        # 5. Check bulk manual action returns correct parameters
        action = ret.action_bulk_manual_entry()
        self.assertEqual(action['res_model'], 'nhs.eric.value')
        self.assertEqual(action['context']['default_return_id'], ret.id)
        self.assertEqual(action['context']['search_default_manual_only'], 1)

        # 6. Check carry-forward to next year's return
        # Setup next year dataset
        dataset_2026 = self.env['nhs.eric.dataset'].create({
            'name': 'ERIC 2026/27',
            'year': '2026/27',
            'state': 'active',
            'prior_dataset_id': self.dataset_2025.id,
        })
        section_profile_26 = self.env['nhs.eric.section'].create({
            'name': 'Site Profile 26',
            'code': 'profile',
            'sequence': 10,
            'dataset_id': dataset_2026.id,
        })
        # Create identical item definitions in 2026
        item_allowed_check_26 = self.env['nhs.eric.item.def'].create({
            'name': 'Allowed Values Check',
            'code': 'A_VAL',
            'section_id': section_profile_26.id,
            'data_type': 'text',
            'source_type': 'manual',
            'required': False,
            'allowed_values': 'Yes, No, Partial',
        })

        ret_2026 = self.env['nhs.eric.return'].create({
            'dataset_id': dataset_2026.id,
            'prior_return_id': ret.id,
        })
        # Action carry forward
        ret_2026.action_carry_forward()

        # Check manual value is copied
        val_manual_26 = ret_2026.value_ids.filtered(lambda v: v.item_def_id == item_allowed_check_26)
        self.assertEqual(val_manual_26.value_text, 'Yes')
        
        # Check attachment is carried forward (copied as a new attachment)
        self.assertTrue(val_manual_26.attachment_ids)
        self.assertNotEqual(val_manual_26.attachment_ids[0].id, attachment.id)
        self.assertEqual(val_manual_26.attachment_ids[0].name, 'evidence.pdf')

    def test_07_validation_gap_and_anomalies(self):
        """Test required gaps, cross-field checks, anomaly detection, and policy blocks."""
        # 1. Setup prior dataset and return
        prior_dataset = self.env['nhs.eric.dataset'].create({
            'name': 'Validation prior dataset',
            'year': '2028/29',
        })
        prior_section = self.env['nhs.eric.section'].create({
            'name': 'Validation Testing Section',
            'code': 'val_test',
            'sequence': 99,
            'dataset_id': prior_dataset.id,
        })
        item_prior_gia = self.env['nhs.eric.item.def'].create({
            'name': 'GIA',
            'code': 'E_GIA',
            'section_id': prior_section.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': True,
        })
        
        prior_ret = self.env['nhs.eric.return'].create({
            'dataset_id': prior_dataset.id,
            'year': '2028/29',
        })
        # Set value in prior return
        val_prior_gia = prior_ret.value_ids.filtered(lambda v: v.item_def_id == item_prior_gia)
        val_prior_gia.write({
            'value_number': 100.0,
            'status': 'populated'
        })

        # 2. Setup current dataset and return
        dataset = self.env['nhs.eric.dataset'].create({
            'name': 'Validation current dataset',
            'year': '2029/30',
        })
        section = self.env['nhs.eric.section'].create({
            'name': 'Validation Testing Section',
            'code': 'val_test',
            'sequence': 99,
            'dataset_id': dataset.id,
        })
        
        item_gia = self.env['nhs.eric.item.def'].create({
            'name': 'GIA',
            'code': 'E_GIA',
            'section_id': section.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': True,
        })
        
        item_occupied = self.env['nhs.eric.item.def'].create({
            'name': 'Occupied Area',
            'code': 'E_OCCUPIED_AREA',
            'section_id': section.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': True,
        })

        item_owned = self.env['nhs.eric.item.def'].create({
            'name': 'Tenure Owned',
            'code': 'E_TENURE_OWNED',
            'section_id': section.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': False,
        })

        item_leased = self.env['nhs.eric.item.def'].create({
            'name': 'Tenure Leased',
            'code': 'E_TENURE_LEASED',
            'section_id': section.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': False,
        })

        item_backlog_total = self.env['nhs.eric.item.def'].create({
            'name': 'Total Backlog',
            'code': 'E_BACKLOG_TOTAL',
            'section_id': section.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': False,
        })

        item_backlog_high = self.env['nhs.eric.item.def'].create({
            'name': 'Backlog High',
            'code': 'E_BACKLOG_HIGH',
            'section_id': section.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': False,
        })

        # Current Return Setup
        current_ret = self.env['nhs.eric.return'].create({
            'dataset_id': dataset.id,
            'prior_return_id': prior_ret.id,
            'year': '2029/30',
        }).with_context(bypass_sign_off_check=True)

        # Verify default state and gaps
        val_gia = current_ret.value_ids.filtered(lambda v: v.item_def_id == item_gia)
        val_occ = current_ret.value_ids.filtered(lambda v: v.item_def_id == item_occupied)
        val_owned = current_ret.value_ids.filtered(lambda v: v.item_def_id == item_owned)
        val_leased = current_ret.value_ids.filtered(lambda v: v.item_def_id == item_leased)
        val_backlog_tot = current_ret.value_ids.filtered(lambda v: v.item_def_id == item_backlog_total)
        val_backlog_high = current_ret.value_ids.filtered(lambda v: v.item_def_id == item_backlog_high)

        # Set values to trigger cross-field check failures: Occupied Area (120) > GIA (100)
        val_gia.write({'value_number': 100.0, 'status': 'populated'})
        val_occ.write({'value_number': 120.0, 'status': 'populated'})
        # Also tenure parts do not sum to GIA: 40 + 50 = 90 != 100
        val_owned.write({'value_number': 40.0, 'status': 'populated'})
        val_leased.write({'value_number': 50.0, 'status': 'populated'})
        # Also backlog components: total is 1000 but high is 800 (low/mod/sig are 0) -> mismatch!
        val_backlog_tot.write({'value_number': 1000.0, 'status': 'populated'})
        val_backlog_high.write({'value_number': 800.0, 'status': 'populated'})

        # Run validation with policy set to warn first
        # It should succeed without raising UserError, but mark items as invalid
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_validation_policy', 'warn')
        current_ret.action_validate()

        # Check they are marked as invalid
        self.assertEqual(val_occ.status, 'invalid')
        self.assertEqual(val_owned.status, 'invalid')
        self.assertEqual(val_leased.status, 'invalid')
        self.assertEqual(val_gia.status, 'invalid')
        self.assertEqual(val_backlog_tot.status, 'invalid')
        self.assertEqual(val_backlog_high.status, 'invalid')

        # Set policy to block, running validation again should raise UserError
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_validation_policy', 'block')
        with self.assertRaises(UserError):
            current_ret.action_validate()

        # Now fix the cross-field error: Occupied = 80 <= GIA = 100, parts = 40 + 60 = 100, backlog high = 1000 = backlog total
        val_occ.write({'value_number': 80.0, 'status': 'populated'})
        val_owned.write({'value_number': 40.0, 'status': 'populated'})
        val_leased.write({'value_number': 60.0, 'status': 'populated'})
        val_backlog_high.write({'value_number': 1000.0, 'status': 'populated'})

        # Also test anomaly: GIA goes from 100 (prior) to 160 (current) -> 60% change
        val_gia.write({'value_number': 160.0, 'status': 'populated'})
        # And correct the parts sum: 40 + 120 = 160
        val_leased.write({'value_number': 120.0, 'status': 'populated'})

        # Validation should succeed now because cross-field constraints are satisfied
        current_ret.action_validate()
        self.assertEqual(val_gia.status, 'populated')
        self.assertEqual(val_occ.status, 'populated')
        self.assertEqual(val_owned.status, 'populated')
        self.assertEqual(val_leased.status, 'populated')
        self.assertEqual(val_backlog_tot.status, 'populated')
        self.assertEqual(val_backlog_high.status, 'populated')

        # Verify anomaly flagging
        self.assertTrue(val_gia.is_anomaly)
        self.assertIn('differs by 60.0%', val_gia.anomaly_reason)
        # Occupied did not change from prior (prior did not have occupied), so not an anomaly
        self.assertFalse(val_occ.is_anomaly)

        # Test policy blocks finalisation
        # Reset state to draft so action_finalise runs validation again
        current_ret.write({'state': 'draft'})
        # Make one of them invalid again (occupied > GIA)
        val_occ.write({'value_number': 200.0, 'status': 'populated'})
        
        # Policy is block, so action_finalise must fail
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_validation_policy', 'block')
        with self.assertRaises(UserError):
            current_ret.with_context(bypass_sign_off_check=True).action_finalise()

        # Policy set to warn, action_finalise must pass
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_validation_policy', 'warn')
        current_ret.with_context(bypass_sign_off_check=True).action_finalise()
        self.assertEqual(current_ret.state, 'finalised')

    def test_08_year_on_year_comparison_and_trends(self):
        """Test Year-on-Year comparison lines and trend metric reporting."""
        # 1. Setup prior dataset and return
        prior_ds = self.env['nhs.eric.dataset'].create({
            'name': 'ERIC 2022/23',
            'year': '2022/23',
            'state': 'active',
        })
        prior_sec = self.env['nhs.eric.section'].create({
            'name': 'Site Profile',
            'code': 'profile',
            'sequence': 10,
            'dataset_id': prior_ds.id,
        })
        item_prior_gia = self.env['nhs.eric.item.def'].create({
            'name': 'Total GIA',
            'code': 'E_GIA',
            'section_id': prior_sec.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': True,
        })
        item_prior_backlog = self.env['nhs.eric.item.def'].create({
            'name': 'Total Backlog Cost',
            'code': 'E_BACKLOG_TOT',
            'section_id': prior_sec.id,
            'data_type': 'currency',
            'source_type': 'manual',
            'required': False,
        })
        item_prior_comp = self.env['nhs.eric.item.def'].create({
            'name': 'Overall Compliance %',
            'code': 'C_PCT',
            'section_id': prior_sec.id,
            'data_type': 'percent',
            'source_type': 'manual',
            'required': False,
        })

        prior_ret = self.env['nhs.eric.return'].create({
            'dataset_id': prior_ds.id,
            'state': 'draft',
        })
        
        val_prior_gia = prior_ret.value_ids.filtered(lambda v: v.item_def_id.id == item_prior_gia.id)
        val_prior_gia.write({
            'value_number': 100.0,
            'status': 'populated',
        })
        val_prior_backlog = prior_ret.value_ids.filtered(lambda v: v.item_def_id.id == item_prior_backlog.id)
        val_prior_backlog.write({
            'value_number': 5000.0,
            'status': 'populated',
        })
        val_prior_comp = prior_ret.value_ids.filtered(lambda v: v.item_def_id.id == item_prior_comp.id)
        val_prior_comp.write({
            'value_number': 80.0,
            'status': 'populated',
        })

        # 2. Setup current dataset and return
        curr_ds = self.env['nhs.eric.dataset'].create({
            'name': 'ERIC 2023/24',
            'year': '2023/24',
            'state': 'active',
        })
        curr_sec = self.env['nhs.eric.section'].create({
            'name': 'Site Profile',
            'code': 'profile',
            'sequence': 10,
            'dataset_id': curr_ds.id,
        })
        item_curr_gia = self.env['nhs.eric.item.def'].create({
            'name': 'Total GIA',
            'code': 'E_GIA',
            'section_id': curr_sec.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': True,
        })
        item_curr_backlog = self.env['nhs.eric.item.def'].create({
            'name': 'Total Backlog Cost',
            'code': 'E_BACKLOG_TOT',
            'section_id': curr_sec.id,
            'data_type': 'currency',
            'source_type': 'manual',
            'required': False,
        })
        item_curr_comp = self.env['nhs.eric.item.def'].create({
            'name': 'Overall Compliance %',
            'code': 'C_PCT',
            'section_id': curr_sec.id,
            'data_type': 'percent',
            'source_type': 'manual',
            'required': False,
        })

        curr_ret = self.env['nhs.eric.return'].create({
            'dataset_id': curr_ds.id,
            'prior_return_id': prior_ret.id,
            'state': 'draft',
        })
        
        val_curr_gia = curr_ret.value_ids.filtered(lambda v: v.item_def_id.id == item_curr_gia.id)
        val_curr_gia.write({
            'value_number': 120.0,
            'status': 'populated',
        })
        val_curr_backlog = curr_ret.value_ids.filtered(lambda v: v.item_def_id.id == item_curr_backlog.id)
        val_curr_backlog.write({
            'value_number': 8000.0,  # 60% change (>50% anomaly threshold)
            'status': 'populated',
        })
        val_curr_comp = curr_ret.value_ids.filtered(lambda v: v.item_def_id.id == item_curr_comp.id)
        val_curr_comp.write({
            'value_number': 90.0,
            'status': 'populated',
        })

        # Set anomaly threshold parameter to 50%
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.anomaly_threshold_pct', '50.0')

        # Trigger YoY lines generation
        curr_ret.invalidate_recordset()
        comp_lines = curr_ret.comparison_line_ids
        self.assertEqual(len(comp_lines), 3)

        gia_line = comp_lines.filtered(lambda l: l.item_code == 'E_GIA')
        backlog_line = comp_lines.filtered(lambda l: l.item_code == 'E_BACKLOG_TOT')
        comp_line = comp_lines.filtered(lambda l: l.item_code == 'C_PCT')

        # Verify GIA comparison (20% increase)
        self.assertAlmostEqual(gia_line.percentage_change, 20.0)
        self.assertEqual(gia_line.change_flag, 'up')
        self.assertEqual(gia_line.highlight_color, 'green')

        # Verify Backlog comparison (60% increase, exceeds threshold -> orange)
        self.assertAlmostEqual(backlog_line.percentage_change, 60.0)
        self.assertEqual(backlog_line.change_flag, 'up')
        self.assertEqual(backlog_line.highlight_color, 'orange')

        # 3. Finalise and check trends
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_validation_policy', 'warn')
        
        # Finalise prior return
        prior_ret.with_context(bypass_sign_off_check=True).action_finalise()
        self.assertEqual(prior_ret.state, 'finalised')

        # Finalise current return
        curr_ret.with_context(bypass_sign_off_check=True).action_finalise()
        self.assertEqual(curr_ret.state, 'finalised')

        # Verify trend records were created
        prior_trend = self.env['nhs.eric.trend.metric'].search([
            ('company_id', '=', prior_ret.company_id.id),
            ('year', '=', '2022/23')
        ])
        curr_trend = self.env['nhs.eric.trend.metric'].search([
            ('company_id', '=', curr_ret.company_id.id),
            ('year', '=', '2023/24')
        ])

        self.assertTrue(prior_trend)
        self.assertTrue(curr_trend)

        # Assert prior values
        self.assertEqual(prior_trend.gia, 100.0)
        self.assertEqual(prior_trend.backlog, 5000.0)
        self.assertEqual(prior_trend.compliance_pct, 80.0)
        self.assertAlmostEqual(prior_trend.cost_per_m2, 50.0)  # 5000 / 100

        # Assert current values
        self.assertEqual(curr_trend.gia, 120.0)
        self.assertEqual(curr_trend.backlog, 8000.0)
        self.assertEqual(curr_trend.compliance_pct, 90.0)
        self.assertAlmostEqual(curr_trend.cost_per_m2, 66.666666667)  # 8000 / 120

    def test_09_computed_and_data_types(self):
        """Test computed items, cascading calculations, read-only constraints, and integer validation."""
        # 1. Create dataset with manual, computed, and integer items
        ds = self.env['nhs.eric.dataset'].create({
            'name': 'Test Computed & Types',
            'year': '2029/30',
            'state': 'active',
        })
        sec = self.env['nhs.eric.section'].create({
            'name': 'Test Section',
            'code': 'test_sec',
            'sequence': 10,
            'dataset_id': ds.id,
        })
        
        # Manual numeric float item
        item_float = self.env['nhs.eric.item.def'].create({
            'name': 'Float Item',
            'code': 'F_VAL',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'manual',
            'required': True,
        })
        
        # Manual integer item
        item_int = self.env['nhs.eric.item.def'].create({
            'name': 'Integer Item',
            'code': 'I_VAL',
            'section_id': sec.id,
            'data_type': 'integer',
            'source_type': 'manual',
            'required': True,
        })
        
        # Computed item: F_VAL + I_VAL
        item_comp1 = self.env['nhs.eric.item.def'].create({
            'name': 'Computed Item 1',
            'code': 'COMP1',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'computed',
            'computation_operator': 'sum',
            'computed_input_ids': [(6, 0, [item_float.id, item_int.id])],
            'required': True,
        })
        
        # Cascaded computed item: COMP1 / I_VAL
        item_comp2 = self.env['nhs.eric.item.def'].create({
            'name': 'Computed Item 2',
            'code': 'COMP2',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'computed',
            'computation_operator': 'div',
            'computed_input_ids': [(6, 0, [item_comp1.id, item_int.id])],
            'required': True,
        })
        
        # Create return
        ret = self.env['nhs.eric.return'].create({
            'dataset_id': ds.id,
            'state': 'draft',
        })
        
        val_float = ret.value_ids.filtered(lambda v: v.item_def_id == item_float)
        val_int = ret.value_ids.filtered(lambda v: v.item_def_id == item_int)
        val_comp1 = ret.value_ids.filtered(lambda v: v.item_def_id == item_comp1)
        val_comp2 = ret.value_ids.filtered(lambda v: v.item_def_id == item_comp2)
        
        # Initial values (all gaps/0.0)
        self.assertEqual(val_comp1.value_number, 0.0)
        self.assertEqual(val_comp2.value_number, 0.0)
        
        # 2. Write to manual float item: should calculate COMP1 and COMP2
        val_float.write({'value_number': 10.0})
        self.assertEqual(val_comp1.value_number, 10.0)  # 10.0 + 0.0
        self.assertEqual(val_comp2.value_number, 0.0)   # 10.0 / 0.0 -> 0.0
        
        # 3. Write to manual integer item: should cascade recalculate
        val_int.write({'value_number': 5.0})
        self.assertEqual(val_comp1.value_number, 15.0)  # 10.0 + 5.0
        self.assertEqual(val_comp2.value_number, 3.0)   # 15.0 / 5.0
        
        # 4. Enforce read-only constraint on computed items
        with self.assertRaises(UserError):
            val_comp1.write({'value_number': 100.0})
            
        # 5. Enforce integer validation (non-integer should be marked as invalid)
        # Verify valid integer first
        val_int.write({'value_number': 5.0})
        self.assertEqual(val_int.status, 'populated')
        
        # Write decimal to integer item
        val_int.write({'value_number': 5.5})
        self.assertEqual(val_int.status, 'invalid')
        
        # Verify validate return detects invalid integer
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_validation_policy', 'block')
        with self.assertRaises(UserError):
            ret.action_validate()

    def test_10_selection_source_key(self):
        """Test selection_source_key computed and inverse behavior."""
        ds = self.env['nhs.eric.dataset'].create({
            'name': 'Test Selection Source Key',
            'year': '2030/31',
            'state': 'active',
        })
        sec = self.env['nhs.eric.section'].create({
            'name': 'Test Section',
            'code': 'test_sec',
            'sequence': 10,
            'dataset_id': ds.id,
        })

        # 1. Create with source_type auto and valid resolver key
        item_auto = self.env['nhs.eric.item.def'].create({
            'name': 'Auto Item',
            'code': 'A_VAL',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'auto',
            'source_key': 'estate.total_gia',
        })
        # Compute should set selection_source_key
        self.assertEqual(item_auto.selection_source_key, 'estate.total_gia')

        # 2. Write to selection_source_key: should update source_key via inverse
        item_auto.write({'selection_source_key': 'estate.site_count'})
        self.assertEqual(item_auto.source_key, 'estate.site_count')

        # 3. Create with source_type computed and custom formula
        item_computed = self.env['nhs.eric.item.def'].create({
            'name': 'Computed Item',
            'code': 'C_VAL',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'computed',
            'source_key': 'A_VAL * 2',
        })
        # Compute should set selection_source_key to False because it's computed/not in resolver keys
        self.assertFalse(item_computed.selection_source_key)

        # 4. Create with source_type auto and invalid key
        item_invalid = self.env['nhs.eric.item.def'].create({
            'name': 'Invalid Key Item',
            'code': 'I_VAL_KEY',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'auto',
            'source_key': 'invalid.key.name',
        })
        # Compute should set selection_source_key to False because it's not a valid resolver key
        self.assertFalse(item_invalid.selection_source_key)

    def test_11_site_level_filtering(self):
        """Test site-specific filtering logic for site-level items."""
        # Create sites
        site_a = self.env['nhs.estate.site'].create({
            'name': 'Site A',
            'code': 'SITEA',
            'company_id': self.env.company.id,
            'land_area_ha': 2.0,
        })
        site_b = self.env['nhs.estate.site'].create({
            'name': 'Site B',
            'code': 'SITEB',
            'company_id': self.env.company.id,
            'land_area_ha': 5.0,
        })

        ds = self.env['nhs.eric.dataset'].create({
            'name': 'Test Site Level Filtering',
            'year': '2031/32',
            'state': 'active',
        })
        sec = self.env['nhs.eric.section'].create({
            'name': 'Test Section',
            'code': 'test_sec',
            'sequence': 10,
            'dataset_id': ds.id,
        })

        # Create item bound to site_a specifically
        item_site_a = self.env['nhs.eric.item.def'].create({
            'name': 'Site A Land',
            'code': 'S_LAND_A',
            'section_id': sec.id,
            'data_type': 'float',
            'reporting_level': 'site',
            'site_id': site_a.id,
            'source_type': 'auto',
            'source_key': 'estate.land_area',
        })

        # Create item bound to site_b specifically
        item_site_b = self.env['nhs.eric.item.def'].create({
            'name': 'Site B Land',
            'code': 'S_LAND_B',
            'section_id': sec.id,
            'data_type': 'float',
            'reporting_level': 'site',
            'site_id': site_b.id,
            'source_type': 'auto',
            'source_key': 'estate.land_area',
        })

        # Create return
        ret = self.env['nhs.eric.return'].create({
            'dataset_id': ds.id,
        })

        # Verify that only value records matching the specific site were created
        val_site_a = ret.value_ids.filtered(lambda v: v.item_def_id == item_site_a)
        self.assertEqual(len(val_site_a), 1)
        self.assertEqual(val_site_a.site_id, site_a)

        val_site_b = ret.value_ids.filtered(lambda v: v.item_def_id == item_site_b)
        self.assertEqual(len(val_site_b), 1)
        self.assertEqual(val_site_b.site_id, site_b)

        # Populating should fetch site-specific resolver values
        ret.action_populate()
        self.assertEqual(val_site_a.auto_value, 2.0)
        self.assertEqual(val_site_b.auto_value, 5.0)

        # Update item_site_a configuration: change its site_id to site_b
        item_site_a.write({'site_id': site_b.id})
        
        # Trigger _ensure_value_records to apply changes
        ret._ensure_value_records()

        # The old value record for site_a should have been removed
        val_site_a_old = ret.value_ids.filtered(lambda v: v.item_def_id == item_site_a and v.site_id == site_a)
        self.assertFalse(val_site_a_old)

        # A new value record for site_b should exist
        val_site_a_new = ret.value_ids.filtered(lambda v: v.item_def_id == item_site_a and v.site_id == site_b)
        self.assertEqual(len(val_site_a_new), 1)

        # Repopulating should fetch site-specific resolver value for site_b (5.0)
        ret.action_populate()
        self.assertEqual(val_site_a_new.auto_value, 5.0)

    def test_12_resolver_logic_correctness(self):
        """Test the correctness of the refactored resolver logic, filtering, mappings, and edge cases."""
        company = self.env.company
        resolver = self.env['nhs.eric.source.resolver']

        # Setup Sites
        site_a = self.env['nhs.estate.site'].create({
            'name': 'Site A',
            'code': 'SITEA',
            'company_id': company.id,
            'land_area_ha': 10.0,
            'active': True,
        })
        site_b = self.env['nhs.estate.site'].create({
            'name': 'Site B',
            'code': 'SITEB',
            'company_id': company.id,
            'land_area_ha': 20.0,
            'active': True,
        })
        site_inactive = self.env['nhs.estate.site'].create({
            'name': 'Site Inactive',
            'code': 'SITE_INACTIVE',
            'company_id': company.id,
            'land_area_ha': 30.0,
            'active': False,
        })

        # Setup Buildings
        b_a1 = self.env['nhs.estate.building'].create({
            'name': 'Building A1',
            'code': 'BA1',
            'site_id': site_a.id,
            'build_year': 1970,
            'active': True,
            'nia': 100.0,
        })
        floor_a1 = self.env['nhs.estate.floor'].create({
            'name': 'Floor A1',
            'building_id': b_a1.id,
        })
        self.env['nhs.estate.space'].create({
            'name': 'Space A1',
            'floor_id': floor_a1.id,
            'area': 500.0,
            'utilisation': 'full',
            'is_clinical': True,
        })
        
        b_a2 = self.env['nhs.estate.building'].create({
            'name': 'Building A2',
            'code': 'BA2',
            'site_id': site_a.id,
            'build_year': 1990,
            'active': True,
        })
        floor_a2 = self.env['nhs.estate.floor'].create({
            'name': 'Floor A2',
            'building_id': b_a2.id,
        })
        self.env['nhs.estate.space'].create({
            'name': 'Space A2',
            'floor_id': floor_a2.id,
            'area': 800.0,
            'utilisation': 'full',
            'is_clinical': False,
        })

        b_b1 = self.env['nhs.estate.building'].create({
            'name': 'Building B1',
            'code': 'BB1',
            'site_id': site_b.id,
            'build_year': 2010,
            'active': True,
        })
        floor_b1 = self.env['nhs.estate.floor'].create({
            'name': 'Floor B1',
            'building_id': b_b1.id,
        })
        self.env['nhs.estate.space'].create({
            'name': 'Space B1',
            'floor_id': floor_b1.id,
            'area': 1200.0,
            'utilisation': 'full',
            'is_clinical': True,
        })

        b_inactive = self.env['nhs.estate.building'].create({
            'name': 'Building Inactive',
            'code': 'BINACTIVE',
            'site_id': site_a.id,
            'build_year': 1960,
            'active': False,
        })
        floor_inactive = self.env['nhs.estate.floor'].create({
            'name': 'Floor Inactive',
            'building_id': b_inactive.id,
        })
        self.env['nhs.estate.space'].create({
            'name': 'Space Inactive',
            'floor_id': floor_inactive.id,
            'area': 2000.0,
            'utilisation': 'full',
            'is_clinical': False,
        })

        b_no_year = self.env['nhs.estate.building'].create({
            'name': 'Building No Year',
            'code': 'BNOYEAR',
            'site_id': site_a.id,
            'build_year': 0,
            'active': True,
        })
        floor_no_year = self.env['nhs.estate.floor'].create({
            'name': 'Floor No Year',
            'building_id': b_no_year.id,
        })
        self.env['nhs.estate.space'].create({
            'name': 'Space No Year',
            'floor_id': floor_no_year.id,
            'area': 300.0,
            'utilisation': 'full',
            'is_clinical': False,
        })

        # Invalidate cache and trigger all computed area metrics sequentially
        self.env.invalidate_all()
        (floor_a1 | floor_a2 | floor_b1 | floor_inactive | floor_no_year)._compute_areas()
        (b_a1 | b_a2 | b_b1 | b_inactive | b_no_year)._compute_areas()
        (b_a1 | b_a2 | b_b1 | b_inactive | b_no_year)._compute_analysis()
        (site_a | site_b | site_inactive)._compute_rollups()
        (site_a | site_b | site_inactive)._compute_site_analysis()
        self.env.flush_all()

        # Check total GIA
        self.assertEqual(resolver.resolve('estate.total_gia', company), 2900.0)
        self.assertEqual(resolver.resolve('estate.total_gia', company, site=site_a), 1700.0)
        self.assertEqual(resolver.resolve('estate.total_gia', company, site=site_b), 1200.0)

        # Check site count
        self.assertEqual(resolver.resolve('estate.site_count', company), 2)
        self.assertEqual(resolver.resolve('estate.site_count', company, site=site_a), 1)

        # Check building count
        self.assertEqual(resolver.resolve('estate.building_count', company), 4)
        self.assertEqual(resolver.resolve('estate.building_count', company, site=site_a), 3)
        self.assertEqual(resolver.resolve('estate.building_count', company, site=site_b), 1)

        # Check land area
        self.assertEqual(resolver.resolve('estate.land_area', company), 30.0)
        self.assertEqual(resolver.resolve('estate.land_area', company, site=site_a), 10.0)

        # Setup Backlog
        self.env['nhs.estate.backlog'].create({
            'name': 'Backlog A1',
            'building_id': b_a1.id,
            'risk_category': 'high',
            'cost_estimate': 5000.0,
            'status': 'identified',
            'active': True,
        })
        self.env['nhs.estate.backlog'].create({
            'name': 'Backlog A2',
            'building_id': b_a2.id,
            'risk_category': 'significant',
            'cost_estimate': 15000.0,
            'status': 'planned',
            'active': True,
        })
        self.env['nhs.estate.backlog'].create({
            'name': 'Backlog Inactive',
            'building_id': b_a1.id,
            'risk_category': 'high',
            'cost_estimate': 25000.0,
            'status': 'identified',
            'active': False,
        })
        self.env['nhs.estate.backlog'].create({
            'name': 'Backlog Resolved',
            'building_id': b_a1.id,
            'risk_category': 'high',
            'cost_estimate': 35000.0,
            'status': 'resolved',
            'active': True,
        })
        self.env['nhs.estate.backlog'].create({
            'name': 'Backlog Inactive Building',
            'building_id': b_inactive.id,
            'risk_category': 'high',
            'cost_estimate': 45000.0,
            'status': 'identified',
            'active': True,
        })
        self.env['nhs.estate.backlog'].create({
            'name': 'Backlog B1',
            'building_id': b_b1.id,
            'risk_category': 'moderate',
            'cost_estimate': 8000.0,
            'status': 'in_progress',
            'active': True,
        })

        self.env.flush_all()

        # Verify Backlog resolution
        self.assertEqual(resolver.resolve('estate.backlog.high', company), 5000.0)
        self.assertEqual(resolver.resolve('estate.backlog.significant', company), 15000.0)
        self.assertEqual(resolver.resolve('estate.backlog.moderate', company), 8000.0)
        self.assertEqual(resolver.resolve('estate.backlog.low', company), 0.0)
        self.assertEqual(resolver.resolve('estate.backlog.total', company), 28000.0)

        self.assertEqual(resolver.resolve('estate.backlog.high', company, site=site_a), 5000.0)
        self.assertEqual(resolver.resolve('estate.backlog.total', company, site=site_a), 20000.0)
        self.assertEqual(resolver.resolve('estate.backlog.total', company, site=site_b), 8000.0)

        # Check Age Bands
        self.assertEqual(resolver.resolve('estate.age_bands.pre_1980', company), 1)
        self.assertEqual(resolver.resolve('estate.age_bands.1980_2000', company), 1)
        self.assertEqual(resolver.resolve('estate.age_bands.post_2000', company), 1)

        # Check Age Bands GIA percentage
        self.assertAlmostEqual(resolver.resolve('estate.age_bands_pct.pre_1980', company), 23.076923, places=4)
        self.assertAlmostEqual(resolver.resolve('estate.age_bands_pct.1980_2000', company), 30.769230, places=4)
        self.assertAlmostEqual(resolver.resolve('estate.age_bands_pct.post_2000', company), 46.153846, places=4)

        self.assertAlmostEqual(resolver.resolve('estate.age_bands_pct.pre_1980', company, site=site_a), 42.857142, places=4)

        # Setup Tenure
        tenure_a1 = self.env['nhs.estate.tenure'].create({
            'building_id': b_a1.id,
            'tenure_type': 'freehold',
        })
        tenure_a2 = self.env['nhs.estate.tenure'].create({
            'building_id': b_a2.id,
            'tenure_type': 'leasehold',
        })
        b_a1.write({'tenure_id': tenure_a1.id})
        b_a2.write({'tenure_id': tenure_a2.id})
        self.env.flush_all()

        self.assertAlmostEqual(resolver.resolve('estate.tenure.owned', company), 42.857142, places=4)
        self.assertAlmostEqual(resolver.resolve('estate.tenure.leased', company), 57.142857, places=4)

        # Setup Condition Grade
        self.env['nhs.estate.condition'].create({
            'building_id': b_a1.id,
            'survey_date': '2026-01-01',
            'facet_physical': 'B',
        })
        self.env['nhs.estate.condition'].create({
            'building_id': b_a2.id,
            'survey_date': '2026-01-01',
            'facet_physical': 'C',
        })
        self.env['nhs.estate.condition'].create({
            'building_id': b_b1.id,
            'survey_date': '2026-01-01',
            'facet_physical': 'A',
        })

        (b_a1 | b_a2 | b_b1)._compute_latest_condition_grade()
        self.env.flush_all()

        self.assertEqual(resolver.resolve('estate.condition', company), 3.0)
        self.assertAlmostEqual(resolver.resolve('estate.condition.A', company), 46.153846, places=4)
        self.assertAlmostEqual(resolver.resolve('estate.condition.B', company), 23.076923, places=4)
        self.assertEqual(resolver.resolve('estate.condition.count.A', company), 1)

        # Setup Compliance items
        disc_fire = self.env['nhs.compliance.discipline'].search([('code', '=', 'FIRE')], limit=1)
        disc_lightning = self.env['nhs.compliance.discipline'].search([('code', '=', 'LIGHT')], limit=1)

        type_fire = self.env['nhs.compliance.type'].create({
            'name': 'Fire Alarm Inspection',
            'discipline_id': disc_fire.id,
        })
        type_lightning = self.env['nhs.compliance.type'].create({
            'name': 'Lightning Protection Test',
            'discipline_id': disc_lightning.id,
        })

        item_fire_a = self.env['nhs.compliance.item'].create({
            'compliance_type_id': type_fire.id,
            'site_id': site_a.id,
            'company_id': company.id,
            'frequency_value': 1,
            'frequency_unit': 'year',
        })
        item_lightning_b = self.env['nhs.compliance.item'].create({
            'compliance_type_id': type_lightning.id,
            'site_id': site_b.id,
            'company_id': company.id,
            'frequency_value': 1,
            'frequency_unit': 'year',
        })

        self.env['nhs.compliance.test'].create({
            'item_id': item_fire_a.id,
            'test_date': '2026-05-01',
            'outcome': 'pass',
        })
        item_lightning_b.write({'next_due_date': '2025-01-01'})

        item_fire_a._compute_status()
        item_lightning_b._compute_status()
        self.env.flush_all()

        self.assertEqual(resolver.resolve('compliance.fire', company), 100.0)
        self.assertEqual(resolver.resolve('compliance.lightning', company), 0.0)
        self.assertEqual(resolver.resolve('compliance.pct', company), 50.0)
        self.assertEqual(resolver.resolve('compliance.overdue_count', company), 1)

        self.assertEqual(resolver.resolve('compliance.pct', company, site=site_a), 100.0)
        self.assertEqual(resolver.resolve('compliance.overdue_count', company, site=site_a), 0)
        self.assertEqual(resolver.resolve('compliance.pct', company, site=site_b), 0.0)
        self.assertEqual(resolver.resolve('compliance.overdue_count', company, site=site_b), 1)

        # Traceability notes
        note_gia = resolver.get_traceability_note('estate.total_gia', company)
        self.assertIn('Site A', note_gia)
        self.assertIn('Site B', note_gia)

        note_fire = resolver.get_traceability_note('compliance.fire', company)
        self.assertIn('Fire Alarm Inspection', note_fire)

    def test_13_computed_field_calculations(self):
        """Test the new computed fields and operators ( sub, mul, div, avg, pct) and constraints."""
        # Setup dataset
        ds = self.env['nhs.eric.dataset'].create({
            'name': 'Test Operators',
            'year': '2030/31',
            'state': 'active',
        })
        sec = self.env['nhs.eric.section'].create({
            'name': 'Test Section',
            'code': 'test_sec',
            'sequence': 10,
            'dataset_id': ds.id,
        })
        
        # Inputs
        inp_a = self.env['nhs.eric.item.def'].create({
            'name': 'Input A',
            'code': 'INP_A',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'manual',
        })
        inp_b = self.env['nhs.eric.item.def'].create({
            'name': 'Input B',
            'code': 'INP_B',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'manual',
        })

        # Test operator Add
        comp_add = self.env['nhs.eric.item.def'].create({
            'name': 'Comp Add',
            'code': 'COMP_ADD',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'computed',
            'computation_operator': 'sum',
            'computed_input_ids': [(6, 0, [inp_a.id, inp_b.id])],
        })

        # Test operator Subtract
        comp_sub = self.env['nhs.eric.item.def'].create({
            'name': 'Comp Sub',
            'code': 'COMP_SUB',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'computed',
            'computation_operator': 'sub',
            'computed_input_ids': [(6, 0, [inp_a.id, inp_b.id])],
        })

        # Test operator Multiply
        comp_mul = self.env['nhs.eric.item.def'].create({
            'name': 'Comp Mul',
            'code': 'COMP_MUL',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'computed',
            'computation_operator': 'mul',
            'computed_input_ids': [(6, 0, [inp_a.id, inp_b.id])],
        })

        # Test operator Divide
        comp_div = self.env['nhs.eric.item.def'].create({
            'name': 'Comp Div',
            'code': 'COMP_DIV',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'computed',
            'computation_operator': 'div',
            'computed_input_ids': [(6, 0, [inp_a.id, inp_b.id])],
        })

        # Test operator Average
        comp_avg = self.env['nhs.eric.item.def'].create({
            'name': 'Comp Avg',
            'code': 'COMP_AVG',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'computed',
            'computation_operator': 'avg',
            'computed_input_ids': [(6, 0, [inp_a.id, inp_b.id])],
        })

        # Test operator Percentage
        comp_pct = self.env['nhs.eric.item.def'].create({
            'name': 'Comp Pct',
            'code': 'COMP_PCT',
            'section_id': sec.id,
            'data_type': 'float',
            'source_type': 'computed',
            'computation_operator': 'pct',
            'computed_input_ids': [(6, 0, [inp_a.id, inp_b.id])],
        })

        # Circular dependency validation check - self loop
        with self.assertRaises(ValidationError):
            comp_add.write({'computed_input_ids': [(4, comp_add.id)]})

        # Two-item loop check
        inp_a.write({
            'source_type': 'computed',
            'computation_operator': 'sum',
            'computed_input_ids': [(6, 0, [inp_b.id])]
        })
        with self.assertRaises(ValidationError):
            inp_b.write({
                'source_type': 'computed',
                'computation_operator': 'sum',
                'computed_input_ids': [(6, 0, [inp_a.id])]
            })

        # Reset source_type back to manual for inputs
        inp_a.write({'source_type': 'manual', 'computed_input_ids': [(5, 0, 0)]})
        inp_b.write({'source_type': 'manual', 'computed_input_ids': [(5, 0, 0)]})

        # Creating return
        ret = self.env['nhs.eric.return'].create({
            'dataset_id': ds.id,
            'state': 'draft',
        })

        v_a = ret.value_ids.filtered(lambda v: v.item_def_id == inp_a)
        v_b = ret.value_ids.filtered(lambda v: v.item_def_id == inp_b)
        
        v_add = ret.value_ids.filtered(lambda v: v.item_def_id == comp_add)
        v_sub = ret.value_ids.filtered(lambda v: v.item_def_id == comp_sub)
        v_mul = ret.value_ids.filtered(lambda v: v.item_def_id == comp_mul)
        v_div = ret.value_ids.filtered(lambda v: v.item_def_id == comp_div)
        v_avg = ret.value_ids.filtered(lambda v: v.item_def_id == comp_avg)
        v_pct = ret.value_ids.filtered(lambda v: v.item_def_id == comp_pct)

        # Write inputs
        v_a.write({'value_number': 15.0})
        v_b.write({'value_number': 5.0})

        self.assertEqual(v_add.value_number, 20.0) # 15 + 5
        self.assertEqual(v_sub.value_number, 10.0) # 15 - 5
        self.assertEqual(v_mul.value_number, 75.0) # 15 * 5
        self.assertEqual(v_div.value_number, 3.0)  # 15 / 5
        self.assertEqual(v_avg.value_number, 10.0) # (15 + 5) / 2
        self.assertEqual(v_pct.value_number, 300.0) # (15 / 5) * 100

    def test_14_yoy_trend_and_aggregation(self):
        """Test Year-on-Year trend calculations, site aggregation for key metrics, and auto-refresh search/read_group hooks."""
        # Create site records
        site_c = self.env['nhs.estate.site'].create({
            'name': 'Test Site C',
            'code': 'TSITEC',
            'company_id': self.env.company.id,
        })
        site_d = self.env['nhs.estate.site'].create({
            'name': 'Test Site D',
            'code': 'TSITED',
            'company_id': self.env.company.id,
        })

        # Set GIA item to be site level
        self.item_gia.write({
            'reporting_level': 'site',
        })

        # Create return
        ret = self.env['nhs.eric.return'].create({
            'dataset_id': self.dataset_2025.id,
        })

        # Ensure GIA values exist for both site C and site D
        val_c = ret.value_ids.filtered(lambda v: v.item_def_id == self.item_gia and v.site_id == site_c)
        val_d = ret.value_ids.filtered(lambda v: v.item_def_id == self.item_gia and v.site_id == site_d)
        
        self.assertTrue(val_c)
        self.assertTrue(val_d)

        # Write site level GIA values
        val_c.write({'value_number': 350.0, 'status': 'populated', 'is_overridden': True})
        val_d.write({'value_number': 450.0, 'status': 'populated', 'is_overridden': True})

        # Get aggregated key metric
        aggregated_gia = ret._get_key_metric_value('gia')
        self.assertEqual(aggregated_gia, 800.0) # 350.0 + 450.0

        # Mark return as finalised
        self.env['ir.config_parameter'].sudo().set_param('odoo_nhs_eric.eric_validation_policy', 'warn')
        ret.with_context(bypass_sign_off_check=True).action_finalise()
        self.assertEqual(ret.state, 'finalised')

        # Verify trend metric got created/updated
        trend = self.env['nhs.eric.trend.metric'].search([
            ('company_id', '=', ret.company_id.id),
            ('year', '=', ret.year)
        ])
        self.assertTrue(trend)
        self.assertEqual(trend.gia, 800.0)

        # Update return values directly in database to simulate manual changes bypassing normal hooks,
        # then check if search/read_group automatically refreshes the trends.
        self.env.cr.execute(
            "UPDATE nhs_eric_value SET value_number = 500.0 WHERE id = %s",
            (val_c.id,)
        )
        self.env.invalidate_all()
        # Search again - should trigger refresh_trends
        trend_refreshed = self.env['nhs.eric.trend.metric'].search([
            ('company_id', '=', ret.company_id.id),
            ('year', '=', ret.year)
        ])
        self.assertEqual(trend_refreshed.gia, 950.0) # 500.0 + 450.0

    def test_15_non_numeric_auto_populate_flow(self):
        """Test the auto-population, validation, display, and overrides for non-numeric (text, boolean) items."""
        from odoo.addons.odoo_nhs_eric.models.nhs_eric_source_resolver import NhsEricSourceResolver
        
        orig_resolve = NhsEricSourceResolver.resolve
        def mock_resolve(resolver_self, source_key, company, year=None, site=None):
            if source_key == 'estate.test_text':
                return 'Yes'
            elif source_key == 'estate.test_bool':
                return True
            return orig_resolve(resolver_self, source_key, company, year, site)

        NhsEricSourceResolver.resolve = mock_resolve

        try:
            # Create text and boolean item definitions
            item_text = self.env['nhs.eric.item.def'].create({
                'name': 'Test Text Auto Item',
                'code': 'TTEXT',
                'section_id': self.section_profile.id,
                'data_type': 'text',
                'source_type': 'auto',
                'source_key': 'estate.test_text',
                'allowed_values': 'Yes,No,Partial',
                'reporting_level': 'organisational',
            })
            item_bool = self.env['nhs.eric.item.def'].create({
                'name': 'Test Boolean Auto Item',
                'code': 'TBOOL',
                'section_id': self.section_profile.id,
                'data_type': 'boolean',
                'source_type': 'auto',
                'source_key': 'estate.test_bool',
                'reporting_level': 'organisational',
            })

            # Create return
            ret = self.env['nhs.eric.return'].create({
                'dataset_id': self.dataset_2025.id,
            })

            # Fetch value records
            val_text_rec = ret.value_ids.filtered(lambda v: v.item_def_id == item_text)
            val_bool_rec = ret.value_ids.filtered(lambda v: v.item_def_id == item_bool)

            self.assertTrue(val_text_rec)
            self.assertTrue(val_bool_rec)

            # Initially they should be gaps
            self.assertEqual(val_text_rec.status, 'gap')
            self.assertEqual(val_bool_rec.status, 'gap')

            # Populate return
            ret.action_populate()

            # Verify resolved values got populated correctly in respective fields
            self.assertEqual(val_text_rec.auto_value_text, 'Yes')
            self.assertEqual(val_text_rec.value_text, 'Yes')
            self.assertEqual(val_text_rec.status, 'populated')
            self.assertEqual(val_text_rec._get_value_display(), 'Yes')

            self.assertTrue(val_bool_rec.auto_value_bool)
            self.assertTrue(val_bool_rec.value_bool)
            self.assertEqual(val_bool_rec.status, 'populated')
            self.assertEqual(val_bool_rec._get_value_display(), 'Yes')

            # Run validation - should succeed with no errors
            ret.with_context(bypass_sign_off_check=True).action_validate()
            self.assertEqual(val_text_rec.status, 'populated')
            self.assertEqual(val_bool_rec.status, 'populated')

            # Override the text value to "No"
            val_text_rec.write({'value_text': 'No'})
            self.assertTrue(val_text_rec.is_overridden)
            self.assertEqual(val_text_rec.value_text, 'No')
            self.assertEqual(val_text_rec.auto_value_text, 'Yes') # auto_value_text should remain unchanged
            self.assertEqual(val_text_rec._get_value_display(), 'No')

            # Clear override
            val_text_rec.action_clear_override()
            self.assertFalse(val_text_rec.is_overridden)
            self.assertEqual(val_text_rec.value_text, 'Yes')
            self.assertEqual(val_text_rec._get_value_display(), 'Yes')

        finally:
            NhsEricSourceResolver.resolve = orig_resolve





