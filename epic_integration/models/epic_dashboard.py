from datetime import date, timedelta
from odoo import models, api


class EpicDashboard(models.AbstractModel):
    _name = 'epic.dashboard'
    _description = 'Epic NHS Dashboard'

    @api.model
    def get_dashboard_data(self):
        today = date.today()
        tomorrow = today + timedelta(days=1)

        Patient = self.env['epic.patient']
        Appointment = self.env['epic.appointment']
        Allergy = self.env['epic.allergy']
        Condition = self.env['epic.condition']
        Note = self.env['epic.clinical.note']
        Practitioner = self.env['epic.practitioner']
        Ward = self.env['nhs.ward']

        return {
            'patients': {
                'total': Patient.search_count([]),
                'active': Patient.search_count([('active', '=', True)]),
                'male': Patient.search_count([('gender', '=', 'male')]),
                'female': Patient.search_count([('gender', '=', 'female')]),
                'other': Patient.search_count([('gender', 'not in', ['male', 'female'])]),
            },
            'appointments': {
                'total': Appointment.search_count([]),
                'today': Appointment.search_count([
                    ('start', '>=', str(today)),
                    ('start', '<', str(tomorrow)),
                ]),
                'booked': Appointment.search_count([('status', '=', 'booked')]),
                'arrived': Appointment.search_count([('status', '=', 'arrived')]),
                'fulfilled': Appointment.search_count([('status', '=', 'fulfilled')]),
                'cancelled': Appointment.search_count([('status', '=', 'cancelled')]),
                'proposed': Appointment.search_count([('status', 'in', ['proposed', 'pending'])]),
            },
            'allergies': {
                'total': Allergy.search_count([]),
                'active': Allergy.search_count([('clinical_status', '=', 'active')]),
                'inactive': Allergy.search_count([('clinical_status', '=', 'inactive')]),
                'resolved': Allergy.search_count([('clinical_status', '=', 'resolved')]),
                'high_criticality': Allergy.search_count([('criticality', '=', 'high')]),
                'low_criticality': Allergy.search_count([('criticality', '=', 'low')]),
                'food': Allergy.search_count([('category', '=', 'food')]),
                'medication': Allergy.search_count([('category', '=', 'medication')]),
                'environment': Allergy.search_count([('category', '=', 'environment')]),
                'biologic': Allergy.search_count([('category', '=', 'biologic')]),
            },
            'conditions': {
                'total': Condition.search_count([]),
                'active': Condition.search_count([('clinical_status', '=', 'active')]),
                'inactive': Condition.search_count([('clinical_status', '=', 'inactive')]),
                'resolved': Condition.search_count([('clinical_status', '=', 'resolved')]),
            },
            'clinical_notes': {
                'total': Note.search_count([]),
            },
            'practitioners': {
                'total': Practitioner.search_count([]),
                'active': Practitioner.search_count([('active', '=', True)]),
            },
            'wards': {
                'total': Ward.search_count([('active', '=', True)]),
            },
        }
