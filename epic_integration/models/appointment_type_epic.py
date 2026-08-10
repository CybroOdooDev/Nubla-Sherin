from odoo import models, fields, api, _


class AppointmentTypeEpic(models.Model):
    _inherit = 'appointment.type'

    # ── NHS marker ───────────────────────────────────────────────────────────
    is_nhs_appointment = fields.Boolean(
        string='NHS Appointment',
        default=False,
        help='When set, this appointment type appears in the NHS Trust | Epic '
             'Appointments list.',
    )

    # ── Epic Mapping ─────────────────────────────────────────────────────────
    epic_service_type_code = fields.Char(
        string='Epic Service Type Code',
        help='Service type code used in the Epic FHIR Appointment resource '
             '(serviceType coding.code). e.g. "501" or "CARDIO".',
    )
    epic_appointment_type_code = fields.Char(
        string='Epic Appointment Type Code',
        help='Appointment type code used in the Epic FHIR Appointment resource '
             '(appointmentType coding.code). e.g. "FOLLOW-UP" or "ROUTINE".',
    )
    epic_department_code = fields.Char(
        string='Epic Department / Location Code',
        help='Department or location identifier in Epic used when pushing '
             'appointments. e.g. "CARDIO-001".',
    )

    # ── Epic Behaviour ───────────────────────────────────────────────────────
    epic_push_enabled = fields.Boolean(
        string='Push to Epic on Booking',
        default=False,
        help='When enabled, new bookings for this appointment type are '
             'automatically pushed to Epic as FHIR Appointment resources.',
    )
    epic_auto_sync = fields.Boolean(
        string='Auto-Sync from Epic',
        default=False,
        help='Periodically pull matching appointments from Epic and update '
             'the linked calendar events.',
    )
    epic_notes = fields.Text(
        string='Epic Integration Notes',
        help='Free-text notes about how this appointment type maps to Epic.',
    )

    # ── NHS Preset Templates ─────────────────────────────────────────────────

    @api.model
    def get_nhs_appointment_type_templates_data(self):
        base = '/epic_integration/static/src/img/'
        return {
            'gp_consultation': {
                'title': _('GP Consultation'),
                'description': _('Standard GP appointment for general practice consultations'),
                'icon': base + 'nhs_doctor.svg',
                'template_key': 'gp_consultation',
                'duration_label': '15 minutes',
            },
            'specialist_consultation': {
                'title': _('Specialist Consultation'),
                'description': _('Referral appointment with a hospital specialist'),
                'icon': base + 'nhs_specialist.svg',
                'template_key': 'specialist_consultation',
                'duration_label': '30 minutes',
            },
            'follow_up': {
                'title': _('Follow-up Appointment'),
                'description': _('Post-treatment or post-discharge follow-up visit'),
                'icon': base + 'nhs_followup.svg',
                'template_key': 'follow_up',
                'duration_label': '15 minutes',
            },
            'annual_health_review': {
                'title': _('Annual Health Review'),
                'description': _('Routine NHS annual health check and wellness review'),
                'icon': base + 'nhs_review.svg',
                'template_key': 'annual_health_review',
                'duration_label': '30 minutes',
            },
            'nurse_practitioner': {
                'title': _('Nurse Practitioner'),
                'description': _('Nurse-led appointment for treatments, dressings or assessments'),
                'icon': base + 'nhs_nurse.svg',
                'template_key': 'nurse_practitioner',
                'duration_label': '20 minutes',
            },
            'urgent_appointment': {
                'title': _('Urgent / Same-Day'),
                'description': _('Same-day urgent appointment for acute or emergency care'),
                'icon': base + 'nhs_urgent.svg',
                'template_key': 'urgent_appointment',
                'duration_label': '30 minutes',
            },
        }

    @api.model
    def action_setup_nhs_appointment_type_template(self, template_key):
        vals = self._get_nhs_appointment_type_template_values(template_key)
        new_record = self.env['appointment.type'].create(vals)
        action = self.env['ir.actions.act_window']._for_xml_id(
            'epic_integration.action_epic_appointment_types'
        )
        action['res_id'] = new_record.id
        action['views'] = [
            [self.env.ref('appointment.appointment_type_view_form').id, 'form']
        ]
        return action

    @api.model
    def _get_nhs_appointment_type_template_values(self, template_key):
        dispatch = {
            'gp_consultation': self._nhs_gp_consultation_values,
            'specialist_consultation': self._nhs_specialist_consultation_values,
            'follow_up': self._nhs_follow_up_values,
            'annual_health_review': self._nhs_annual_health_review_values,
            'nurse_practitioner': self._nhs_nurse_practitioner_values,
            'urgent_appointment': self._nhs_urgent_appointment_values,
        }
        return dispatch.get(template_key, lambda: {})()

    # ── Individual template value methods ────────────────────────────────────

    @api.model
    def _nhs_gp_consultation_values(self):
        return {
            'name': _('GP Consultation'),
            'appointment_duration': 0.25,
            'is_nhs_appointment': True,
            'is_auto_assign': False,
            'is_date_first': True,
            'show_avatars': True,
            'staff_user_ids': [(6, 0, [self.env.user.id])],
            'min_cancellation_hours': 2.0,
            'min_schedule_hours': 1.0,
            'max_schedule_days': 30,
            'question_ids': [(0, 0, {
                'name': _('Reason for visit'),
                'question_type': 'text',
                'placeholder': _('e.g. chest pain, repeat prescription, blood test results…'),
            })],
        }

    @api.model
    def _nhs_specialist_consultation_values(self):
        return {
            'name': _('Specialist Consultation'),
            'appointment_duration': 0.5,
            'is_nhs_appointment': True,
            'is_auto_assign': False,
            'is_date_first': True,
            'show_avatars': True,
            'staff_user_ids': [(6, 0, [self.env.user.id])],
            'min_cancellation_hours': 24.0,
            'min_schedule_hours': 24.0,
            'max_schedule_days': 90,
            'question_ids': [
                (0, 0, {
                    'name': _('Reason for referral'),
                    'question_type': 'text',
                    'placeholder': _('Describe the reason for this specialist referral…'),
                }),
                (0, 0, {
                    'name': _('GP referring you'),
                    'question_type': 'char',
                    'placeholder': _('Name of your referring GP…'),
                }),
            ],
        }

    @api.model
    def _nhs_follow_up_values(self):
        return {
            'name': _('Follow-up Appointment'),
            'appointment_duration': 0.25,
            'is_nhs_appointment': True,
            'is_auto_assign': False,
            'is_date_first': True,
            'show_avatars': True,
            'staff_user_ids': [(6, 0, [self.env.user.id])],
            'min_cancellation_hours': 2.0,
            'min_schedule_hours': 1.0,
            'max_schedule_days': 60,
            'question_ids': [(0, 0, {
                'name': _('What are you following up on?'),
                'question_type': 'text',
            })],
        }

    @api.model
    def _nhs_annual_health_review_values(self):
        return {
            'name': _('Annual Health Review'),
            'appointment_duration': 0.5,
            'is_nhs_appointment': True,
            'is_auto_assign': False,
            'is_date_first': True,
            'show_avatars': True,
            'staff_user_ids': [(6, 0, [self.env.user.id])],
            'min_cancellation_hours': 4.0,
            'min_schedule_hours': 24.0,
            'max_schedule_days': 90,
            'question_ids': [
                (0, 0, {
                    'name': _('Any changes to your health since last review?'),
                    'question_type': 'text',
                }),
                (0, 0, {
                    'name': _('Current medications'),
                    'question_type': 'text',
                    'placeholder': _('List any current medications…'),
                }),
            ],
        }

    @api.model
    def _nhs_nurse_practitioner_values(self):
        return {
            'name': _('Nurse Practitioner'),
            'appointment_duration': 0.33,
            'is_nhs_appointment': True,
            'is_auto_assign': False,
            'is_date_first': True,
            'show_avatars': True,
            'staff_user_ids': [(6, 0, [self.env.user.id])],
            'min_cancellation_hours': 1.0,
            'min_schedule_hours': 0.5,
            'max_schedule_days': 30,
            'question_ids': [(0, 0, {
                'name': _('Purpose of nurse appointment'),
                'question_type': 'text',
                'placeholder': _('e.g. wound dressing, injection, blood pressure check…'),
            })],
        }

    @api.model
    def _nhs_urgent_appointment_values(self):
        return {
            'name': _('Urgent / Same-Day Appointment'),
            'appointment_duration': 0.5,
            'is_nhs_appointment': True,
            'is_auto_assign': True,
            'is_date_first': True,
            'show_avatars': True,
            'staff_user_ids': [(6, 0, [self.env.user.id])],
            'min_cancellation_hours': 0.0,
            'min_schedule_hours': 0.0,
            'max_schedule_days': 1,
            'question_ids': [
                (0, 0, {
                    'name': _('Describe your urgent concern'),
                    'question_type': 'text',
                    'placeholder': _('Briefly describe your symptoms or reason for urgent appointment…'),
                }),
                (0, 0, {
                    'name': _('How long have you had this issue?'),
                    'question_type': 'char',
                }),
            ],
        }
