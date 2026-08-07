# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields


class TestEricExport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestEricExport, cls).setUpClass()

        # Prior dataset and return
        cls.dataset_prior = cls.env['nhs.eric.dataset'].create({
            'name': 'ERIC 2024/25',
            'year': '2024/25',
            'state': 'active',
        })
        cls.section_prior = cls.env['nhs.eric.section'].create({
            'name': 'Profile Section',
            'code': 'profile',
            'sequence': 10,
            'dataset_id': cls.dataset_prior.id,
        })
        cls.item_gia_prior = cls.env['nhs.eric.item.def'].create({
            'name': 'Total GIA',
            'code': 'E_GIA',
            'section_id': cls.section_prior.id,
            'data_type': 'float',
            'unit': 'm²',
            'source_type': 'manual',
            'required': True,
        })
        cls.item_backlog_prior = cls.env['nhs.eric.item.def'].create({
            'name': 'Total Backlog Cost',
            'code': 'E_BACKLOG_TOT',
            'section_id': cls.section_prior.id,
            'data_type': 'currency',
            'unit': '£',
            'source_type': 'manual',
            'required': False,
        })
        cls.return_prior = cls.env['nhs.eric.return'].create({
            'dataset_id': cls.dataset_prior.id,
            'year': '2024/25',
        })

        # Populate prior return values
        for val in cls.return_prior.value_ids:
            if val.item_code == 'E_GIA':
                val.write({'value_number': 1000.0, 'status': 'populated'})
            elif val.item_code == 'E_BACKLOG_TOT':
                val.write({'value_number': 50000.0, 'status': 'populated'})

        # Current dataset
        cls.dataset_current = cls.env['nhs.eric.dataset'].create({
            'name': 'ERIC 2025/26',
            'year': '2025/26',
            'state': 'active',
            'prior_dataset_id': cls.dataset_prior.id,
        })
        cls.section_current = cls.env['nhs.eric.section'].create({
            'name': 'Profile Section',
            'code': 'profile',
            'sequence': 10,
            'dataset_id': cls.dataset_current.id,
        })
        cls.item_gia_current = cls.env['nhs.eric.item.def'].create({
            'name': 'Total GIA',
            'code': 'E_GIA',
            'section_id': cls.section_current.id,
            'data_type': 'float',
            'unit': 'm²',
            'source_type': 'manual',
            'required': True,
        })
        cls.item_backlog_current = cls.env['nhs.eric.item.def'].create({
            'name': 'Total Backlog Cost',
            'code': 'E_BACKLOG_TOT',
            'section_id': cls.section_current.id,
            'data_type': 'currency',
            'unit': '£',
            'source_type': 'manual',
            'required': False,
        })
        cls.item_site_gia = cls.env['nhs.eric.item.def'].create({
            'name': 'Site GIA',
            'code': 'S_GIA',
            'section_id': cls.section_current.id,
            'data_type': 'float',
            'reporting_level': 'site',
            'source_type': 'manual',
            'required': True,
        })

        # Create site
        cls.site_a = cls.env['nhs.estate.site'].create({
            'name': 'Test Site A',
            'code': 'TSITEA',
            'company_id': cls.env.company.id,
        })

        cls.return_current = cls.env['nhs.eric.return'].create({
            'dataset_id': cls.dataset_current.id,
            'prior_return_id': cls.return_prior.id,
            'year': '2025/26',
        })

        # Populate current values
        for val in cls.return_current.value_ids:
            if val.item_code == 'E_GIA':
                val.write({'value_number': 1200.0, 'status': 'populated'})
            elif val.item_code == 'E_BACKLOG_TOT':
                val.write({'value_number': 60000.0, 'status': 'populated'})
            elif val.item_code == 'S_GIA':
                val.write({'value_number': 1200.0, 'status': 'populated'})

    def test_export_formats(self):
        """Verify that the export wizard processes all formats without raising exceptions."""
        wizard = self.env['nhs.eric.export.wizard'].create({
            'return_id': self.return_current.id,
        })

        # 1. Submission Workbook (Excel)
        wizard.write({'export_format': 'submission_excel'})
        action = wizard.action_export()
        self.assertEqual(action['res_model'], 'nhs.eric.export.wizard')
        self.assertTrue(wizard.export_file)
        self.assertTrue(wizard.filename.endswith('.xlsx'))

        # Clear file to ensure next format creates new content
        wizard.write({'export_file': False, 'filename': False})

        # 2. Submission Trust CSV
        wizard.write({'export_format': 'submission_csv_trust'})
        action = wizard.action_export()
        self.assertEqual(action['res_model'], 'nhs.eric.export.wizard')
        self.assertTrue(wizard.export_file)
        self.assertTrue(wizard.filename.endswith('.csv'))

        wizard.write({'export_file': False, 'filename': False})

        # 3. Submission Site CSV
        wizard.write({'export_format': 'submission_csv_site'})
        action = wizard.action_export()
        self.assertEqual(action['res_model'], 'nhs.eric.export.wizard')
        self.assertTrue(wizard.export_file)
        self.assertTrue(wizard.filename.endswith('.csv'))

        wizard.write({'export_file': False, 'filename': False})

        # 4. Gap Excel
        wizard.write({'export_format': 'gap_excel'})
        action = wizard.action_export()
        self.assertEqual(action['res_model'], 'nhs.eric.export.wizard')
        self.assertTrue(wizard.export_file)
        self.assertTrue(wizard.filename.endswith('.xlsx'))

        wizard.write({'export_file': False, 'filename': False})

        # 5. Summary Excel
        wizard.write({'export_format': 'summary'})
        action = wizard.action_export()
        self.assertEqual(action['res_model'], 'nhs.eric.export.wizard')
        self.assertTrue(wizard.export_file)
        self.assertTrue(wizard.filename.endswith('.xlsx'))

        wizard.write({'export_file': False, 'filename': False})

        # 6. Full Excel
        wizard.write({'export_format': 'full_excel'})
        action = wizard.action_export()
        self.assertEqual(action['res_model'], 'nhs.eric.export.wizard')
        self.assertTrue(wizard.export_file)
        self.assertTrue(wizard.filename.endswith('.xlsx'))

        # 7. Action download url check
        download_action = wizard.action_download()
        self.assertEqual(download_action['type'], 'ir.actions.act_url')
        self.assertIn('/export_file/', download_action['url'])

        # 8. QWeb PDF reports trigger check
        wizard.write({'export_format': 'pdf'})
        pdf_action = wizard.action_export()
        self.assertEqual(pdf_action['type'], 'ir.actions.report')
        self.assertEqual(pdf_action['report_name'], 'odoo_nhs_eric.report_nhs_eric_return_template')

        wizard.write({'export_format': 'gap_pdf'})
        gap_pdf_action = wizard.action_export()
        self.assertEqual(gap_pdf_action['type'], 'ir.actions.report')
        self.assertEqual(gap_pdf_action['report_name'], 'odoo_nhs_eric.report_nhs_eric_gap_template')
