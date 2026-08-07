# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo.fields import Date
from dateutil.relativedelta import relativedelta


class TestDeviceMaintenanceWorkflow(TransactionCase):

    def setUp(self):
        super(TestDeviceMaintenanceWorkflow, self).setUp()
        self.ScheduleType = self.env['nhs.device.schedule.type']
        self.Category = self.env['nhs.device.category']
        self.Device = self.env['nhs.device']
        self.Schedule = self.env['nhs.device.schedule']
        self.Service = self.env['nhs.device.service']
        self.MaintenanceRequest = self.env['maintenance.request']
        self.MaintenanceStage = self.env['maintenance.stage']

        # Create schedule type
        self.ppm_type = self.ScheduleType.create({
            'name': 'Annual PPM',
            'code': 'ppm',
        })

        # Create category with default schedule
        self.category = self.Category.create({
            'name': 'Test Infusion Pump',
            'default_schedule_ids': [(0, 0, {
                'schedule_type_id': self.ppm_type.id,
                'interval_months': 12,
                'delivery': 'in_house',
            })]
        })

        # Create maintenance stages
        self.stage_new = self.MaintenanceStage.create({'name': 'New', 'sequence': 1, 'fold': False})
        self.stage_in_progress = self.MaintenanceStage.create({'name': 'In Progress', 'sequence': 2, 'fold': False})
        self.stage_repaired = self.MaintenanceStage.create({'name': 'Repaired', 'sequence': 3, 'fold': True})
        self.stage_scrap = self.MaintenanceStage.create({'name': 'Scrap', 'sequence': 4, 'fold': True})

    def test_01_device_creation_schedule_dates(self):
        """Test device creation copies category schedule with empty initial dates."""
        device = self.Device.create({
            'name': 'Pump #001',
            'category_id': self.category.id,
        })

        self.assertEqual(len(device.schedule_ids), 1)
        schedule = device.schedule_ids[0]
        self.assertFalse(schedule.last_done_date, "New device schedule should have no last_done_date")
        self.assertFalse(schedule.next_due_date, "New device schedule should have no next_due_date")
        self.assertEqual(schedule.interval_months, 12)

    def test_02_first_service_progression(self):
        """Test first service with pass outcome sets last_done_date and calculates next_due_date."""
        device = self.Device.create({
            'name': 'Pump #002',
            'category_id': self.category.id,
        })
        schedule = device.schedule_ids[0]

        service_date = Date.today() - relativedelta(days=5)
        service = self.Service.create({
            'device_id': device.id,
            'schedule_id': schedule.id,
            'service_type': 'ppm',
            'service_date': service_date,
            'outcome': 'pass',
            'performed_by_id': self.env.user.id,
        })

        self.assertEqual(schedule.last_done_date, service_date)
        expected_next_due = service_date + relativedelta(months=12)
        self.assertEqual(schedule.next_due_date, expected_next_due)
        self.assertEqual(schedule.status, 'ok')

    def test_03_maintenance_request_cron_and_single_request_enforcement(self):
        """Test cron creates maintenance request when due and prevents duplicate open requests."""
        device = self.Device.create({
            'name': 'Pump #003',
            'category_id': self.category.id,
        })
        schedule = device.schedule_ids[0]

        # Manually set next_due_date to past date
        schedule.last_done_date = Date.today() - relativedelta(months=13)
        schedule._compute_next_due_date()

        # Run cron
        self.Schedule._cron_generate_maintenance_requests()

        requests = self.MaintenanceRequest.search([('nhs_schedule_id', '=', schedule.id)])
        self.assertEqual(len(requests), 1, "Cron should create exactly one maintenance request")
        request = requests[0]
        self.assertEqual(request.nhs_device_id, device)

        # Run cron again - should not create duplicate request
        self.Schedule._cron_generate_maintenance_requests()
        requests_after = self.MaintenanceRequest.search([('nhs_schedule_id', '=', schedule.id)])
        self.assertEqual(len(requests_after), 1, "Cron should not create duplicate open requests")

    def test_04_maintenance_request_workflow_repaired_pass(self):
        """Test service record creation from Repaired stage with Pass outcome rolls schedule forward."""
        device = self.Device.create({
            'name': 'Pump #004',
            'category_id': self.category.id,
        })
        schedule = device.schedule_ids[0]
        schedule.last_done_date = Date.today() - relativedelta(months=13)
        schedule._compute_next_due_date()

        # Create maintenance request
        request = self.MaintenanceRequest.create({
            'name': 'Test Request',
            'nhs_device_id': device.id,
            'nhs_schedule_id': schedule.id,
            'stage_id': self.stage_in_progress.id,
        })

        # Cannot create service record while in progress
        with self.assertRaises(Exception):
            request.action_create_service_record()

        # Move request to Repaired stage
        request.stage_id = self.stage_repaired.id

        # Action opens service creation
        today = Date.today()
        service = self.Service.create({
            'device_id': device.id,
            'schedule_id': schedule.id,
            'maintenance_request_id': request.id,
            'service_type': 'ppm',
            'service_date': today,
            'outcome': 'pass',
            'performed_by_id': self.env.user.id,
        })

        self.assertTrue(request.service_record_created)
        self.assertEqual(request.nhs_service_id, service)
        self.assertEqual(schedule.last_done_date, today)
        self.assertEqual(schedule.next_due_date, today + relativedelta(months=12))

    def test_05_service_fail_and_scrap_outcomes(self):
        """Test service Fail sets awaiting_repair without rolling schedule; Scrap sets out_of_service and deactivates schedule."""
        device = self.Device.create({
            'name': 'Pump #005',
            'category_id': self.category.id,
        })
        schedule = device.schedule_ids[0]
        old_due = Date.today() - relativedelta(days=10)
        schedule.last_done_date = Date.today() - relativedelta(months=13)
        schedule._compute_next_due_date()

        # Test Fail
        service_fail = self.Service.create({
            'device_id': device.id,
            'schedule_id': schedule.id,
            'service_type': 'ppm',
            'service_date': Date.today(),
            'outcome': 'fail',
            'performed_by_id': self.env.user.id,
        })
        self.assertEqual(device.status, 'awaiting_repair')
        self.assertNotEqual(schedule.last_done_date, Date.today(), "Failed service must not update last_done_date")

        # Test Scrap
        service_scrap = self.Service.create({
            'device_id': device.id,
            'schedule_id': schedule.id,
            'service_type': 'ppm',
            'service_date': Date.today(),
            'outcome': 'removed_from_use',
            'performed_by_id': self.env.user.id,
        })
        self.assertEqual(device.status, 'out_of_service')
        self.assertFalse(schedule.active, "Removed from use must deactivate future schedule")

    def test_06_maintenance_equipment_explicit_creation(self):
        """Test that maintenance.equipment is only created when create_maintenance_equipment is True."""
        # Device without equipment integration option
        device_no_equip = self.Device.create({
            'name': 'Pump Without Equipment Integration',
            'category_id': self.category.id,
            'is_medical_device': True,
            'create_maintenance_equipment': False,
        })
        equip_no = self.env['maintenance.equipment'].search([('nhs_device_id', '=', device_no_equip.id)])
        self.assertFalse(equip_no, "No equipment record should be created when create_maintenance_equipment is False")

        # Device with equipment integration option
        device_with_equip = self.Device.create({
            'name': 'Pump With Equipment Integration',
            'category_id': self.category.id,
            'is_medical_device': True,
            'create_maintenance_equipment': True,
        })
        equip_yes = self.env['maintenance.equipment'].search([('nhs_device_id', '=', device_with_equip.id)])
        self.assertTrue(equip_yes, "Equipment record should be automatically created when create_maintenance_equipment is True")
        self.assertEqual(equip_yes.category_id.name, 'Medical Device')
        self.assertEqual(equip_yes.team_id.name, 'NHS Technician Team')
        self.assertEqual(equip_yes.nhs_device_id, device_with_equip)

        # Enable option on existing device
        device_no_equip.write({'create_maintenance_equipment': True})
        equip_now = self.env['maintenance.equipment'].search([('nhs_device_id', '=', device_no_equip.id)])
        self.assertTrue(equip_now, "Equipment record should be created when option is toggled to True")

    def test_07_maintenance_request_generation_with_and_without_equipment(self):
        """Test overdue maintenance request creation linking equipment if present, or leaving it empty if disabled."""
        # Device A: has maintenance equipment
        device_a = self.Device.create({
            'name': 'Device A With Equipment',
            'category_id': self.category.id,
            'is_medical_device': True,
            'create_maintenance_equipment': True,
        })
        sched_a = device_a.schedule_ids[0]
        sched_a.last_done_date = Date.today() - relativedelta(months=14)
        sched_a._compute_next_due_date()

        # Device B: does NOT have maintenance equipment
        device_b = self.Device.create({
            'name': 'Device B Without Equipment',
            'category_id': self.category.id,
            'is_medical_device': True,
            'create_maintenance_equipment': False,
        })
        sched_b = device_b.schedule_ids[0]
        sched_b.last_done_date = Date.today() - relativedelta(months=14)
        sched_b._compute_next_due_date()

        equip_count_before = self.env['maintenance.equipment'].search_count([])

        # Run cron for overdue requests
        self.Schedule._cron_generate_maintenance_requests()

        # Verify Device A request
        req_a = self.MaintenanceRequest.search([('nhs_schedule_id', '=', sched_a.id)])
        self.assertTrue(req_a, "Request should be created for Device A")
        self.assertTrue(req_a.equipment_id, "Request for Device A should have equipment_id populated")
        self.assertEqual(req_a.equipment_id.nhs_device_id, device_a)

        # Verify Device B request
        req_b = self.MaintenanceRequest.search([('nhs_schedule_id', '=', sched_b.id)])
        self.assertTrue(req_b, "Request should be created for Device B")
        self.assertFalse(req_b.equipment_id, "Request for Device B should have empty equipment_id")

        equip_count_after = self.env['maintenance.equipment'].search_count([])
        self.assertEqual(equip_count_before, equip_count_after, "Cron should NOT create any new equipment records")

    def test_08_excel_export_selected_and_all(self):
        """Test excel export methods for selected devices and full register export wrapper."""
        device_1 = self.Device.create({
            'name': 'Export Device 1',
            'category_id': self.category.id,
            'acquisition_cost': 1500.0,
            'indicative_value': 1200.0,
        })
        device_2 = self.Device.create({
            'name': 'Export Device 2',
            'category_id': self.category.id,
            'acquisition_cost': 2500.0,
            'indicative_value': 2000.0,
        })

        # Export selected records (device_1 only)
        res_selected = device_1.action_export_register_excel()
        self.assertEqual(res_selected['type'], 'ir.actions.act_url')
        self.assertTrue('/web/content/' in res_selected['url'])

        # Export all active devices via wrapper
        res_all = self.Device.action_export_all_register_excel()
        self.assertEqual(res_all['type'], 'ir.actions.act_url')
        self.assertTrue('/web/content/' in res_all['url'])

    def test_09_no_hard_delete_archiving(self):
        """Test archive-on-delete policy, confirmation wizard, and cascading archive/unarchive."""
        # 1. Device creation and related records
        device = self.Device.create({
            'name': 'Cascade Test Device',
            'category_id': self.category.id,
            'create_maintenance_equipment': True,
        })
        dev_id = device.id

        # Create active child records
        schedule_active = self.env['nhs.device.schedule'].create({
            'device_id': dev_id,
            'schedule_type_id': self.schedule_type.id,
            'interval_months': 6,
        })
        schedule_pre_archived = self.env['nhs.device.schedule'].create({
            'device_id': dev_id,
            'schedule_type_id': self.schedule_type.id,
            'interval_months': 12,
            'active': False,  # Archived PRIOR to device archiving
        })
        service_active = self.env['nhs.device.service'].create({
            'device_id': dev_id,
            'service_type': 'ppm',
            'service_date': fields.Date.today(),
            'performed_by_id': self.env.user.id,
            'outcome': 'pass',
        })
        warranty_active = self.env['nhs.device.warranty'].create({
            'device_id': dev_id,
            'cover_type': 'warranty',
            'start_date': fields.Date.today(),
            'expiry_date': fields.Date.today(),
        })
        alert = self.env['nhs.device.alert'].create({
            'name': 'Cascade Alert',
            'reference': 'MHRA-TEST-100',
            'source': 'mhra',
        })
        alert_line_active = self.env['nhs.device.alert.line'].create({
            'alert_id': alert.id,
            'device_id': dev_id,
            'action_required': 'Check device',
        })

        # Verify initial active states
        self.assertTrue(device.active)
        self.assertTrue(schedule_active.active)
        self.assertFalse(schedule_pre_archived.active)
        self.assertTrue(service_active.active)
        self.assertTrue(warranty_active.active)
        self.assertTrue(alert_line_active.active)

        # 2. Call unlink() -> archives device directly & returns display_notification client action
        res_action = device.unlink()
        self.assertEqual(res_action['tag'], 'display_notification')
        self.assertIn('Nothing was permanently deleted', res_action['params']['message'])

        # 3. Verify cascading archive: device and active child records are archived
        self.assertFalse(device.active)
        self.assertFalse(schedule_active.active)
        self.assertEqual(schedule_active.archived_by_device_id.id, dev_id)
        self.assertFalse(service_active.active)
        self.assertEqual(service_active.archived_by_device_id.id, dev_id)
        self.assertFalse(warranty_active.active)
        self.assertEqual(warranty_active.archived_by_device_id.id, dev_id)
        self.assertFalse(alert_line_active.active)
        self.assertEqual(alert_line_active.archived_by_device_id.id, dev_id)

        # Verify shared/configuration records are EXCLUDED from cascade archiving
        self.assertTrue(self.category.active)
        self.assertTrue(self.schedule_type.active)

        # 4. Unarchive device -> restores auto-archived records, leaves pre-archived schedule untouched
        device.action_unarchive()
        self.assertTrue(device.active)
        self.assertTrue(schedule_active.active)
        self.assertFalse(schedule_active.archived_by_device_id)
        self.assertFalse(schedule_pre_archived.active, "Pre-archived schedule must remain archived")
        self.assertTrue(service_active.active)
        self.assertTrue(warranty_active.active)
        self.assertTrue(alert_line_active.active)
