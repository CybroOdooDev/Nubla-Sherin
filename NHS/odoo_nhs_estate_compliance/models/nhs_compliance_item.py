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
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import  timedelta
from dateutil.relativedelta import relativedelta

class NHSComplianceItem(models.Model):
    """Model to manage recurring statutory compliance items mapped to Odoo locations or equipment."""
    _name = 'nhs.compliance.item'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A statutory compliance obligation scheduled against a location/asset'
    _order = 'next_due_date, id'
    _rec_name = 'reference'

    name = fields.Char(string='Name', compute='_compute_name', store=True,
                       help='Auto-generated display name combining the compliance type and location.')
    reference = fields.Char(string='Reference', required=True, readonly=True, copy=False, default=lambda self: 'New',
                            help='Auto-generated unique sequence reference for this compliance item.')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                    default=lambda self: self.env.company,help='The company this compliance item belongs to.')
    compliance_type_id = fields.Many2one('nhs.compliance.type', string='Compliance Type', required=True,
                                         help='The type of statutory test or inspection this item schedules.')
    discipline_id = fields.Many2one('nhs.compliance.discipline', string='Discipline',
                                    related='compliance_type_id.discipline_id', store=True,
                                    help='The compliance discipline inherited from the compliance type.')
    site_id = fields.Many2one('nhs.estate.site', string='Site',
                              help='The NHS estate site where this compliance obligation applies.')
    building_id = fields.Many2one('nhs.estate.building', string='Building',
                                  domain="site_id and [('site_id', '=', site_id)] or []",
                                  help='The specific building within the site for this compliance obligation.')
    space_id = fields.Many2one('nhs.estate.space', string='Space',
        domain="building_id and [('building_id', '=', building_id)] or site_id and [('site_id', '=', site_id)] or []",
        help='The specific space or room within the building for this compliance obligation.')
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment',
                                   help='Optional specific asset (a named lift, calorifier, generator)')
    responsible_person_id = fields.Many2one('res.users', string='Responsible Person',
                                            compute='_compute_responsible_person_id',
                                            store=True, readonly=False,
                                            help='Person accountable for this item')
    delivery_method = fields.Selection([
        ('in_house', 'In-House Team'),
        ('contractor', 'External Contractor')
    ], string='Delivery Method', default='in_house',
       help='Whether the test is performed by in-house staff or an external contractor.')
    contractor_id = fields.Many2one('nhs.compliance.contractor', string='Contractor',
                                    domain="discipline_id and [('discipline_ids', 'in', discipline_id)] or []",
                                    help='Contractor delivering')
    frequency_value = fields.Integer(string='Frequency Value', required=True,
                                     help='The numeric interval between recurrences (e.g. 6 for every 6 months).')
    frequency_unit = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('year', 'Year')
    ], string='Frequency Unit', required=True,
       help='The time unit for the recurrence interval (day, week, month, or year).')
    lead_days = fields.Integer(string='Lead Days', store=True, readonly=False,
                        help='Number of days before the due date at which the item transitions to "due soon" status.')
    calendar_id = fields.Many2one('resource.calendar', string='Working Calendar',
                                  default=lambda self: self.env.company.resource_calendar_id,
                                  help='The working calendar used to adjust due dates to working days.')
    grace_days = fields.Integer(string='Grace Days', default=5,
                help='Number of days before the due date within which a completed test preserves the scheduled cycle.')
    last_completed_date = fields.Date(string='Last Completed Date',compute='_compute_last_completed_date', store=True,
                            readonly=False, help='The date of the most recent passing test for this compliance item.')
    next_due_date = fields.Date(string='Next Due Date', compute='_compute_next_due', store=True, readonly=False,
                                help='The calculated date on which the next test or inspection is due.')
    status = fields.Selection([
        ('compliant', 'Compliant'),
        ('due_soon', 'Due Soon'),
        ('overdue', 'Overdue'),
        ('failed', 'Failed'),
        ('not_applicable', 'Not Applicable')
    ], string='Status', compute='_compute_status', store=True, tracking=True,
       help='The current compliance status: Compliant, Due Soon, Overdue, Failed, or Not Applicable.')
    criticality = fields.Selection(related='compliance_type_id.criticality', store=True,
                                   help='The risk criticality level inherited from the compliance type.')
    test_ids = fields.One2many('nhs.compliance.test', 'item_id', string='Tests',
                              help='All compliance tests recorded against this item.')
    test_count = fields.Integer(string='Test Count', compute='_compute_test_count',
                                help='Total number of tests recorded for this compliance item.')
    remedial_ids = fields.One2many('nhs.compliance.remedial', 'item_id', string='Remedials',
                                  help='All remedial actions raised against this compliance item.')
    open_remedial_count = fields.Integer(string='Open Remedial', compute='_compute_open_remedial_count',
                                    help='Number of remedial actions that are still open (not completed or verified).')
    active = fields.Boolean(string='Active', default=True,
                            help='Uncheck to archive this compliance item without deleting it.')

    @api.onchange('compliance_type_id')
    def _onchange_compliance_type_id(self):
        """Pre-fill frequency and lead-day defaults from the selected compliance type."""
        for item in self:
            if item.compliance_type_id:
                item.frequency_value = item.compliance_type_id.default_frequency_value
                item.frequency_unit = item.compliance_type_id.default_frequency_unit
                item.lead_days = item.compliance_type_id.default_lead_days

    @api.onchange('compliance_type_id', 'discipline_id')
    def _onchange_discipline_id_set_contractor(self):
        """Auto-select a contractor when exactly one contractor exists for the chosen discipline."""
        for item in self:
            if item.discipline_id:
                contractors = self.env['nhs.compliance.contractor'].search(
                    [('discipline_ids', 'in', item.discipline_id.id)])
                if len(contractors) == 1:
                    item.contractor_id = contractors[0]
                elif item.contractor_id and item.contractor_id not in contractors:
                    item.contractor_id = False

    @api.onchange('site_id')
    def _onchange_site_id(self):
        """Clear building_id and space_id if they are no longer valid under the selected site."""
        for item in self:
            if item.site_id:
                if item.building_id and item.building_id.site_id != item.site_id:
                    item.building_id = False
                if item.space_id and item.space_id.site_id != item.site_id:
                    item.space_id = False
            else:
                item.building_id = False
                item.space_id = False

    @api.onchange('building_id')
    def _onchange_building_id(self):
        """Auto-populate site_id when building_id is selected, and clear invalid space_id."""
        for item in self:
            if item.building_id:
                if not item.site_id or item.site_id != item.building_id.site_id:
                    item.site_id = item.building_id.site_id
                if item.space_id and item.space_id.building_id != item.building_id:
                    item.space_id = False
            else:
                if item.space_id:
                    if item.site_id:
                        if item.space_id.site_id != item.site_id:
                            item.space_id = False

    @api.depends('discipline_id', 'site_id', 'building_id', 'compliance_type_id')
    def _compute_responsible_person_id(self):
        """Auto-assign a responsible person from duty assignments, prioritising location-specific matches."""
        for item in self:
            discipline = item.discipline_id
            if not discipline:
                if not item.responsible_person_id:
                    item.responsible_person_id = False
                continue
            domain = [
                ('discipline_id', '=', discipline.id),
                ('duty_role_id.code', 'in', ['RP', 'AP']),
            ]
            loc_conditions = []
            if item.building_id:
                loc_conditions.append(('building_id', '=', item.building_id.id))
            if item.site_id:
                loc_conditions.append(('site_id', '=', item.site_id.id))
            assignments = self.env['nhs.duty.assignment']
            if loc_conditions:
                if len(loc_conditions) == 2:
                    assignments = self.env['nhs.duty.assignment'].search(domain + ['|'] + loc_conditions)
                else:
                    assignments = self.env['nhs.duty.assignment'].search(domain + loc_conditions)
            if assignments:
                item.responsible_person_id = assignments[0].person_id
            else:
                all_assignments = self.env['nhs.duty.assignment'].search(domain)
                if all_assignments:
                    item.responsible_person_id = all_assignments[0].person_id
                else:
                    if not item.responsible_person_id:
                        item.responsible_person_id = False

    @api.depends('compliance_type_id', 'site_id', 'building_id', 'space_id')
    def _compute_name(self):
        """Build a display name from the compliance type name and the most specific location name."""
        for item in self:
            location = item.building_id.name or item.site_id.name or item.space_id.name or 'Unnamed'
            item.name = f"{item.compliance_type_id.name} — {location}"

    @api.depends('discipline_id.lead_days', 'compliance_type_id.default_lead_days')
    def _compute_lead_days(self):
        """Compute lead days from discipline, then compliance type, then the system default."""
        due_soon_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_estate_compliance.due_soon_days', 14))
        for item in self:
            if item.discipline_id and item.discipline_id.lead_days:
                item.lead_days = item.discipline_id.lead_days
            elif item.compliance_type_id and item.compliance_type_id.default_lead_days:
                item.lead_days = item.compliance_type_id.default_lead_days
            else:
                item.lead_days = due_soon_days

    def _adjust_to_working_day(self, date_val):
        """Shift a date forward to the next working day according to the item's working calendar."""
        if not date_val or not self.calendar_id:
            return date_val
        import pytz
        from datetime import time, datetime
        calendar = self.calendar_id
        tz = pytz.timezone(calendar.tz or 'UTC')
        current_date = date_val
        for _ in range(30):
            start_dt = tz.localize(datetime.combine(current_date, time.min))
            end_dt = tz.localize(datetime.combine(current_date, time.max))
            intervals = calendar._work_intervals_batch(start_dt, end_dt)[False]
            if intervals:
                return current_date
            current_date += timedelta(days=1)
        return date_val

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-generate a sequence reference, apply type defaults, and sync maintenance records."""
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                seq = self.env['ir.sequence'].next_by_code('nhs.compliance.item') or 'New'
                vals['reference'] = seq
            if vals.get('compliance_type_id'):
                comp_type = self.env['nhs.compliance.type'].browse(vals['compliance_type_id'])
                if comp_type:
                    if not vals.get('frequency_value'):
                        vals['frequency_value'] = comp_type.default_frequency_value or 1
                    if not vals.get('frequency_unit'):
                        vals['frequency_unit'] = comp_type.default_frequency_unit or 'month'
                    if 'lead_days' not in vals or vals.get('lead_days') is False:
                        due_soon_days = int(
                            self.env['ir.config_parameter'].sudo().get_param(
                                'odoo_nhs_estate_compliance.due_soon_days', 14))
                        vals['lead_days'] = comp_type.default_lead_days or due_soon_days
        items = super(NHSComplianceItem, self).create(vals_list)
        items._sync_maintenance_records()
        return items

    def write(self, vals):
        """Override write to re-sync linked maintenance records when key scheduling or location fields change."""
        res = super(NHSComplianceItem, self).write(vals)
        if not self.env.context.get('skip_maintenance_sync'):
            if any(field in vals for field in
                   ['name', 'active', 'next_due_date', 'frequency_value', 'frequency_unit', 'responsible_person_id',
                 'site_id', 'building_id', 'space_id', 'compliance_type_id', 'discipline_id', 'equipment_id','status']):
                self._sync_maintenance_records()
        return res

    def _sync_maintenance_records(self):
        """Create or update maintenance requests based on compliance item status"""
        team = self.env['maintenance.team'].sudo().search([('name', '=', 'Compliance Team')], limit=1)
        if not team:
            team = self.env['maintenance.team'].sudo().create({
                'name': 'Compliance Team',
                'company_id': False,
            })
        new_request_stage = self.env['maintenance.stage'].search([('name', 'ilike', 'New Request')], limit=1)
        in_progress_stage = self.env['maintenance.stage'].search([('name', 'ilike', 'In Progress')], limit=1)
        repaired_stage = self.env['maintenance.stage'].search([('name', 'ilike', 'Repaired')], limit=1)
        scrap_stage = self.env['maintenance.stage'].search([('name', 'ilike', 'Scrap')], limit=1)
        for item in self:
            if not item.active:
                continue
            equipment = item.equipment_id
            if not equipment:
                continue
            open_requests = self.env['maintenance.request'].search([
                ('equipment_id', '=', equipment.id),
                ('stage_id.done', '=', False),
                ('compliance_item_id', '=', item.id),
            ])
            open_remedials = item.remedial_ids.filtered(
                lambda r: r.state not in ['completed', 'verified', 'cancelled']
            )
            item_identifier = item.reference or item.name
            if open_remedials:
                if open_requests:
                    open_requests.with_context(skip_maintenance_sync=True).write({
                        'stage_id': in_progress_stage.id,
                        'schedule_date': False,
                        'priority': '3',
                        'description': f"BLOCKED: Open remedials exist.\n\n"
                                       f"Compliance Item: {item_identifier}\n"
                                       f"Discipline: {item.discipline_id.name}\n"
                                       f"Open Remedials: {', '.join(open_remedials.mapped('name'))}",
                        'maintenance_team_id': team.id,
                    })
                else:
                    request_name = f"BLOCKED: {item_identifier}"
                    existing_request = self.env['maintenance.request'].search([
                        ('name', '=', request_name),
                        ('equipment_id', '=', equipment.id),
                        ('compliance_item_id', '=', item.id),
                    ], limit=1)
                    if existing_request:
                        print("4. existing request - ",existing_request)
                        existing_request.with_context(skip_maintenance_sync=True).write({
                            'stage_id': in_progress_stage.id,
                            'schedule_date': False,
                            'priority': '3',
                            'description': f"BLOCKED: Open remedials exist.\n\n"
                                           f"Compliance Item: {item_identifier}\n"
                                           f"Discipline: {item.discipline_id.name}\n"
                                           f"Open Remedials: {', '.join(open_remedials.mapped('name'))}",
                            'maintenance_team_id': team.id,
                        })
                    else:
                        self.env['maintenance.request'].with_context(skip_maintenance_sync=True).create({
                            'name': request_name,
                            'equipment_id': equipment.id,
                            'maintenance_type': 'preventive',
                            'recurring_maintenance': True,
                            'repeat_interval': item.frequency_value or 1,
                            'repeat_unit': item.frequency_unit or 'month',
                            'schedule_date': False,
                            'company_id': item.company_id.id,
                            'compliance_item_id': item.id,
                            'user_id': item.responsible_person_id.id if item.responsible_person_id else False,
                            'stage_id': in_progress_stage.id,
                            'priority': '3',
                            'description': f"BLOCKED: Open remedials exist.\n\n"
                                           f"Compliance Item: {item_identifier}\n"
                                           f"Discipline: {item.discipline_id.name}\n"
                                           f"Open Remedials: {', '.join(open_remedials.mapped('name'))}",
                            'maintenance_team_id': team.id,
                        })
                continue
            if item.status == 'not_applicable':
                if open_requests:
                    open_requests.with_context(skip_maintenance_sync=True).write({
                        'stage_id': repaired_stage.id if repaired_stage else scrap_stage.id,
                        'close_date': fields.Date.today(),
                        'maintenance_team_id': team.id,
                    })
                continue
            if item.status in ['compliant', 'due_soon']:
                stage = new_request_stage
                priority = '1'
                name_prefix = "Statutory Test"
                description = (f"Scheduled statutory compliance test.\n"
                               f"\nCompliance Item: {item_identifier}"
                               f"\nDiscipline: {item.discipline_id.name}"
                               f"\nType: {item.compliance_type_id.name}"
                               f"\nDue: {item.next_due_date or 'Immediate'}")
                schedule_date = item.next_due_date or fields.Date.today()
            elif item.status == 'overdue':
                stage = new_request_stage
                priority = '3'
                name_prefix = "OVERDUE"
                days_overdue = (fields.Date.today() - item.next_due_date).days if item.next_due_date else 0
                description = (f"OVERDUE STATUTORY TEST!\n"
                               f"\nCompliance Item: {item_identifier}"
                               f"\nDiscipline: {item.discipline_id.name}"
                               f"\nType: {item.compliance_type_id.name}"
                               f"\nDue: {item.next_due_date or 'Immediate'}"
                               f"\nDays Overdue: {days_overdue}")
                schedule_date = fields.Date.today()
            elif item.status == 'failed':
                stage = new_request_stage
                priority = '3'
                name_prefix = "FAILED"
                description = (f"FAILED STATUTORY TEST!\n"
                               f"\nCompliance Item: {item_identifier}"
                               f"\nDiscipline: {item.discipline_id.name}"
                               f"\nType: {item.compliance_type_id.name}\n"
                               f"\nFAILURE DETECTED - Remedial action required before re-testing.")
                schedule_date = fields.Date.today()
            else:
                stage = new_request_stage
                priority = '1'
                name_prefix = "Statutory Test"
                description = (f"Statutory compliance test.\n"
                               f"\nCompliance Item: {item_identifier}"
                               f"\nDiscipline: {item.discipline_id.name}"
                               f"\nType: {item.compliance_type_id.name}")
                schedule_date = item.next_due_date or fields.Date.today()
            request_name = f"{name_prefix}: {item_identifier}"
            request_vals = {
                'stage_id': stage.id if stage else False,
                'maintenance_type': 'preventive',
                'priority': priority,
                'schedule_date': schedule_date,
                'description': description,
                'user_id': item.responsible_person_id.id if item.responsible_person_id else False,
                'recurring_maintenance': True,
                'repeat_interval': item.frequency_value or 1,
                'repeat_unit': item.frequency_unit or 'month',
                'maintenance_team_id': team.id,
            }
            if open_requests:
                update_vals = request_vals.copy()
                if not open_requests[0].name.startswith(name_prefix):
                    update_vals['name'] = request_name
                open_requests.with_context(skip_maintenance_sync=True).write(update_vals)
            else:
                existing_request = self.env['maintenance.request'].search([
                    ('name', '=', request_name),
                    ('equipment_id', '=', equipment.id),
                    ('compliance_item_id', '=', item.id),
                ], limit=1)
                if existing_request:
                    if existing_request.stage_id.id in [repaired_stage.id, scrap_stage.id]:
                        existing_requests_count = self.env['maintenance.request'].search_count([
                            ('name', 'ilike', f"{name_prefix}: {item_identifier}"),
                            ('equipment_id', '=', equipment.id),
                            ('compliance_item_id', '=', item.id),
                        ])
                        new_name = f"{name_prefix}: {item_identifier} ({existing_requests_count + 1})"
                        request_vals.update({
                            'name': new_name,
                            'equipment_id': equipment.id,
                            'company_id': item.company_id.id,
                            'compliance_item_id': item.id,
                        })
                        self.env['maintenance.request'].with_context(skip_maintenance_sync=True).create(request_vals)
                    else:
                        existing_request.with_context(skip_maintenance_sync=True).write(request_vals)
                else:
                    request_vals.update({
                        'name': request_name,
                        'equipment_id': equipment.id,
                        'company_id': item.company_id.id,
                        'compliance_item_id': item.id,
                    })
                    self.env['maintenance.request'].with_context(skip_maintenance_sync=True).create(request_vals)

    @api.depends('test_ids', 'test_ids.test_date', 'test_ids.outcome', 'test_ids.active')
    def _compute_last_completed_date(self):
        """
        Compute last_completed_date from the most recent test (by test_date)
        Only considers PASS or PASS_WITH_OBSERVATIONS outcomes
        """
        for item in self:
            passing_tests = item.test_ids.filtered(
                lambda t: t.active and
                          t.outcome in ['pass', 'pass_with_observations'] and
                          t.test_date
            )
            if passing_tests:
                sorted_tests = passing_tests.sorted('test_date', reverse=True)
                if sorted_tests:
                    latest_test = sorted_tests[0]
                    if latest_test and latest_test.test_date:
                        if item.last_completed_date != latest_test.test_date:
                            item.last_completed_date = latest_test.test_date
            else:
                pass

    @api.depends('last_completed_date', 'frequency_value', 'frequency_unit', 'calendar_id', 'test_ids')
    def _compute_next_due(self):
        """Compute the next due date by adding the frequency interval to the last completed date
         and adjusting for working days."""
        for item in self:
            if item.last_completed_date:
                if item.frequency_unit == 'day':
                    delta = timedelta(days=item.frequency_value)
                elif item.frequency_unit == 'week':
                    delta = timedelta(weeks=item.frequency_value)
                elif item.frequency_unit == 'month':
                    delta = relativedelta(months=item.frequency_value)
                elif item.frequency_unit == 'year':
                    delta = relativedelta(years=item.frequency_value)
                else:
                    delta = relativedelta(months=1)
                raw_due_date = item.last_completed_date + delta
                item.next_due_date = item._adjust_to_working_day(raw_due_date)
            else:
                if not item.next_due_date:
                    item.next_due_date = False

    @api.depends('next_due_date', 'lead_days', 'test_ids.outcome', 'test_ids.test_date', 'test_ids.active', 'active',
                 'compliance_type_id', 'site_id', 'building_id', 'space_id')
    def _compute_status(self):
        """Determine the compliance status based on the latest test outcome, next due date, and lead days."""
        today = fields.Date.today()
        for item in self:
            if not item.active:
                item.status = 'not_applicable'
                continue
            if not item.compliance_type_id or not (item.site_id or item.building_id or item.space_id):
                item.status = 'not_applicable'
                continue
            active_tests = item.test_ids.filtered(lambda t: t.active and t.test_date)
            if active_tests:
                sorted_tests = active_tests.sorted('test_date', reverse=True)
                if sorted_tests:
                    latest_test = sorted_tests[0]
                    if latest_test and latest_test.outcome in ['fail', 'remedial_required']:
                        item.status = 'failed'
                        continue
            if not item.next_due_date:
                if active_tests:
                    item.status = 'not_applicable'
                else:
                    item.status = 'overdue'
                continue
            if item.next_due_date < today:
                item.status = 'overdue'
            elif (item.next_due_date - today).days <= item.lead_days:
                item.status = 'due_soon'
            else:
                item.status = 'compliant'

    def _compute_test_count(self):
        """Compute the total number of tests recorded for this compliance item."""
        for item in self:
            item.test_count = len(item.test_ids)

    def _compute_open_remedial_count(self):
        """Compute the count of remedial actions that have not been completed or verified."""
        for item in self:
            item.open_remedial_count = len(item.remedial_ids.filtered(
                lambda r: r.state not in ['completed', 'verified']
            ))

    @api.constrains('site_id', 'building_id', 'space_id')
    def _check_location(self):
        """Validate that at least one location level (site, building, or space) is set."""
        for item in self:
            if not any([item.site_id, item.building_id, item.space_id]):
                raise ValidationError('At least one location level (site, building, or space) must be set.')

    def action_log_test(self):
        """Open a popup form to log a new compliance test against this item."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log Test',
            'res_model': 'nhs.compliance.test',
            'view_mode': 'form',
            'context': {
                'default_item_id': self.id,
                'default_test_date': fields.Date.today(),
            },
            'target': 'new',
        }

    def action_log_remedial(self):
        """Open a popup form to log a new compliance remedial against this item."""
        failed_tests = self.test_ids.filtered(
            lambda t: t.outcome not in ['pass', 'pass_with_observations'])
        if not failed_tests:
            raise ValidationError('No failed tests found for this compliance item.')
        due_date = fields.Date.today() + relativedelta(days=10)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log Test',
            'res_model': 'nhs.compliance.remedial',
            'view_mode': 'form',
            'context': {
                'default_item_id': self.id,
                'default_due_date': due_date,
            },
            'target': 'new',
        }

    def action_view_history(self):
        """Open a list/form view of the full test history for this compliance item."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Test History',
            'res_model': 'nhs.compliance.test',
            'view_mode': 'list,form',
            'domain': [('item_id', '=', self.id)],
            'context': {'default_item_id': self.id},
        }

    def action_view_maintenance(self):
        """Open a list/form view of maintenance requests linked to this compliance item."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance',
            'res_model': 'maintenance.request',
            'view_mode': 'list,form',
            'domain': [('compliance_item_id', '=', self.id)],
            'context': {'default_compliance_item_id': self.id},
        }

    def action_view_compliance_remedial(self):
        """Open a list/form view of open remedial actions for this compliance item."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Remedial Actions',
            'res_model': 'nhs.compliance.remedial',
            'view_mode': 'list,form',
            'domain': [('item_id', '=', self.id), ('state', 'not in', ['completed', 'verified'])],
            'context': {'default_item_id': self.id},
        }

    def action_compute_status(self):
        """Manually trigger a recomputation of the compliance status."""
        self._compute_status()

    @api.model
    def _send_reminders(self):
        """Scheduled action to send email reminders for due-soon and overdue items and create to-do activities."""
        due_soon_template = self.env.ref('odoo_nhs_estate_compliance.mail_template_compliance_due_soon',
                                         raise_if_not_found=False)
        if due_soon_template:
            due_soon_items = self.search([('status', '=', 'due_soon'), ('responsible_person_id', '!=', False)])
            for item in due_soon_items:
                due_soon_template.send_mail(item.id, force_send=True)
        overdue_template = self.env.ref('odoo_nhs_estate_compliance.mail_template_compliance_overdue',
                                        raise_if_not_found=False)
        if overdue_template:
            overdue_items = self.search([('status', '=', 'overdue'), ('responsible_person_id', '!=', False)])
            for item in overdue_items:
                overdue_template.send_mail(item.id, force_send=True)
        for item in self.search([('status', 'in', ['due_soon', 'overdue']), ('responsible_person_id', '!=', False)]):
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'nhs.compliance.item'),
                ('res_id', '=', item.id),
                ('user_id', '=', item.responsible_person_id.id),
            ])
            if not existing:
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id if activity_type else False,
                    'res_model_id': self.env['ir.model']._get_id('nhs.compliance.item'),
                    'res_id': item.id,
                    'user_id': item.responsible_person_id.id,
                    'summary': f"Compliance Item {item.reference} is {item.status.upper()}",
                    'note': f"Please complete the test for {item.name}. Due on {item.next_due_date}.",
                    'date_deadline': item.next_due_date or fields.Date.today() + timedelta(days=14),
                })

    @api.model
    def _escalate_overdue(self):
        """Scheduled action to escalate compliance items overdue beyond the configurable threshold to Duty Holders."""
        self.env['nhs.compliance.remedial']._check_overdue_remedials()
        threshold = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_estate_compliance.escalation_threshold', 30))
        today = fields.Date.today()
        overdue_limit = today - timedelta(days=threshold)
        items_to_escalate = self.search([
            ('status', '=', 'overdue'),
            ('next_due_date', '<', overdue_limit)
        ])
        if not items_to_escalate:
            return
        template = self.env.ref('odoo_nhs_estate_compliance.mail_template_compliance_escalation',
                                raise_if_not_found=False)
        dh_assignments = self.env['nhs.duty.assignment'].search([('duty_role_id.code', '=', 'DH')])
        dh_users = dh_assignments.mapped('person_id') or self.env.user
        dh_emails = ",".join([u.email for u in dh_users if u.email])
        for item in items_to_escalate:
            item.message_post(body=(
                "ESCALATION ALERT: This item has been overdue for more than %s days (Due: %s). "
                "Escalating to Duty Holder.", threshold, item.next_due_date
            ))
            if template:
                email_to = dh_emails or (item.responsible_person_id.email if item.responsible_person_id else '')
                if email_to:
                    template.send_mail(item.id, email_values={'email_to': email_to}, force_send=True)
            for dh_user in dh_users:
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'nhs.compliance.item'),
                    ('res_id', '=', item.id),
                    ('user_id', '=', dh_user.id),
                    ('summary', '=', f"CRITICAL ESCALATION: Item {item.reference} overdue > {threshold} days"),
                ])
                if not existing:
                    activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                    self.env['mail.activity'].create({
                        'activity_type_id': activity_type.id if activity_type else False,
                        'res_model_id': self.env['ir.model']._get_id('nhs.compliance.item'),
                        'res_id': item.id,
                        'user_id': dh_user.id,
                        'summary': f"CRITICAL ESCALATION: Item {item.reference} overdue - {threshold} days",
                        'note':f"The compliance item {item.name} is critically overdue (Due since {item.next_due_date})."
                               f" Please resolve immediately.",
                        'date_deadline': today,
                    })

    @api.model
    def _send_weekly_digest(self):
        """Send a weekly email digest summarising overall compliance status to configured recipients or Duty Holders."""
        recipients = self.env['ir.config_parameter'].sudo().get_param('odoo_nhs_estate_compliance.digest_recipients')
        if not recipients:
            dh_assignments = self.env['nhs.duty.assignment'].search([('duty_role_id.code', '=', 'DH')])
            emails = dh_assignments.mapped('person_id.email')
            recipients = ",".join([e for e in emails if e]) or self.env.company.email or 'admin@example.com'
        today = fields.Date.today()
        total_items = self.search_count([('active', '=', True)])
        compliant_count = self.search_count([('status', '=', 'compliant'), ('active', '=', True)])
        due_soon_count = self.search_count([('status', '=', 'due_soon'), ('active', '=', True)])
        overdue_count = self.search_count([('status', '=', 'overdue'), ('active', '=', True)])
        failed_count = self.search_count([('status', '=', 'failed'), ('active', '=', True)])
        compliance_rate = (compliant_count / total_items * 100.0) if total_items else 0.0
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    color: #333;
                    line-height: 1.6;
                    background-color: #f5f7fa;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 700px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: #1a237e;
                    color: white;
                    padding: 25px 30px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 22px;
                    font-weight: 600;
                }}
                .header .subtitle {{
                    margin: 5px 0 0 0;
                    opacity: 0.85;
                    font-size: 14px;
                }}
                .content {{
                    padding: 25px 30px;
                }}
                .summary-grid {{
                    display: flex;
                    gap: 10px;
                    margin: 15px 0 20px 0;
                }}
                .summary-card {{
                    flex: 1;
                    padding: 12px 10px;
                    text-align: center;
                    border-radius: 6px;
                    background: #f8f9fa;
                    border-top: 3px solid #6c757d;
                }}
                .summary-card.total {{ border-top-color: #1976d2; background: #e3f2fd; }}
                .summary-card.compliant {{ border-top-color: #2e7d32; background: #e8f5e9; }}
                .summary-card.due-soon {{ border-top-color: #f57c00; background: #fff3e0; }}
                .summary-card.overdue {{ border-top-color: #c62828; background: #ffebee; }}
                .summary-card.failed {{ border-top-color: #d32f2f; background: #fce4ec; }}
                .summary-card .number {{
                    font-size: 24px;
                    font-weight: bold;
                    display: block;
                }}
                .summary-card .label {{
                    font-size: 12px;
                    color: #555;
                }}
                .compliance-bar {{
                    background: #e9ecef;
                    border-radius: 6px;
                    padding: 3px;
                    margin: 5px 0 15px 0;
                    height: 22px;
                }}
                .compliance-bar .fill {{
                    background: #2e7d32;
                    height: 100%;
                    border-radius: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    min-width: 40px;
                    width: {compliance_rate:.0f}%;
                }}
                .compliance-bar .fill.low {{ background: #c62828; }}
                .compliance-bar .fill.medium {{ background: #f57c00; }}
                .login-link {{
                    display: block;
                    text-align: center;
                    margin: 25px 0 10px 0;
                    padding: 12px;
                    background: #e8eaf6;
                    border-radius: 6px;
                }}
                .login-link a {{
                    color: #1a237e;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 15px;
                }}
                .login-link a:hover {{
                    text-decoration: underline;
                }}
                .footer {{
                    padding: 15px 30px;
                    background: #f8f9fa;
                    text-align: center;
                    font-size: 12px;
                    color: #999;
                    border-top: 1px solid #e8eaf6;
                }}
                @media only screen and (max-width: 600px) {{
                    .summary-grid {{
                        flex-direction: column;
                    }}
                    .content {{
                        padding: 15px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ Estates Compliance Weekly Report</h1>
                    <div class="subtitle">Week Ending {today.strftime('%B %d, %Y')}</div>
                </div>

                <div class="content">
                    <!-- Compliance Rate Bar -->
                    <div style="margin-bottom: 5px;">
                        <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 500;">
                            <span>Overall Compliance Rate : </span>
                            <span>{compliance_rate:.0f}%</span>
                        </div>
                        <div class="compliance-bar">
                            <div class="fill {('low' if compliance_rate < 60 else 'medium' if compliance_rate < 80 
                                    else '')}" 
                                 style="width: {compliance_rate:.0f}%;">
                                {compliance_rate:.0f}%
                            </div>
                        </div>
                    </div>

                    <!-- Summary Cards -->
                    <div class="summary-grid">
                        <div class="summary-card total">
                            <span class="number">{total_items}</span>
                            <span class="label">Total Items</span>
                        </div>
                        <div class="summary-card compliant">
                            <span class="number">{compliant_count}</span>
                            <span class="label">✅ Compliant</span>
                        </div>
                        <div class="summary-card due-soon">
                            <span class="number">{due_soon_count}</span>
                            <span class="label">⏰ Due Soon</span>
                        </div>
                        <div class="summary-card overdue">
                            <span class="number">{overdue_count}</span>
                            <span class="label">🚨 Overdue</span>
                        </div>
                        <div class="summary-card failed">
                            <span class="number">{failed_count}</span>
                            <span class="label">❌ Failed</span>
                        </div>
                    </div>

                    <!-- Login Link -->
                    <div class="login-link">
                        <a href="{base_url}/web">🔑 Log in to Odoo to view detailed compliance records</a>
                    </div>
                </div>

                <div class="footer">
                    Estates Compliance System • Automated Report • {today.strftime('%B %d, %Y')}
                </div>
            </div>
        </body>
        </html>
        """

        mail_values = {
            'email_to': recipients,
            'subject': f"Estates Compliance Weekly Digest - {today.strftime('%Y-%m-%d')}",
            'body_html': html_body,
        }

        self.env['mail.mail'].sudo().create(mail_values).send()

    @api.model
    def get_compliance_dashboard_metrics(self):
        """Return aggregated compliance metrics for the redesigned client-side dashboard.
        Computes overall compliance rate, KPIs, breakdowns by discipline/site/building,
        overdue register, due-soon planner, failed tests, open remedials,
        month-on-month trend data, upcoming inspections, expiring certificates,
        recently added compliance items, critical alerts, and a RAG heat-map matrix.
        """
        import calendar as cal
        from dateutil.relativedelta import relativedelta
        today = fields.Date.today()
        start_of_month = today.replace(day=1)
        last_day = cal.monthrange(today.year, today.month)[1]
        end_of_month = today.replace(day=last_day)
        thirty_days_later = today + timedelta(days=30)
        active_items = self.search([('active', '=', True)])
        active_schedules = len(active_items)
        equip_count = len(active_items.mapped('equipment_id'))
        site_count = len(active_items.mapped('site_id'))
        building_count = len(active_items.mapped('building_id'))
        space_count = len(active_items.mapped('space_id'))
        total_assets_locations = equip_count + building_count + space_count + site_count
        tests_due_this_month = self.search_count([
            ('active', '=', True),
            ('next_due_date', '>=', start_of_month),
            ('next_due_date', '<=', end_of_month)
        ])
        overdue_tests = self.search_count([
            ('active', '=', True),
            ('status', '=', 'overdue')
        ])
        completed_this_month = self.env['nhs.compliance.test'].search_count([
            ('active', '=', True),
            ('test_date', '>=', start_of_month),
            ('test_date', '<=', end_of_month)
        ])
        upcoming_tests_30_days = self.search_count([
            ('active', '=', True),
            ('next_due_date', '>=', today),
            ('next_due_date', '<=', thirty_days_later)
        ])
        open_remedials_count = self.env['nhs.compliance.remedial'].search_count([
            ('state', 'in', ['open', 'in_progress'])
        ])
        expiring_certificates = self.env['nhs.compliance.test'].search_count([
            ('active', '=', True),
            ('certificate_expiry', '>=', today),
            ('certificate_expiry', '<=', thirty_days_later)
        ])
        compliant_items = self.search_count([('status', '=', 'compliant'), ('active', '=', True)])
        compliance_rate = (compliant_items / active_schedules * 100.0) if active_schedules else 100.0
        status_overview = {
            'compliant': compliant_items,
            'due_soon': self.search_count([('status', '=', 'due_soon'), ('active', '=', True)]),
            'overdue': overdue_tests,
            'failed': self.search_count([('status', '=', 'failed'), ('active', '=', True)]),
            'not_applicable': self.search_count([('status', '=', 'not_applicable'), ('active', '=', True)]),
        }
        tests = self.env['nhs.compliance.test'].search([('active', '=', True)])
        from collections import defaultdict
        type_counts = defaultdict(int)
        type_names = {}
        for t in tests:
            comp_type = t.item_id.compliance_type_id
            if comp_type:
                type_counts[comp_type.id] += 1
                type_names[comp_type.id] = comp_type.name
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:6]
        tests_by_type = [{'id': k, 'name': type_names[k], 'count': v} for k, v in sorted_types]
        trend_over_time = []
        for i in range(5, -1, -1):
            m_start = start_of_month - relativedelta(months=i)
            m_last_day = cal.monthrange(m_start.year, m_start.month)[1]
            m_end = m_start.replace(day=m_last_day)
            completed = self.env['nhs.compliance.test'].search_count([
                ('active', '=', True),
                ('test_date', '>=', m_start),
                ('test_date', '<=', m_end)
            ])
            overdue = self.search_count([
                ('active', '=', True),
                ('next_due_date', '>=', m_start),
                ('next_due_date', '<=', m_end),
                ('status', '=', 'overdue')
            ])
            trend_over_time.append({
                'month': m_start.strftime('%b %Y'),
                'completed': completed,
                'overdue': overdue,
                'start_date': m_start.strftime('%Y-%m-%d'),
                'end_date': m_end.strftime('%Y-%m-%d')
            })
        upcoming_by_month = []
        for i in range(12):
            m_start = today.replace(day=1) + relativedelta(months=i)
            m_last_day = cal.monthrange(m_start.year, m_start.month)[1]
            m_end = m_start.replace(day=m_last_day)
            count = self.search_count([
                ('active', '=', True),
                ('next_due_date', '>=', m_start),
                ('next_due_date', '<=', m_end)
            ])
            upcoming_by_month.append({
                'month': m_start.strftime('%b %Y'),
                'count': count,
                'start_date': m_start.strftime('%Y-%m-%d'),
                'end_date': m_end.strftime('%Y-%m-%d')
            })
        cert_expirings = []
        for i in range(12):
            m_start = today.replace(day=1) + relativedelta(months=i)
            m_last_day = cal.monthrange(m_start.year, m_start.month)[1]
            m_end = m_start.replace(day=m_last_day)
            count = self.env['nhs.compliance.test'].search_count([
                ('active', '=', True),
                ('certificate_expiry', '>=', m_start),
                ('certificate_expiry', '<=', m_end)
            ])
            cert_expirings.append({
                'month': m_start.strftime('%b %Y'),
                'count': count,
                'start_date': m_start.strftime('%Y-%m-%d'),
                'end_date': m_end.strftime('%Y-%m-%d')
            })
        sites = self.env['nhs.estate.site'].search([])
        site_tasks = []
        site_compliance = []
        for s in sites:
            count = self.search_count([('site_id', '=', s.id), ('active', '=', True)])
            if count > 0:
                site_tasks.append({
                    'id': s.id,
                    'name': s.name,
                    'count': count
                })
                compliant = self.search_count([('site_id', '=', s.id), ('status', '=', 'compliant'),
                                               ('active', '=', True)])
                rate = (compliant / count * 100.0)
                site_compliance.append({
                    'id': s.id,
                    'name': s.name,
                    'rate': round(rate, 1)
                })
        buildings = self.env['nhs.estate.building'].search([])
        building_tasks = []
        for b in buildings:
            count = self.search_count([('building_id', '=', b.id), ('active', '=', True)])
            if count > 0:
                building_tasks.append({
                    'id': b.id,
                    'name': b.name,
                    'count': count
                })
        recent_completed_tests = []
        for t in self.env['nhs.compliance.test'].search([
            ('active', '=', True),
            ('outcome', 'in', ['pass', 'pass_with_observations'])
        ], order='test_date desc, id desc', limit=3):
            recent_completed_tests.append({
                'id': t.id,
                'name': t.name,
                'item_name': t.item_id.name,
                'test_date': t.test_date.strftime('%Y-%m-%d') if t.test_date else '',
                'outcome': t.outcome,
            })
        recent_failed_tests = []
        for t in self.env['nhs.compliance.test'].search([
            ('active', '=', True),
            ('outcome', 'in', ['fail', 'remedial_required'])
        ], order='test_date desc, id desc', limit=3):
            recent_failed_tests.append({
                'id': t.id,
                'name': t.name,
                'item_name': t.item_id.name,
                'test_date': t.test_date.strftime('%Y-%m-%d') if t.test_date else '',
                'outcome': t.outcome,
            })
        upcoming_inspections = []
        for item in self.search([
            ('active', '=', True),
            ('next_due_date', '>=', today)
        ], order='next_due_date asc, id asc', limit=3):
            upcoming_inspections.append({
                'id': item.id,
                'reference': item.reference,
                'name': item.name,
                'next_due_date': item.next_due_date.strftime('%Y-%m-%d') if item.next_due_date else '',
                'responsible': item.responsible_person_id.name or '',
            })
        recently_added_assets = []
        for item in self.search([
            ('active', '=', True)
        ], order='create_date desc, id desc', limit=3):
            recently_added_assets.append({
                'id': item.id,
                'reference': item.reference,
                'name': item.name,
                'create_date': item.create_date.strftime('%Y-%m-%d') if item.create_date else '',
                'location': item.building_id.name or item.site_id.name or item.space_id.name or '',
            })
        critical_alerts = []
        for item in self.search([
            ('active', '=', True),
            ('status', '=', 'overdue'),
            ('criticality', 'in', ['life_safety', 'high'])
        ], order='next_due_date asc, id asc', limit=3):
            critical_alerts.append({
                'id': item.id,
                'reference': item.reference,
                'name': item.name,
                'next_due_date': item.next_due_date.strftime('%Y-%m-%d') if item.next_due_date else '',
                'criticality': item.criticality,
            })
        disciplines = self.env['nhs.compliance.discipline'].search([])
        rag_matrix = []
        for b in buildings:
            row = {
                'building_id': b.id,
                'building_name': b.name,
                'cells': []
            }
            for d in disciplines:
                total = self.search_count([
                    ('building_id', '=', b.id),
                    ('discipline_id', '=', d.id),
                    ('active', '=', True)
                ])
                compliant = self.search_count([
                    ('building_id', '=', b.id),
                    ('discipline_id', '=', d.id),
                    ('status', '=', 'compliant'),
                    ('active', '=', True)
                ])
                if total == 0:
                    cell_val = 'N/A'
                    cell_class = 'bg-light text-muted'
                    rate = -1
                else:
                    rate = (compliant / total * 100.0)
                    if rate < 70.0:
                        cell_val = f"{rate:.0f}%"
                        cell_class = 'bg-danger text-white fw-bold'
                    elif rate < 90.0:
                        cell_val = f"{rate:.0f}%"
                        cell_class = 'bg-warning text-dark fw-bold'
                    else:
                        cell_val = f"{rate:.0f}%"
                        cell_class = 'bg-success text-white fw-bold'
                row['cells'].append({
                    'discipline_id': d.id,
                    'discipline_name': d.name,
                    'value': cell_val,
                    'class': cell_class,
                    'total': total,
                    'rate': round(rate, 1)
                })
            rag_matrix.append(row)
        return {
            'overall_compliance_rate': round(compliance_rate, 1),
            'total_assets_locations': total_assets_locations,
            'active_schedules': active_schedules,
            'tests_due_this_month': tests_due_this_month,
            'overdue_tests': overdue_tests,
            'completed_this_month': completed_this_month,
            'upcoming_tests_30_days': upcoming_tests_30_days,
            'open_remedials_count': open_remedials_count,
            'expiring_certificates': expiring_certificates,
            'status_overview': status_overview,
            'tests_by_type': tests_by_type,
            'trend_over_time': trend_over_time,
            'upcoming_by_month': upcoming_by_month,
            'cert_expirings': cert_expirings,
            'site_tasks': site_tasks,
            'site_compliance': site_compliance,
            'building_tasks': building_tasks,
            'recent_completed_tests': recent_completed_tests,
            'recent_failed_tests': recent_failed_tests,
            'upcoming_inspections': upcoming_inspections,
            'recently_added_assets': recently_added_assets,
            'critical_alerts': critical_alerts,
            'rag_matrix': rag_matrix,
            'discipline_headers': [{'id': d.id, 'name': d.name} for d in disciplines]
        }

    def unlink(self):
        """Prevent deletion of compliance records to preserve the statutory audit trail."""
        from odoo.exceptions import UserError
        raise UserError(
            "Compliance records cannot be deleted to preserve the statutory audit trail."
            "Please archive them instead if they are no longer needed.")

    def get_last_completed_as_of(self, date_val):
        """Return the most recent passing test date on or before the given date.
        Used for point-in-time historical reporting to determine what the
        last completed date was as of a specific reference date.
        """
        self.ensure_one()
        if isinstance(date_val, str):
            date_val = fields.Date.to_date(date_val)
        tests = self.test_ids.filtered(lambda t: t.active and t.test_date and t.test_date <= date_val)
        latest_test = tests.sorted('test_date', reverse=True)[:1]
        return latest_test.test_date if latest_test else False

    def get_next_due_as_of(self, date_val):
        """Calculate what the next due date would have been as of the given reference date.
        Applies grace-period logic and frequency calculations against the most
        recent test on or before date_val to produce a point-in-time next-due value.
        """
        self.ensure_one()
        if isinstance(date_val, str):
            date_val = fields.Date.to_date(date_val)
        tests = self.test_ids.filtered(lambda t: t.active and t.test_date and t.test_date <= date_val)
        latest_test = tests.sorted('test_date', reverse=True)[:1]
        last_completed = latest_test.test_date if latest_test else False
        if last_completed:
            prev_due_date = latest_test.due_date
            if prev_due_date and self.grace_days:
                early_limit = prev_due_date - timedelta(days=self.grace_days)
                if early_limit <= last_completed <= prev_due_date:
                    base_date = prev_due_date
                else:
                    base_date = last_completed
            else:
                base_date = last_completed
            if self.frequency_unit == 'day':
                delta = timedelta(days=self.frequency_value)
            elif self.frequency_unit == 'week':
                delta = timedelta(weeks=self.frequency_value)
            elif self.frequency_unit == 'month':
                delta = relativedelta(months=self.frequency_value)
            elif self.frequency_unit == 'year':
                delta = relativedelta(years=self.frequency_value)
            else:
                delta = relativedelta(months=1)
            raw_due_date = base_date + delta
            return self._adjust_to_working_day(raw_due_date)
        future_tests = self.test_ids.filtered(lambda t: t.active and t.test_date and
                                                        t.test_date > date_val)
        if future_tests:
            oldest_test = future_tests.sorted('test_date', reverse=False)[0]
            if oldest_test.due_date:
                return oldest_test.due_date
        if self.next_due_date and self.create_date.date() <= date_val:
            return self.next_due_date
        return False

    def get_status_as_of(self, date_val):
        """Determine the compliance status as of a given reference date.
        Returns 'compliant', 'due_soon', 'overdue', 'failed', or
        'not_applicable' by evaluating the latest test outcome and next due
        date relative to date_val.
        """
        self.ensure_one()
        if isinstance(date_val, str):
            date_val = fields.Date.to_date(date_val)
        if not self.active or self.create_date.date() > date_val:
            return 'not_applicable'
        if not self.compliance_type_id or not (self.site_id or self.building_id or self.space_id):
            return 'not_applicable'
        tests = self.test_ids.filtered(lambda t: t.active and t.test_date and t.test_date <= date_val)
        if tests:
            latest_test = tests.sorted('test_date', reverse=True)[:1]
            if latest_test and latest_test.outcome in ['fail', 'remedial_required']:
                return 'failed'
        next_due = self.get_next_due_as_of(date_val)
        if not next_due:
            if tests:
                return 'not_applicable'
            else:
                return 'overdue'
        if next_due < date_val:
            return 'overdue'
        elif (next_due - date_val).days <= self.lead_days:
            return 'due_soon'
        else:
            return 'compliant'

    @api.model
    def get_import_templates(self):
        """Download import templates"""
        return [{
            'label': 'Import Template for Compliance Item',
            'template': '/odoo_nhs_estate_compliance/static/import_templates/compliance_item.xlsx',
        }]
