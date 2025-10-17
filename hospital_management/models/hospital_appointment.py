from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class HospitalAppointment(models.Model):
    _name = 'hospital.appointment'
    _description = 'Hospital Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'appointment_date desc, appointment_time desc'

    # Basic Information
    name = fields.Char(string='Appointment Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hospital.doctor', string='Doctor', required=True, tracking=True)
    department_id = fields.Many2one('hospital.department', string='Department',
                                    related='doctor_id.department_id', store=True)

    # Appointment Details
    appointment_date = fields.Date(string='Appointment Date', required=True, tracking=True)
    appointment_time = fields.Float(string='Appointment Time', required=True)
    duration = fields.Float(string='Duration (hours)', default=0.5)
    appointment_type = fields.Selection([
        ('consultation', 'Consultation'),
        ('follow_up', 'Follow-up'),
        ('emergency', 'Emergency'),
        ('walk_in', 'Walk-in'),
    ], string='Type', required=True, default='consultation', tracking=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string='Status', default='draft', tracking=True)

    # Additional Information
    reason = fields.Text(string='Reason for Visit')
    notes = fields.Text(string='Notes')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Very High'),
    ], string='Priority', default='0')

    # Recurring
    is_recurring = fields.Boolean(string='Recurring Appointment')
    recurrence_pattern = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Recurrence Pattern')
    recurrence_count = fields.Integer(string='Number of Recurrences')

    # Notifications
    email_sent = fields.Boolean(string='Email Sent', default=False)
    sms_sent = fields.Boolean(string='SMS Sent', default=False)
    reminder_sent = fields.Boolean(string='Reminder Sent', default=False)

    # Related Records
    consultation_id = fields.Many2one('hospital.consultation', string='Consultation')
    invoice_id = fields.Many2one('account.move', string='Invoice')

    # Computed
    patient_phone = fields.Char(string='Patient Phone', related='patient_id.phone', readonly=True)
    patient_email = fields.Char(string='Patient Email', related='patient_id.email', readonly=True)
    doctor_fee = fields.Float(string='Consultation Fee', related='doctor_id.consultation_fee', readonly=True)

    # Queue Management
    queue_number = fields.Integer(string='Queue Number')
    check_in_time = fields.Datetime(string='Check-in Time')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hospital.appointment') or _('New')
        return super(HospitalAppointment, self).create(vals_list)

        # Set queue number
        if vals.get('appointment_date') and vals.get('doctor_id'):
            same_day_appointments = self.search([
                ('appointment_date', '=', vals['appointment_date']),
                ('doctor_id', '=', vals['doctor_id']),
                ('state', '!=', 'cancelled')
            ])
            vals['queue_number'] = len(same_day_appointments) + 1

        return super(HospitalAppointment, self).create(vals)

    @api.constrains('appointment_date', 'appointment_time', 'doctor_id')
    def _check_appointment_slot(self):
        for record in self:
            if record.appointment_date < fields.Date.today():
                raise ValidationError(_('Appointment date cannot be in the past.'))

            # Check if doctor is available
            if record.doctor_id.on_leave:
                raise ValidationError(_('Doctor is on leave.'))

            # Check for overlapping appointments
            overlapping = self.search([
                ('doctor_id', '=', record.doctor_id.id),
                ('appointment_date', '=', record.appointment_date),
                ('id', '!=', record.id),
                ('state', 'not in', ['cancelled', 'no_show']),
            ])

            for apt in overlapping:
                if (record.appointment_time < apt.appointment_time + apt.duration and
                        record.appointment_time + record.duration > apt.appointment_time):
                    raise ValidationError(_('This time slot is already booked.'))

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        self._send_confirmation_notification()

    def action_waiting(self):
        self.write({
            'state': 'waiting',
            'check_in_time': fields.Datetime.now()
        })

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})
        # Create consultation record
        self._create_consultation()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_no_show(self):
        self.write({'state': 'no_show'})

    def _create_consultation(self):
        """Create consultation record from appointment"""
        for record in self:
            if not record.consultation_id:
                consultation = self.env['hospital.consultation'].create({
                    'patient_id': record.patient_id.id,
                    'doctor_id': record.doctor_id.id,
                    'appointment_id': record.id,
                    'consultation_date': record.appointment_date,
                })
                record.consultation_id = consultation.id

    def _send_confirmation_notification(self):
        """Send email/SMS confirmation"""
        for record in self:
            if record.patient_email and not record.email_sent:
                template = self.env.ref('hospital_management.email_template_appointment_confirmation',
                                        raise_if_not_found=False)
                if template:
                    template.send_mail(record.id, force_send=True)
                    record.email_sent = True

    def action_send_reminder(self):
        """Send appointment reminder"""
        tomorrow = fields.Date.today() + timedelta(days=1)
        appointments = self.search([
            ('appointment_date', '=', tomorrow),
            ('state', '=', 'confirmed'),
            ('reminder_sent', '=', False)
        ])

        for appointment in appointments:
            # Send reminder logic
            appointment.reminder_sent = True

    def create_recurring_appointments(self):
        """Create recurring appointments"""
        for record in self:
            if record.is_recurring and record.recurrence_pattern and record.recurrence_count:
                current_date = record.appointment_date

                for i in range(record.recurrence_count):
                    if record.recurrence_pattern == 'daily':
                        current_date += timedelta(days=1)
                    elif record.recurrence_pattern == 'weekly':
                        current_date += timedelta(weeks=1)
                    elif record.recurrence_pattern == 'monthly':
                        current_date += timedelta(days=30)

                    self.create({
                        'patient_id': record.patient_id.id,
                        'doctor_id': record.doctor_id.id,
                        'appointment_date': current_date,
                        'appointment_time': record.appointment_time,
                        'appointment_type': record.appointment_type,
                        'reason': record.reason,
                    })

    @api.model
    def send_appointment_reminders(self):
        """Send reminders for tomorrow's appointments"""
        tomorrow = fields.Date.today() + timedelta(days=1)
        appointments = self.search([
            ('appointment_date', '=', tomorrow),
            ('state', '=', 'confirmed'),
            ('reminder_sent', '=', False)
        ])

        template = self.env.ref('hospital_management.email_template_appointment_reminder',
                                raise_if_not_found=False)

        for appointment in appointments:
            if template and appointment.patient_email:
                template.send_mail(appointment.id, force_send=True)
                appointment.reminder_sent = True

        return True

    @api.model
    def auto_update_appointment_status(self):
        """Auto-mark appointments as no-show if not checked in"""
        yesterday = fields.Date.today() - timedelta(days=1)
        appointments = self.search([
            ('appointment_date', '<', yesterday),
            ('state', '=', 'confirmed')
        ])
        appointments.write({'state': 'no_show'})
        return True
