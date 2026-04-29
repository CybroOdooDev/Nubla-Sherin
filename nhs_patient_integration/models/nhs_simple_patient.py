# -*- coding: utf-8 -*-
"""
Simple Patient model with one-click NHS PDS lookup.
"""
import json
import logging
import time
import uuid
from datetime import date

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

NHS_BASE_URLS = {
    'sandbox':     'https://sandbox.api.service.nhs.uk',
    'integration': 'https://int.api.service.nhs.uk',
    'production':  'https://api.service.nhs.uk',
}
TIMEOUT_SEC = 30


class NhsSimplePatient(models.Model):
    _name = 'nhs.simple.patient'
    _description = 'NHS Patient (Simple)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # Identification
    name = fields.Char(string='Full Name', tracking=True)
    nhs_number = fields.Char(string='NHS Number', size=10, tracking=True,
                             help='10-digit NHS identifier (sandbox: 9000000009)')

    # Demographics
    date_of_birth = fields.Date(string='Date of Birth', tracking=True)
    age = fields.Integer(string='Age', compute='_compute_age')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ], string='Gender', tracking=True)

    # Contact
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')

    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    zip = fields.Char(string='Postcode')

    # NHS sync metadata
    nhs_synced = fields.Boolean(string='Verified with NHS', readonly=True,
                                tracking=True)
    nhs_last_sync = fields.Datetime(string='Last NHS Sync', readonly=True)
    nhs_raw_response = fields.Text(string='Last NHS FHIR Response',
                                    readonly=True)

    active = fields.Boolean(default=True)

    # ---------- computed ----------
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year - (
                    (today.month, today.day) <
                    (rec.date_of_birth.month, rec.date_of_birth.day)
                )
            else:
                rec.age = 0

    # ---------- validation ----------
    @api.constrains('nhs_number')
    def _check_nhs_number(self):
        """NHS Number must be 10 digits and pass the modulus-11 checksum."""
        for rec in self:
            n = (rec.nhs_number or '').replace(' ', '')
            if not n:
                continue
            if len(n) != 10 or not n.isdigit():
                raise ValidationError("NHS Number must be exactly 10 digits.")
            total = sum(int(d) * (10 - i) for i, d in enumerate(n[:9]))
            check = 11 - (total % 11)
            if check == 11:
                check = 0
            if check == 10 or check != int(n[9]):
                raise ValidationError(
                    f"Invalid NHS Number checksum for '{n}'. "
                    "Use a valid sandbox number (e.g. 9000000009)."
                )


    def action_fetch_from_nhs(self):
        """One-click fetch demographics from NHS PDS and update the form."""
        self.ensure_one()
        if not self.nhs_number:
            raise UserError("Please enter the NHS Number first, then save.")

        # 1. read settings
        ICP = self.env['ir.config_parameter'].sudo()
        env = ICP.get_param('nhs_simple.environment', 'sandbox')
        apikey = ICP.get_param('nhs_simple.apikey', '')
        if not apikey:
            raise UserError(
                "NHS API key not configured.\n"
                "Go to Settings → NHS Patient Simple to set it."
            )

        base_url = NHS_BASE_URLS[env]
        url = (f"{base_url}/personal-demographics/FHIR/R4/"
               f"Patient/{self.nhs_number}")

        # 2. build headers
        request_id = str(uuid.uuid4())
        headers = {
            'apikey': apikey,
            'X-Request-ID': request_id,
            'Accept': 'application/fhir+json',
        }

        # 3. call NHS
        log_vals = {
            'patient_id': self.id,
            'nhs_number': self.nhs_number,
            'request_id': request_id,
            'url': url,
            'environment': env,
        }
        start = time.time()
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT_SEC)
            log_vals['duration_ms'] = int((time.time() - start) * 1000)
            log_vals['status_code'] = resp.status_code
            log_vals['response_body'] = (resp.text or '')[:8000]

            if not resp.ok:
                self.env['nhs.simple.log'].sudo().create(log_vals)
                raise UserError(
                    f"NHS API returned HTTP {resp.status_code}.\n"
                    f"Response: {resp.text[:300]}\n\n"
                    "Tip: in sandbox, only certain test NHS Numbers work — "
                    "try 9000000009 or 9000000017."
                )

            data = resp.json()
            self.env['nhs.simple.log'].sudo().create(log_vals)
        except requests.exceptions.Timeout:
            log_vals['error'] = 'Timeout'
            self.env['nhs.simple.log'].sudo().create(log_vals)
            raise UserError("NHS API call timed out. Check network.")
        except requests.exceptions.RequestException as e:
            log_vals['error'] = str(e)
            self.env['nhs.simple.log'].sudo().create(log_vals)
            raise UserError(f"NHS API call failed: {e}")

        # 4. map FHIR response to Odoo fields
        self._apply_fhir_data(data)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'NHS Sync Complete',
                'message': f"Fetched {self.name} from NHS PDS ({env}).",
                'type': 'success',
                'sticky': False,
            },
        }

    def _apply_fhir_data(self, fhir):
        """Map a FHIR Patient resource onto this Odoo record."""
        self.ensure_one()
        vals = {
            'nhs_synced': True,
            'nhs_last_sync': fields.Datetime.now(),
            'nhs_raw_response': json.dumps(fhir, indent=2)[:8000],
        }

        # name
        names = fhir.get('name', []) or []
        chosen = next((n for n in names if n.get('use') == 'usual'), None)
        if not chosen and names:
            chosen = names[0]
        if chosen:
            given = ' '.join(chosen.get('given') or [])
            family = chosen.get('family', '')
            full = f"{given} {family}".strip()
            if full:
                vals['name'] = full

        # DOB & gender
        if fhir.get('birthDate'):
            vals['date_of_birth'] = fhir['birthDate']
        gender = fhir.get('gender')
        if gender in ('male', 'female', 'other', 'unknown'):
            vals['gender'] = gender

        # address
        addresses = fhir.get('address', []) or []
        home = next((a for a in addresses if a.get('use') == 'home'), None)
        if not home and addresses:
            home = addresses[0]
        if home:
            lines = home.get('line') or []
            if lines:
                vals['street'] = lines[0]
            if len(lines) > 1:
                vals['street2'] = lines[1]
            if home.get('city'):
                vals['city'] = home['city']
            if home.get('postalCode'):
                vals['zip'] = home['postalCode']

        # telecom
        telecoms = fhir.get('telecom', []) or []
        for t in telecoms:
            if t.get('system') == 'phone' and not vals.get('phone'):
                vals['phone'] = t.get('value')
            elif t.get('system') == 'email' and not vals.get('email'):
                vals['email'] = t.get('value')

        self.write(vals)
        self.message_post(body=(
            f"Demographics fetched from NHS PDS "
            f"(NHS Number {self.nhs_number})."
        ))
