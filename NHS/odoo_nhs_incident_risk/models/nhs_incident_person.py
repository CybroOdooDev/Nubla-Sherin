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
from odoo import fields, models


class NhsIncidentPerson(models.Model):
    """A person affected by, or involved in, an incident."""
    _name = 'nhs.incident.person'
    _description = 'Person Affected by or Involved in an Incident'
    _order = 'incident_id, sequence'

    incident_id = fields.Many2one('nhs.incident', string='Incident',
                                  required=True, ondelete='cascade',
                                  help='The incident this person record is linked to.')
    sequence = fields.Integer(default=10,
                              help='Display order of this person within the persons affected list.')
    person_type = fields.Selection([
        ('patient', 'Patient / Resident / Service User'),
        ('staff', 'Staff Member'),
        ('visitor', 'Visitor'),
        ('contractor', 'Contractor'),
        ('witness', 'Witness'),
        ('other', 'Other'),
    ], string='Person Type', required=True, default='patient',
       help='The role or relationship of this individual to the incident.')
    name = fields.Char(string='Name / Initials',
                       help='Optional — supports anonymous-subject reporting.')
    age_band = fields.Selection([
        ('0_17', '0–17'),
        ('18_64', '18–64'),
        ('65_plus', '65+'),
        ('unknown', 'Unknown'),
    ], string='Age Band',
       help='The approximate age group of this person, used for LFPSE reporting and trend analysis.')
    harm_observed = fields.Selection([
        ('none', 'No Harm'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('death', 'Death'),
    ], string='Harm Observed', help="Reporter's view of harm to this person.")
    injury_description = fields.Char(string='Injury / Condition Description',
                                     help='Brief description of the physical injury or medical condition '
                                          'resulting from the incident (e.g. "laceration to left hand", "fractured wrist").')
    treatment_required = fields.Selection([
        ('none', 'None'),
        ('first_aid', 'First Aid'),
        ('gp_or_clinic', 'GP / Clinic'),
        ('a_and_e', 'A&E'),
        ('admitted', 'Hospital Admission'),
    ], string='Treatment Required',
       help='The level of medical treatment this person required as a direct result of the incident.')
    # employee_id (hr.employee) is added by a separate glue module when hr is installed.
