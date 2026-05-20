import logging
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)


class EpicAppointment(models.Model):
    _name = 'epic.appointment'
    _description = 'Epic Appointment'
    _inherit = ['epic.fhir.mixin']
    _order = 'start desc'

    epic_id = fields.Char(string='Epic FHIR ID', required=True, index=True)
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
    ], string='Status')
    start = fields.Datetime(string='Start')
    end = fields.Datetime(string='End')
    description = fields.Char(string='Description')
    appointment_type = fields.Char(string='Appointment Type')
    service_type = fields.Char(string='Service Type')
    patient_name = fields.Char(string='Patient')
    practitioner_name = fields.Char(string='Practitioner')
    comment = fields.Text(string='Comment')

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
                "Configure Date From / Status / Patient under Settings > Epic Integration."
            )

        access_token, granted_scope = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        self._epic_check_scope('system/Appointment.read', granted_scope)

        url = self._epic_fhir_url(company, 'Appointment')
        bundle = self._epic_fhir_get(access_token, url, params=search_params)

        entries = bundle.get('entry', [])
        created = updated = 0

        for entry in entries:
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
                service_type = codings[0].get('display', '') if codings else st.get('text', '')
                if service_type:
                    break

            appt_type_codings = resource.get('appointmentType', {}).get('coding', [])
            appointment_type = appt_type_codings[0].get('display', '') if appt_type_codings else ''

            vals = {
                'status': resource.get('status', ''),
                'start': resource.get('start') or False,
                'end': resource.get('end') or False,
                'description': resource.get('description', ''),
                'appointment_type': appointment_type,
                'service_type': service_type,
                'patient_name': patient_name,
                'practitioner_name': practitioner_name,
                'comment': resource.get('comment', '') or resource.get('patientInstruction', ''),
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
                'message': f'Synced appointments from Epic. Created: {created}, Updated: {updated}',
                'sticky': False,
            },
        }
