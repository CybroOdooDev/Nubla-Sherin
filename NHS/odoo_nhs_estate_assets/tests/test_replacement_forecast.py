# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo.fields import Date
from dateutil.relativedelta import relativedelta


class TestReplacementForecast(TransactionCase):

    def setUp(self):
        super(TestReplacementForecast, self).setUp()
        self.Category = self.env['nhs.device.category']
        self.Device = self.env['nhs.device']

        self.category = self.Category.create({
            'name': 'Test Ultrasound System',
            'expected_life_years': 5,
        })

        self.device = self.Device.create({
            'name': 'Ultrasound #001',
            'category_id': self.category.id,
            'acquisition_date': Date.today() - relativedelta(years=3),
            'acquisition_cost': 5000.0,
            'expected_life_years': 5,
            'manufacturer': 'Test Corp',
            'department': 'Cardiology',
        })

    def test_01_replacement_date_and_cost_computation(self):
        """Test calculation of expected_replacement_date, replacement_year, and estimated_replacement_cost."""
        self.assertTrue(self.device.expected_replacement_date)
        expected_date = self.device.acquisition_date + relativedelta(years=5)
        self.assertEqual(self.device.expected_replacement_date, expected_date)
        self.assertEqual(self.device.replacement_year, expected_date.year)
        self.assertEqual(self.device.estimated_replacement_cost, 5000.0)

    def test_02_manual_override(self):
        """Test manual modification of replacement date and estimated replacement cost."""
        custom_date = Date.today() + relativedelta(years=1)
        self.device.write({
            'expected_replacement_date': custom_date,
            'estimated_replacement_cost': 6500.0,
        })
        self.assertEqual(self.device.replacement_year, custom_date.year)
        self.assertEqual(self.device.estimated_replacement_cost, 6500.0)

    def test_03_report_rendering(self):
        """Test QWeb PDF replacement forecast report rendering."""
        report = self.env.ref('odoo_nhs_estate_assets.action_report_nhs_replacement_forecast')
        html_content, report_type = report._render_qweb_html(self.device.ids)
        self.assertEqual(report_type, 'html')
        self.assertTrue(html_content)
        self.assertIn(b'Replacement Forecast Report', html_content)
        self.assertIn(b'Ultrasound #001', html_content)

    def test_04_indicative_depreciation_method_config(self):
        """Test indicative value calculation using ir.config_parameter setting."""
        Param = self.env['ir.config_parameter'].sudo()

        # 1. Straight-line depreciation method
        Param.set_param('odoo_nhs_estate_assets.indicative_depreciation_method', 'straight_line')
        self.device._compute_indicative_value()
        # Acquisition cost = 5000, 3 of 5 years in service, remaining = 2 years -> 5000 * 2/5 = 2000
        self.assertAlmostEqual(self.device.indicative_value, 2000.0, delta=100.0)

        # 2. No Depreciation (Cost Only) method
        Param.set_param('odoo_nhs_estate_assets.indicative_depreciation_method', 'none')
        self.device._compute_indicative_value()
        self.assertEqual(self.device.indicative_value, 5000.0)

    def test_05_overdue_escalation_threshold_config(self):
        """Test overdue escalation threshold configuration."""
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param('odoo_nhs_estate_assets.overdue_escalation_days', '10')

        sched_type = self.env['nhs.device.schedule.type'].search([], limit=1)
        schedule = self.env['nhs.device.schedule'].create({
            'device_id': self.device.id,
            'schedule_type_id': sched_type.id,
            'interval_months': 12,
            'last_done_date': Date.today() - relativedelta(years=1, days=5), # 5 days overdue
        })
        schedule._compute_status()
        schedule._compute_is_escalated()
        self.assertEqual(schedule.status, 'overdue')
        self.assertFalse(schedule.is_escalated) # 5 days overdue < 10 threshold

        Param.set_param('odoo_nhs_estate_assets.overdue_escalation_days', '3')
        schedule._compute_is_escalated()
        self.assertTrue(schedule.is_escalated) # 5 days overdue >= 3 threshold

    def test_06_end_of_life_assignee_fallback(self):
        """Test that End-of-Life / replacement-due activities assign to responsible user or manager fallback."""
        test_user = self.env['res.users'].create({
            'name': 'Test Responsible Person',
            'login': 'test_responsible_user',
            'email': 'responsible@test.com',
        })
        manager_group = self.env.ref('odoo_nhs_estate_assets.group_nhs_equipment_manager')
        group_field = 'group_ids' if 'group_ids' in self.env['res.users']._fields else 'groups_id'
        manager_user = self.env['res.users'].create({
            'name': 'Test Equipment Manager',
            'login': 'test_equipment_manager',
            'email': 'manager@test.com',
            group_field: [(4, manager_group.id)],
        })

        # 1. Device with responsible person assigned
        self.device.responsible_user_id = test_user
        assignee = self.device._get_responsible_or_manager_user()
        self.assertEqual(assignee, test_user)

        # 2. Device WITHOUT responsible person -> falls back to Manager
        self.device.responsible_user_id = False
        assignee_fallback = self.device._get_responsible_or_manager_user()
        self.assertTrue(assignee_fallback.has_group('odoo_nhs_estate_assets.group_nhs_equipment_manager'))

    def test_07_safety_alert_pending_activities(self):
        """Test activity creation for responsible person on pending/quarantined devices under active safety alert."""
        alert = self.env['nhs.device.alert'].create({
            'name': 'Medical Device Recall Alert',
            'reference': 'MHRA-2026-001',
            'state': 'open',
            'action_deadline': Date.today() + relativedelta(days=7),
            'line_ids': [(0, 0, {
                'device_id': self.device.id,
                'action_status': 'pending',
                'action_required': 'Inspect transducer cable',
            })]
        })

        alert._create_pending_device_activities()

        device_model_id = self.env['ir.model']._get_id('nhs.device')
        activity = self.env['mail.activity'].search([
            ('res_id', '=', self.device.id),
            ('res_model_id', '=', device_model_id),
            ('summary', 'like', '[SAFETY ALERT ACTION REQUIRED]'),
        ], limit=1)

        self.assertTrue(activity)
        self.assertEqual(activity.date_deadline, alert.action_deadline)

    def test_08_weekly_digest_cron(self):
        """Test execution of the weekly digest cron job."""
        # Execute weekly digest cron
        self.env['nhs.device']._cron_send_weekly_digest()
        # Ensure no exception is raised during execution
        self.assertTrue(True)

    def test_09_safety_alert_expiring_reminder(self):
        """Test safety alert expiring reminder activity generation when deadline is within 7 days."""
        alert = self.env['nhs.device.alert'].create({
            'name': 'Expiring Recall Alert',
            'reference': 'MHRA-2026-EXP',
            'state': 'open',
            'action_deadline': Date.today() + relativedelta(days=3),
            'line_ids': [(0, 0, {
                'device_id': self.device.id,
                'action_status': 'quarantined',
                'action_required': 'Quarantine immediately',
            })]
        })

        self.assertTrue(alert.is_expiring)
        alert._create_pending_device_activities()

        device_model_id = self.env['ir.model']._get_id('nhs.device')
        activity = self.env['mail.activity'].search([
            ('res_id', '=', self.device.id),
            ('res_model_id', '=', device_model_id),
            ('summary', 'like', '[SAFETY ALERT EXPIRING REMINDER]'),
        ], limit=1)

        self.assertTrue(activity)
        self.assertEqual(activity.date_deadline, alert.action_deadline)



