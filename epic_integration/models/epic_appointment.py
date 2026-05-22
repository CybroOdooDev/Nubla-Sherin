import logging
from dateutil import parser as dateutil_parser
from odoo import models, fields, api, exceptions

_logger = logging.getLogger(__name__)


def _parse_epic_dt(value):
    if not value:
        return False
    dt = dateutil_parser.parse(value)
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


class EpicAppointment(models.Model):
    _name = 'epic.appointment'
    _description = 'Epic Appointment'
    _inherit = ['epic.fhir.mixin']
    _order = 'start desc'

    # ── Core ────────────────────────────────────────────────────────────────
    description = fields.Char(string='Title / Description', required=True,
                              default='New Appointment')
    status = fields.Selection([
        ('proposed', 'Proposed'),
        ('pending', 'Pending'),
        ('booked', 'Booked'),
        ('arrived', 'Arrived'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
        ('noshow', 'No Show'),
        ('entered-in-error', 'Entered in Error'),
        ('checked-in', 'Checked In'),
        ('waitlist', 'Waitlist'),
    ], string='Status', default='booked')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
    ], string='Priority', default='0')
    color = fields.Integer(default=0)

    # ── Schedule ────────────────────────────────────────────────────────────
    start = fields.Datetime(string='Start')
    end = fields.Datetime(string='End')
    duration = fields.Float(string='Duration (hrs)', compute='_compute_duration',
                            store=True, readonly=False)
    appointment_type = fields.Char(string='Appointment Type')
    service_type = fields.Char(string='Service Type')
    location = fields.Char(string='Location / Room')

    # ── Participants (Odoo-linked) ───────────────────────────────────────────
    patient_id = fields.Many2one('epic.patient', string='Patient',
                                 ondelete='set null', index=True)
    practitioner_id = fields.Many2one('epic.practitioner', string='Practitioner',
                                      ondelete='set null', index=True)

    # ── Fallback Char fields (populated from Epic sync when no local record) ─
    patient_name = fields.Char(string='Patient Name (Epic)')
    practitioner_name = fields.Char(string='Practitioner Name (Epic)')

    # ── NHS Appointment Category ─────────────────────────────────────────────
    nhs_appointment_type = fields.Selection([
        ('gp_consultation', 'GP Consultation'),
        ('specialist', 'Specialist Consultation'),
        ('follow_up', 'Follow-up Appointment'),
        ('annual_review', 'Annual Health Review'),
        ('nurse', 'Nurse Practitioner'),
        ('urgent', 'Urgent / Same-Day'),
        ('other', 'Other'),
    ], string='NHS Appointment Category', default='gp_consultation')

    ward_id = fields.Many2one('nhs.ward', string='Ward', ondelete='set null')

    # ── Notes ───────────────────────────────────────────────────────────────
    comment = fields.Text(string='Notes / Patient Instructions')

    # ── Epic FHIR ───────────────────────────────────────────────────────────
    epic_id = fields.Char(string='Epic FHIR ID', index=True)

    # ────────────────────────────────────────────────────────────────────────

    @api.depends('start', 'end')
    def _compute_duration(self):
        for rec in self:
            if rec.start and rec.end and rec.end > rec.start:
                rec.duration = (rec.end - rec.start).total_seconds() / 3600.0
            else:
                rec.duration = 0.0

    _NHS_TYPE_LABELS = {
        'gp_consultation': 'GP Consultation',
        'specialist': 'Specialist Consultation',
        'follow_up': 'Follow-up Appointment',
        'annual_review': 'Annual Health Review',
        'nurse': 'Nurse Practitioner',
        'urgent': 'Urgent / Same-Day',
        'other': 'Appointment',
    }

    @api.onchange('nhs_appointment_type', 'patient_id')
    def _onchange_nhs_appointment_type(self):
        label = self._NHS_TYPE_LABELS.get(self.nhs_appointment_type or 'other', 'Appointment')
        if self.patient_id:
            self.description = f'{label} — {self.patient_id.name}'
        else:
            self.description = label

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.patient_name = self.patient_id.name

    @api.onchange('practitioner_id')
    def _onchange_practitioner_id(self):
        if self.practitioner_id:
            self.practitioner_name = self.practitioner_id.name

    @api.onchange('start', 'duration')
    def _onchange_start_duration(self):
        if self.start and self.duration and self.duration > 0:
            from datetime import timedelta
            self.end = self.start + timedelta(hours=self.duration)

    # ── Epic sync ────────────────────────────────────────────────────────────

    def action_sync_appointments(self):
        company = self.env.company

        search_params = {}
        if company.epic_appointment_search_date:
            search_params['date'] = f"ge{company.epic_appointment_search_date}"
        if company.epic_appointment_search_status:
            search_params['status'] = company.epic_appointment_search_status.strip()
        if company.epic_appointment_search_patient:
            search_params['patient'] = company.epic_appointment_search_patient.strip()

        if not search_params:
            raise exceptions.UserError(
                "Appointment sync requires at least one search parameter.\n"
                "Configure Date From / Status / Patient under "
                "Settings > Epic Integration."
            )

        access_token, granted_scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        self._epic_check_scope('system/Appointment.read', granted_scope)

        url = self._epic_fhir_url(company, 'Appointment')
        bundle = self._epic_fhir_get(access_token, url, params=search_params)

        created = updated = 0

        for entry in bundle.get('entry', []):
            resource = entry.get('resource', {})
            if resource.get('resourceType') != 'Appointment':
                continue

            epic_id = resource.get('id')
            if not epic_id:
                continue

            patient_name = practitioner_name = ''
            for participant in resource.get('participant', []):
                actor = participant.get('actor', {})
                ref = actor.get('reference', '')
                display = actor.get('display', '')
                if 'Patient' in ref and not patient_name:
                    patient_name = display
                elif 'Practitioner' in ref and not practitioner_name:
                    practitioner_name = display

            service_type = ''
            for st in resource.get('serviceType', []):
                codings = st.get('coding', [])
                service_type = (codings[0].get('display', '')
                                if codings else st.get('text', ''))
                if service_type:
                    break

            appt_type_codings = resource.get('appointmentType', {}).get('coding', [])
            appointment_type = (appt_type_codings[0].get('display', '')
                                if appt_type_codings else '')

            # Try to link to local records by name
            patient_rec = self.env['epic.patient'].search(
                [('name', '=ilike', patient_name)], limit=1
            ) if patient_name else self.env['epic.patient']
            practitioner_rec = self.env['epic.practitioner'].search(
                [('name', '=ilike', practitioner_name)], limit=1
            ) if practitioner_name else self.env['epic.practitioner']

            vals = {
                'status': resource.get('status', 'booked'),
                'start': _parse_epic_dt(resource.get('start')),
                'end': _parse_epic_dt(resource.get('end')),
                'description': resource.get('description', '') or 'Appointment',
                'appointment_type': appointment_type,
                'service_type': service_type,
                'patient_name': patient_name,
                'practitioner_name': practitioner_name,
                'patient_id': patient_rec.id if patient_rec else False,
                'practitioner_id': practitioner_rec.id if practitioner_rec else False,
                'comment': (resource.get('comment', '')
                            or resource.get('patientInstruction', '')),
            }

            existing = self.search([('epic_id', '=', epic_id)], limit=1)
            if existing:
                existing.write(vals)
                updated += 1
            else:
                vals['epic_id'] = epic_id
                self.create(vals)
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Appointment Sync Complete',
                'message': (f'Synced appointments from Epic. '
                            f'Created: {created}, Updated: {updated}'),
                'sticky': False,
            },
        }
