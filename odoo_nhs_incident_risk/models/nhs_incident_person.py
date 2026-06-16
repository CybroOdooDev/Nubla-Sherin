from odoo import fields, models


class NhsIncidentPerson(models.Model):
    _name = 'nhs.incident.person'
    _description = 'Person Affected by or Involved in an Incident'
    _order = 'incident_id, sequence'

    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    person_type = fields.Selection([
        ('patient', 'Patient / Resident / Service User'),
        ('staff', 'Staff Member'),
        ('visitor', 'Visitor'),
        ('contractor', 'Contractor'),
        ('witness', 'Witness'),
        ('other', 'Other'),
    ], string='Person Type', required=True, default='patient')
    name = fields.Char(string='Name / Initials',
                       help='Optional — supports anonymous-subject reporting.')
    age_band = fields.Selection([
        ('0_17', '0–17'),
        ('18_64', '18–64'),
        ('65_plus', '65+'),
        ('unknown', 'Unknown'),
    ], string='Age Band')
    harm_observed = fields.Selection([
        ('none', 'No Harm'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('death', 'Death'),
    ], string='Harm Observed', help="Reporter's view of harm to this person.")
    injury_description = fields.Char(string='Injury / Condition Description')
    treatment_required = fields.Selection([
        ('none', 'None'),
        ('first_aid', 'First Aid'),
        ('gp_or_clinic', 'GP / Clinic'),
        ('a_and_e', 'A&E'),
        ('admitted', 'Hospital Admission'),
    ], string='Treatment Required')
    # employee_id (hr.employee) is added by a separate glue module when hr is installed.
