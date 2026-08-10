# -*- coding: utf-8 -*-
import requests
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class NhsSimpleDoctor(models.Model):
    _name = 'nhs.simple.doctor'
    _description = 'NHS Doctor / GP'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Doctor Name', required=True, tracking=True)
    gp_code = fields.Char(string='GP Code / GMC Number', tracking=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    active = fields.Boolean(default=True)

    def action_sync_nhs_gps(self):
        """
        Fetch GP practices from the public NHS ODS API and create records in Odoo.
        For performance, we limit this to the first 100 results.
        """
        url = "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations?PrimaryRoleId=RO76&Limit=100"
        
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Failed to fetch NHS GPs: {e}")
            raise UserError(f"Failed to connect to NHS ODS API: {e}")

        organisations = data.get('Organisations', [])
        if not organisations:
            raise UserError("No GP practices found from the NHS API.")

        created_count = 0
        updated_count = 0

        for org in organisations:
            gp_code = org.get('OrgId')
            name = org.get('Name')
            
            if not gp_code or not name:
                continue

            # Check if GP already exists
            existing_gp = self.search([('gp_code', '=', gp_code)], limit=1)
            
            if existing_gp:
                # Optionally update existing GP (just name for now)
                if existing_gp.name != name:
                    existing_gp.write({'name': name})
                    updated_count += 1
            else:
                # Create new GP
                self.create({
                    'name': name,
                    'gp_code': gp_code,
                })
                created_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'NHS GP Sync Complete',
                'message': f"Imported {created_count} new GPs and updated {updated_count} existing GPs.",
                'type': 'success',
                'sticky': False,
            },
        }
