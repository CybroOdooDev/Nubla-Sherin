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
import base64
import logging
from datetime import datetime, timezone
import pytz
import requests

from hubspot import HubSpot
from hubspot.crm.deals import BatchInputSimplePublicObjectBatchInput, SimplePublicObjectInput
from hubspot.crm.companies import BatchInputSimplePublicObjectBatchInput as CompanyBatchInput
from hubspot.crm.contacts import BatchInputSimplePublicObjectBatchInput as ContactBatchInput

from odoo import models, fields, _
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class HubspotConnector(models.Model):
    """HubSpot connector with full sync features: Contacts, Companies, Deals."""
    _name = "hubspot.connector"
    _description = "HubSpot Connector"

    # General
    state = fields.Selection(
        [("disconnected", "Disconnected"), ("connected", "Connected")],
        default="disconnected", string="State", help="Connection state to HubSpot"
    )
    name = fields.Char(string="Connector Name")
    access_key = fields.Char(string="Access Token", password=True)
    owner_id = fields.Char(string="Owner ID", required=True)
    connection = fields.Boolean(string="Connection")

    # Contact toggles
    import_contacts = fields.Boolean(string="Import Contacts")
    export_contacts = fields.Boolean(string="Export Contacts")
    update_odoo_contacts = fields.Boolean(string="Update Odoo Contacts")
    update_hub_contacts = fields.Boolean(string="Update HubSpot Contacts")

    # Company toggles
    import_company = fields.Boolean(string="Import Company")
    export_company = fields.Boolean(string="Export Company")
    update_odoo_company = fields.Boolean(string="Update Odoo Company")
    update_hub_company = fields.Boolean(string="Update HubSpot Company")

    # Deals toggles
    export_deals = fields.Boolean(string="Export Deals")
    import_deals = fields.Boolean(string="Import Deals")
    update_odoo_deals = fields.Boolean(string="Update Odoo Deals")
    update_hub_deals = fields.Boolean(string="Update HubSpot Deals")

    # Timestamps
    contacts_last_imported = fields.Datetime(string="Contacts Last Imported", readonly=True)
    contacts_last_exported = fields.Datetime(string="Contacts Last Exported", readonly=True)
    hub_contact_last_updated = fields.Datetime(string="HubSpot Contacts Updated", readonly=True)
    odoo_contact_last_updated = fields.Datetime(string="Odoo Contacts Updated", readonly=True)

    company_last_imported = fields.Datetime(string="Company Last Imported", readonly=True)
    company_last_exported = fields.Datetime(string="Company Last Exported", readonly=True)
    hub_company_last_updated = fields.Datetime(string="HubSpot Company Updated", readonly=True)
    odoo_company_last_updated = fields.Datetime(string="Odoo Company Updated", readonly=True)

    deals_last_imported = fields.Datetime(string="Deals Last Imported", readonly=True)
    deals_last_exported = fields.Datetime(string="Deals Last Exported", readonly=True)
    hub_deal_last_updated = fields.Datetime(string="HubSpot Deal Updated", readonly=True)
    odoo_deal_last_updated = fields.Datetime(string="Odoo Deal Updated", readonly=True)


    def _hubspot_headers(self):
        return {
            "Authorization": f"Bearer {self.access_key}",
            "Content-Type": "application/json",
        }

    def _hubspot_base(self):
        return "https://api.hubapi.com"

    def _get_hubspot_client(self):
        return HubSpot(access_token=self.access_key)

    def _notify_and_rainbow(self, title, message):
        # Commit first so user sees up-to-date data
        try:
            self.env.cr.commit()
        except Exception:
            pass
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "notification",
            {
                "title": title,
                "message": message,
                "sticky": False,
            }
        )


    def action_connect(self):
        """Test connection to HubSpot and verify owner_id."""
        if not self.connection:
            owners_endpoint = f"{self._hubspot_base()}/crm/v3/owners/"
            headers = self._hubspot_headers()
            try:
                resp = requests.get(owners_endpoint, headers=headers, timeout=10)
                if resp.ok:
                    data = resp.json()
                    results = data.get("results", [])
                    if results:
                        owner_id = str(results[0].get("id"))
                        if owner_id == self.owner_id:
                            self.connection = True
                            self.state = "connected"
                        else:
                            raise AccessError(_("Owner ID mismatch: HubSpot returned %s, expected %s") % (owner_id, self.owner_id))
                    else:
                        raise AccessError(_("No owners found in HubSpot response"))
                else:
                    raise AccessError(_("Error fetching account info: %s - %s") % (resp.status_code, resp.text))
            except requests.exceptions.RequestException as e:
                raise AccessError(_("Connection failed: %s") % str(e))
        else:
            self.connection = False
            self.state = "disconnected"


    def action_contact_sync(self):
        """Top-level contact sync action: import/export/update + UI feedback."""
        rainbow_msg = "Congrats, "
        if self.export_contacts:
            exported_count = self.action_export_partner()
            if exported_count > 0:
                rainbow_msg += f"# {exported_count} Contacts Exported"
        if self.import_contacts:
            imported_count = self.action_import_partner()
            if imported_count > 0:
                rainbow_msg += f", # {imported_count} Contacts Imported"
        if self.update_hub_contacts:
            hub_update_count = self.action_update_hub_partner()
            if hub_update_count > 0:
                rainbow_msg += f", #{hub_update_count} HubSpot Contacts Updated"
        if self.update_odoo_contacts:
            odoo_update_count = self.action_update_odoo_partner()
            if odoo_update_count > 0:
                rainbow_msg += f", # {odoo_update_count} Odoo Contacts Updated"

        if rainbow_msg == "Congrats, ":
            rainbow_msg += "Contacts are already synced"

        return self._notify_and_rainbow("HubSpot Sync Completed 🎉", rainbow_msg)

    def action_company_sync(self):
        """Top-level company sync action + UI feedback."""
        rainbow_msg = "Congrats, "
        if self.export_company:
            exported_count = self.action_export_company()
            if exported_count > 0:
                rainbow_msg += f"# {exported_count} Companies Exported"
        if self.import_company:
            imported_count = self.action_import_company()
            if imported_count > 0:
                rainbow_msg += f", # {imported_count} Companies Imported"
        if self.update_hub_company:
            hub_update_count = self.action_update_hub_company()
            if hub_update_count > 0:
                rainbow_msg += f", #{hub_update_count} HubSpot Companies Updated"
        if self.update_odoo_company:
            odoo_update_count = self.action_update_odoo_company()
            if odoo_update_count > 0:
                rainbow_msg += f", # {odoo_update_count} Odoo Companies Updated"

        if rainbow_msg == "Congrats, ":
            rainbow_msg += "Companies are already synced"

        return self._notify_and_rainbow("HubSpot Company Sync Completed 🎉", rainbow_msg)

    def action_deal_sync(self):
        """Top-level deals sync action + UI feedback."""
        rainbow_msg = "Congrats, "
        if self.export_deals:
            exported_count = self.action_export_deals()
            if exported_count > 0:
                rainbow_msg += f"# {exported_count} Deals Exported"
        if self.import_deals:
            imported_count = self.action_import_deals()
            if imported_count > 0:
                rainbow_msg += f", # {imported_count} Deals Imported"
        if self.update_hub_deals:
            hub_update_count = self.action_update_hub_deals()
            if hub_update_count > 0:
                rainbow_msg += f", #{hub_update_count} HubSpot Deals Updated"
        if self.update_odoo_deals:
            odoo_update_count = self.action_update_odoo_deals()
            if odoo_update_count > 0:
                rainbow_msg += f", # {odoo_update_count} Odoo Deals Updated"

        if rainbow_msg == "Congrats, ":
            rainbow_msg += "Deals are already synced"

        return self._notify_and_rainbow("HubSpot Deals Sync Completed 🎉", rainbow_msg)


    def action_export_partner(self):
        """
        Export Odoo contacts to HubSpot v3.
        Creates required custom properties if missing.
        Handles conflicts by linking existing HubSpot ID to Odoo record.
        """
        access_token = self.access_key
        headers = self._hubspot_headers()
        base_url = self._hubspot_base()

        # 1) Ensure custom properties exist (odoo_mail, odoo_image_string)
        partner_fields = [
            {
                "name": "odoo_mail",
                "label": "Mail",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation",
                "description": "Custom field created from Odoo"
            },
            {
                "name": "odoo_image_string",
                "label": "Image String",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation",
                "description": "Custom field created from Odoo"
            },
        ]
        for field in partner_fields:
            check_url = f"{base_url}/crm/v3/properties/contacts/{field['name']}"
            try:
                r = requests.get(check_url, headers=headers, timeout=10)
            except Exception as e:
                raise AccessError(_("HubSpot request failed: %s") % str(e))
            if r.status_code == 404:
                create_url = f"{base_url}/crm/v3/properties/contacts"
                r2 = requests.post(create_url, headers=headers, json=field, timeout=10)
                if not r2.ok:
                    _logger.warning("Failed creating property %s: %s", field['name'], r2.text)

        hubspot_ids = []
        has_more = True
        after = None
        page_count = 0
        while has_more:
            page_count += 1
            url = f"{base_url}/crm/v3/objects/contacts"
            params = {"limit": 100}
            if after:
                params["after"] = after
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=15)
            except Exception as e:
                raise AccessError(_("HubSpot contacts fetch failed: %s") % str(e))
            if not resp.ok:
                _logger.warning("Failed to fetch contacts page %s: %s", page_count, resp.text)
                break
            data = resp.json()
            hubspot_ids.extend([item.get("id") for item in data.get("results", []) if item.get("id")])
            after = data.get("paging", {}).get("next", {}).get("after")
            has_more = bool(after)
            if page_count >= 20:
                _logger.warning("Stopping HubSpot contact pagination after 20 pages")
                break

        odoo_partners = self.env["res.partner"].search([("active", "=", True)])
        success_count = 0
        for rec in odoo_partners:
            if not rec.hs_object_id or rec.hs_object_id not in hubspot_ids:
                props = {
                    "firstname": rec.name or "",
                    "lastname": "",
                    "odoo_mail": rec.email or "",
                    "phone": rec.phone or "",
                    "company": rec.commercial_company_name or rec.company_name or "",
                    "jobtitle": rec.function or "",
                    "website": rec.website or "",
                    "address": (rec.street or "") + ("," + rec.street2 if rec.street2 else ""),
                    "city": rec.city or "",
                    "state": rec.state_id.name if rec.state_id else "",
                    "zip": rec.zip or "",
                    "country": rec.country_id.name if rec.country_id else "",
                    "odoo_image_string": base64.b64encode(rec.image_1920).decode("utf-8") if rec.image_1920 else "",
                }
                payload = {"properties": props}
                create_url = f"{base_url}/crm/v3/objects/contacts"
                try:
                    r = requests.post(create_url, headers=headers, json=payload, timeout=15)
                except Exception as e:
                    raise AccessError(_("HubSpot create contact failed: %s") % str(e))

                if r.ok:
                    new_id = r.json().get("id")
                    if new_id:
                        try:
                            with self.env.cr.savepoint():
                                rec.write({"hs_object_id": new_id, "sync_mode": "export"})
                                success_count += 1
                        except Exception as e:
                            _logger.warning("Failed to update contact %s after export: %s", rec.display_name, str(e))
                else:
                    try:
                        data = r.json()
                    except Exception:
                        data = {}
                    if data.get("category") == "CONFLICT" and "Existing ID" in data.get("message", ""):
                        existing_id = data["message"].split("Existing ID:")[-1].strip('"} ')
                        if existing_id:
                            try:
                                with self.env.cr.savepoint():
                                    rec.write({"hs_object_id": existing_id, "sync_mode": "export"})
                                    success_count += 1
                            except Exception as e:
                                _logger.warning("Failed to update contact %s with existing ID: %s", rec.display_name, str(e))
                    else:
                        _logger.warning("Failed exporting contact %s: %s", rec.display_name, r.text)

        if success_count > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": datetime.now(),
                "res_model_id": self.env.ref("base.model_res_partner").id,
                "sync_mode": "export",
                "state": "success",
                "count": success_count,
            })
        self.contacts_last_exported = datetime.now()
        return success_count

    def action_import_partner(self):
        """
        Import contacts from HubSpot and create missing res.partner records.
        """
        needed_fields = [
            "firstname", "lastname", "email", "phone", "company", "jobtitle",
            "website", "address", "city", "state", "zip", "country",
            "odoo_mail", "odoo_image_string"
        ]
        client = self._get_hubspot_client()
        try:
            hubspot_contacts = client.crm.contacts.get_all(properties=needed_fields)
        except Exception as e:
            raise AccessError(_("Failed to fetch HubSpot contacts: %s") % str(e))

        existing_hs_ids = self.env["res.partner"].search([]).mapped("hs_object_id")
        partners_to_create = []
        success_count = 0

        state_dict = {s["name"]: s["id"] for s in self.env["res.country.state"].search_read([], ["name"])}
        country_dict = {c["name"]: c["id"] for c in self.env["res.country"].search_read([], ["name"])}

        for rec in hubspot_contacts:
            hs_id = rec.properties.get("hs_object_id") or rec.id
            if not hs_id:
                continue
            if hs_id not in existing_hs_ids:
                name = (rec.properties.get("firstname") or "") + (" " + rec.properties.get("lastname") if rec.properties.get("lastname") else "")
                email = rec.properties.get("email") or rec.properties.get("odoo_mail")
                image_b64 = rec.properties.get("odoo_image_string")
                partners_to_create.append({
                    "name": name or "Contact",
                    "email": email,
                    "phone": rec.properties.get("phone"),
                    "function": rec.properties.get("jobtitle"),
                    "website": rec.properties.get("website"),
                    "street": rec.properties.get("address"),
                    "city": rec.properties.get("city"),
                    "zip": rec.properties.get("zip"),
                    "state_id": state_dict.get(str(rec.properties.get("state")), None),
                    "country_id": country_dict.get(str(rec.properties.get("country")), None),
                    "image_1920": base64.b64decode(image_b64) if image_b64 else None,
                    "hs_object_id": hs_id,
                    "sync_mode": "import"
                })
                success_count += 1

        if partners_to_create:
            self.env["res.partner"].sudo().create(partners_to_create)

        if success_count > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": datetime.now(),
                "res_model_id": self.env.ref("base.model_res_partner").id,
                "sync_mode": "import",
                "state": "success",
                "count": success_count,
            })
        self.contacts_last_imported = datetime.now()
        return success_count

    def action_update_hub_partner(self):
        """Update HubSpot contacts based on Odoo changes."""
        client = self._get_hubspot_client()
        odoo_partners = self.env["res.partner"].search([])
        odoo_hs_list = odoo_partners.mapped("hs_object_id")
        try:
            hubspot_contacts = client.crm.contacts.get_all()
        except Exception as e:
            raise AccessError(_("Failed to fetch HubSpot contacts for update: %s") % str(e))

        update_success = 0
        data_to_update = []
        for rec in hubspot_contacts:
            hs_id = rec.properties.get("hs_object_id") or rec.id
            if not hs_id:
                continue
            if hs_id in odoo_hs_list:
                odoo_rec = self.env["res.partner"].search([("hs_object_id", "=", hs_id)], limit=1)
                last_hub_updated = rec.updated_at.astimezone(timezone.utc).replace(tzinfo=None) if getattr(rec, "updated_at", None) else None
                if odoo_rec and (odoo_rec.write_date and (odoo_rec.write_date > (self.hub_contact_last_updated or last_hub_updated))):
                    props = {
                        "firstname": odoo_rec.name,
                        "lastname": "",
                        "odoo_mail": odoo_rec.email or "",
                        "phone": odoo_rec.phone or "",
                        "company": odoo_rec.commercial_company_name or odoo_rec.company_name or "",
                        "jobtitle": odoo_rec.function or "",
                        "website": odoo_rec.website or "",
                        "address": (odoo_rec.street or "") + ("," + odoo_rec.street2 if odoo_rec.street2 else ""),
                        "city": odoo_rec.city or "",
                        "state": odoo_rec.state_id.name if odoo_rec.state_id else "",
                        "zip": odoo_rec.zip or "",
                        "country": odoo_rec.country_id.name if odoo_rec.country_id else "",
                        "odoo_image_string": base64.b64encode(odoo_rec.image_1920).decode("utf-8") if odoo_rec.image_1920 else "",
                    }
                    data_to_update.append({
                        "id": hs_id,
                        "properties": props
                    })
                    update_success += 1

        if data_to_update:
            try:
                client.crm.contacts.batch_api.update(batch_input_simple_public_object_batch_input=ContactBatchInput(data_to_update))
            except Exception as e:
                _logger.warning("Batch update of contacts failed: %s", str(e))

        self.hub_contact_last_updated = datetime.now()
        if update_success > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": self.hub_contact_last_updated,
                "res_model_id": self.env.ref("base.model_res_partner").id,
                "sync_mode": "hub_updated",
                "state": "success",
                "count": update_success,
            })
        return update_success

    def action_update_odoo_partner(self):
        """Update Odoo partner records based on HubSpot changes."""
        client = self._get_hubspot_client()
        needed_fields = [
            "firstname", "lastname", "email", "phone", "company", "jobtitle",
            "website", "address", "city", "state", "zip", "country", "odoo_mail", "odoo_image_string"
        ]
        try:
            hubspot_contacts = client.crm.contacts.get_all(properties=needed_fields)
        except Exception as e:
            raise AccessError(_("Failed to fetch HubSpot contacts for import update: %s") % str(e))

        hub_ids = [rec.properties.get("hs_object_id") or rec.id for rec in hubspot_contacts]
        update_success = 0

        state_dict = {s["name"]: s["id"] for s in self.env["res.country.state"].search_read([], ["name"])}
        country_dict = {c["name"]: c["id"] for c in self.env["res.country"].search_read([], ["name"])}

        for rec in self.env["res.partner"].search([]):
            if not rec.hs_object_id or rec.hs_object_id not in hub_ids:
                continue
            hub_map = {h.id: h for h in hubspot_contacts}
            hub_record = hub_map.get(rec.hs_object_id)
            if not hub_record:
                continue
            last_hub_updated = hub_record.updated_at.astimezone(timezone.utc).replace(tzinfo=None) if getattr(hub_record, "updated_at", None) else None
            if last_hub_updated and last_hub_updated > (self.odoo_contact_last_updated or rec.write_date):
                data_to_update = {
                    "name": (hub_record.properties.get("firstname") or "") + (" " + hub_record.properties.get("lastname") if hub_record.properties.get("lastname") else ""),
                    "email": hub_record.properties.get("email") or hub_record.properties.get("odoo_mail"),
                    "phone": hub_record.properties.get("phone"),
                    "function": hub_record.properties.get("jobtitle"),
                    "website": hub_record.properties.get("website"),
                    "street": hub_record.properties.get("address"),
                    "city": hub_record.properties.get("city"),
                    "zip": hub_record.properties.get("zip"),
                    "state_id": state_dict.get(str(hub_record.properties.get("state")), None),
                    "country_id": country_dict.get(str(hub_record.properties.get("country")), None),
                    "image_1920": base64.b64decode(hub_record.properties.get("odoo_image_string")) if hub_record.properties.get("odoo_image_string") else None,
                }
                try:
                    with self.env.cr.savepoint():
                        rec.write(data_to_update)
                        update_success += 1
                except Exception as e:
                    _logger.warning("Failed to update Odoo partner from HubSpot: %s", str(e))

        self.odoo_contact_last_updated = datetime.now()
        if update_success > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": self.odoo_contact_last_updated,
                "res_model_id": self.env.ref("base.model_res_partner").id,
                "sync_mode": "odoo_updated",
                "state": "success",
                "count": update_success,
            })
        return update_success


    def action_export_company(self):
        """
        Export Odoo companies to HubSpot v3.
        Uses Odoo website as HubSpot 'domain' (Option 1).
        """
        client = self._get_hubspot_client()
        base_url = self._hubspot_base()
        headers = self._hubspot_headers()

        hub_ids = []
        try:
            for rec in client.crm.companies.get_all():
                hs_id = rec.properties.get("hs_object_id") or rec.id
                if hs_id:
                    hub_ids.append(hs_id)
        except Exception:
            has_more = True
            after = None
            page_count = 0
            while has_more:
                page_count += 1
                url = f"{base_url}/crm/v3/objects/companies"
                params = {"limit": 100}
                if after:
                    params["after"] = after
                r = requests.get(url, headers=headers, params=params, timeout=15)
                if not r.ok:
                    break
                data = r.json()
                hub_ids.extend([item.get("id") for item in data.get("results", []) if item.get("id")])
                after = data.get("paging", {}).get("next", {}).get("after")
                has_more = bool(after)
                if page_count >= 20:
                    break

        odoo_companies = self.env["res.company"].search([])
        success_count = 0
        for rec in odoo_companies:
            if not rec.hs_object_id or rec.hs_object_id not in hub_ids:
                props = {
                    "name": rec.name,
                    "domain": rec.website or "",
                    "description": rec.company_details or "",
                    "phone": rec.phone or "",
                    "address": (rec.street or "") + ("," + rec.street2 if rec.street2 else ""),
                    "city": rec.city or "",
                    "state": rec.state_id.name if rec.state_id else "",
                    "zip": rec.zip or "",
                    "country": rec.country_id.name if rec.country_id else "",
                    "industry": "",
                }
                try:
                    api_response = client.crm.companies.basic_api.create(simple_public_object_input_for_create=SimplePublicObjectInput(props))
                    if api_response:
                        new_id = api_response.properties.get("hs_object_id") or api_response.id
                        try:
                            with self.env.cr.savepoint():
                                rec.write({"hs_object_id": new_id, "sync_mode": "export"})
                                success_count += 1
                        except Exception as e:
                            _logger.warning("Failed to update company %s after export: %s", rec.name, str(e))
                except Exception as e:
                    # Handle duplicate company (CONFLICT)
                    error_body = getattr(e, 'body', '')
                    if 'CONFLICT' in str(e) or (error_body and 'CONFLICT' in error_body):
                        # Attempt to extract Existing ID from error message
                        # Example: "Company already exists. Existing ID: 12345"
                        err_msg = error_body if error_body else str(e)
                        if "Existing ID:" in err_msg:
                            existing_id = err_msg.split("Existing ID:")[-1].split('"')[0].split('}')[0].strip(' "')
                            if existing_id:
                                try:
                                    with self.env.cr.savepoint():
                                        rec.write({"hs_object_id": existing_id, "sync_mode": "export"})
                                        success_count += 1
                                except Exception as e:
                                    _logger.warning("Failed to update company %s with existing ID: %s", rec.name, str(e))
                                continue
                    _logger.warning("Failed to export company %s: %s", rec.name, str(e))

        self.company_last_exported = datetime.now()
        if success_count > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": self.company_last_exported,
                "res_model_id": self.env.ref("base.model_res_company").id,
                "sync_mode": "export",
                "state": "success",
                "count": success_count,
            })
        return success_count

    def action_import_company(self):
        """
        Import HubSpot companies into Odoo.
        """
        client = self._get_hubspot_client()
        needed_fields = ["name", "domain", "website", "description", "phone", "city", "state", "country", "zip"]
        try:
            hub_companies = client.crm.companies.get_all(properties=needed_fields)
        except Exception as e:
            raise AccessError(_("Failed to fetch HubSpot companies: %s") % str(e))

        existing_hs = self.env["res.company"].search([]).mapped("hs_object_id")
        companies_to_create = []
        success_count = 0

        state_dict = {s["name"]: s["id"] for s in self.env["res.country.state"].search_read([], ["name"])}
        country_dict = {c["name"]: c["id"] for c in self.env["res.country"].search_read([], ["name"])}

        for rec in hub_companies:
            hs_id = rec.properties.get("hs_object_id") or rec.id
            if not hs_id:
                continue
            if hs_id not in existing_hs:
                name = rec.properties.get("name") or "Company"
                existing_company = self.env["res.company"].search([("name", "=", name)], limit=1)
                if existing_company:
                    if not existing_company.hs_object_id:
                        try:
                            with self.env.cr.savepoint():
                                existing_company.write({"hs_object_id": hs_id, "sync_mode": "import"})
                                success_count += 1
                        except Exception as e:
                            _logger.warning("Failed to link existing company %s: %s", name, str(e))
                    continue

                companies_to_create.append({
                    "name": name,
                    "website": rec.properties.get("domain") or rec.properties.get("website"),
                    "company_details": rec.properties.get("description"),
                    "phone": rec.properties.get("phone"),
                    "city": rec.properties.get("city"),
                    "state_id": state_dict.get(str(rec.properties.get("state")), None),
                    "country_id": country_dict.get(str(rec.properties.get("country")), None),
                    "zip": rec.properties.get("zip"),
                    "hs_object_id": hs_id,
                    "sync_mode": "import"
                })
                success_count += 1

        if companies_to_create:
            self.env["res.company"].sudo().create(companies_to_create)

        if success_count > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": datetime.now(),
                "res_model_id": self.env.ref("base.model_res_company").id,
                "sync_mode": "import",
                "state": "success",
                "count": success_count,
            })
        self.company_last_imported = datetime.now()
        return success_count

    def action_update_hub_company(self):
        """
        Update HubSpot companies based on Odoo changes (batch update).
        """
        client = self._get_hubspot_client()
        try:
            hub_companies = client.crm.companies.get_all()
        except Exception as e:
            raise AccessError(_("Failed to get HubSpot companies for update: %s") % str(e))

        odoo_companies = self.env["res.company"].search([])
        odoo_ids = odoo_companies.mapped("hs_object_id")
        data_to_update = []
        update_success = 0

        for rec in hub_companies:
            hs_id = rec.properties.get("hs_object_id") or rec.id
            if not hs_id:
                continue
            if hs_id in odoo_ids:
                odoo_rec = self.env["res.company"].search([("hs_object_id", "=", hs_id)], limit=1)
                last_hub_updated = rec.updated_at.astimezone(timezone.utc).replace(tzinfo=None) if getattr(rec, "updated_at", None) else None
                if odoo_rec and (odoo_rec.write_date and (odoo_rec.write_date > (self.hub_company_last_updated or last_hub_updated))):
                    props = {
                        "name": odoo_rec.name,
                        "domain": odoo_rec.website or "",
                        "description": odoo_rec.company_details or "",
                        "phone": odoo_rec.phone or "",
                        "address": (odoo_rec.street or "") + ("," + odoo_rec.street2 if odoo_rec.street2 else ""),
                        "city": odoo_rec.city or "",
                        "state": odoo_rec.state_id.name if odoo_rec.state_id else "",
                        "zip": odoo_rec.zip or "",
                        "country": odoo_rec.country_id.name if odoo_rec.country_id else "",
                    }
                    data_to_update.append({"id": hs_id, "properties": props})
                    update_success += 1

        if data_to_update:
            try:
                client.crm.companies.batch_api.update(batch_input_simple_public_object_batch_input=CompanyBatchInput(data_to_update))
            except Exception as e:
                _logger.warning("Failed to batch update companies: %s", str(e))

        self.hub_company_last_updated = datetime.now()
        if update_success > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": self.hub_company_last_updated,
                "res_model_id": self.env.ref("base.model_res_company").id,
                "sync_mode": "hub_updated",
                "state": "success",
                "count": update_success,
            })
        return update_success

    def action_update_odoo_company(self):
        """
        Update Odoo companies based on HubSpot changes.
        """
        client = self._get_hubspot_client()
        needed_fields = ["hs_object_id", "name", "domain", "website", "description", "phone", "city", "state", "country", "zip"]
        try:
            hub_companies = client.crm.companies.get_all(properties=needed_fields)
        except Exception as e:
            raise AccessError(_("Failed to fetch HubSpot companies for import update: %s") % str(e))

        hub_map = {rec.properties.get("hs_object_id") or rec.id: rec for rec in hub_companies}
        update_success = 0

        state_dict = {s["name"]: s["id"] for s in self.env["res.country.state"].search_read([], ["name"])}
        country_dict = {c["name"]: c["id"] for c in self.env["res.country"].search_read([], ["name"])}

        odoo_companies = self.env["res.company"].search([])
        for rec in odoo_companies:
            if not rec.hs_object_id:
                continue
            hub_rec = hub_map.get(rec.hs_object_id)
            if not hub_rec:
                continue
            last_hub_updated = hub_rec.updated_at.astimezone(timezone.utc).replace(tzinfo=None) if getattr(hub_rec, "updated_at", None) else None
            if last_hub_updated and last_hub_updated > rec.write_date:
                vals = {
                    "name": hub_rec.properties.get("name"),
                    "website": hub_rec.properties.get("domain") or hub_rec.properties.get("website"),
                    "company_details": hub_rec.properties.get("description"),
                    "phone": hub_rec.properties.get("phone"),
                    "city": hub_rec.properties.get("city"),
                    "state_id": state_dict.get(str(hub_rec.properties.get("state")), None),
                    "country_id": country_dict.get(str(hub_rec.properties.get("country")), None),
                    "zip": hub_rec.properties.get("zip"),
                }
                try:
                    with self.env.cr.savepoint():
                        rec.write(vals)
                        update_success += 1
                except Exception as e:
                    _logger.warning("Failed to update Odoo company from HubSpot: %s", str(e))

        self.odoo_company_last_updated = datetime.now()
        if update_success > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": self.odoo_company_last_updated,
                "res_model_id": self.env.ref("base.model_res_company").id,
                "sync_mode": "odoo_updated",
                "state": "success",
                "count": update_success,
            })
        return update_success


    def _get_default_pipeline_and_stage_map(self):
        """
        Auto-detect pipeline and stage IDs from HubSpot.
        Returns: pipeline_id, mapping of stage name -> stage_id
        """
        client = self._get_hubspot_client()
        try:
            pipelines = client.crm.pipelines.pipelines_api.get_all(object_type="deals").results
        except Exception as e:
            _logger.warning("Failed to fetch HubSpot pipelines: %s", str(e))
            pipelines = []

        if pipelines:
            pipeline = pipelines[0]
            pipeline_id = pipeline.id
            stage_map = {}
            for stage in pipeline.stages:
                stage_name = getattr(stage, "label", None) or getattr(stage, "displayName", None) or getattr(stage, "label", None)
                if not stage_name:
                    stage_name = stage.id
                stage_map[stage_name.lower()] = stage.id
            return pipeline_id, stage_map
        return None, {}

    def action_export_deals(self):
        """
        Export Odoo deals (crm.lead) to HubSpot. Uses auto-detected pipeline/stage ids.
        """
        client = self._get_hubspot_client()
        pipeline_id, stage_map = self._get_default_pipeline_and_stage_map()

        odoo_deals = self.env["crm.lead"].search([])
        existing_deal_ids = []
        success_count = 0

        try:
            for d in client.crm.deals.get_all():
                existing_deal_ids.append(d.properties.get("hs_object_id") or d.id)
        except Exception:
            pass


        fallback_mapping = {
            "new": "appointmentscheduled",
            "qualified": "qualifiedtobuy",
            "proposition": "presentationscheduled",
            "won": "closedwon",
            "lost": "closedlost",
        }

        for rec in odoo_deals:
            if not rec.hs_object_id or rec.hs_object_id not in existing_deal_ids:
                closedate = ""
                if rec.date_deadline:
                    closedate = datetime.combine(rec.date_deadline, datetime.min.time()).astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                # match stage name(s)
                hub_stage_id = None
                if rec.stage_id and rec.stage_id.name:
                    mapped = stage_map.get(rec.stage_id.name.lower())
                    if mapped:
                        hub_stage_id = mapped
                    else:
                        hub_stage_id = stage_map.get(fallback_mapping.get(rec.stage_id.name.lower()))
                props = {
                    "dealname": rec.name or "Deal",
                    "amount": rec.expected_revenue or None,
                    "closedate": closedate or None,
                    "dealstage": hub_stage_id,
                    "pipeline": pipeline_id,
                }
                try:
                    api_response = client.crm.deals.basic_api.create(simple_public_object_input_for_create=SimplePublicObjectInput(props))
                    if api_response:
                        new_id = api_response.properties.get("hs_object_id") or api_response.id
                        try:
                            with self.env.cr.savepoint():
                                rec.write({"hs_object_id": new_id, "sync_mode": "export"})
                                success_count += 1
                        except Exception as e:
                            _logger.warning("Failed to update deal %s after export: %s", rec.name, str(e))
                except Exception as e:
                    _logger.warning("Failed to export deal %s: %s", rec.name, str(e))

        self.deals_last_exported = datetime.now()
        if success_count > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": self.deals_last_exported,
                "res_model_id": self.env.ref("crm.model_crm_lead").id,
                "sync_mode": "export",
                "state": "success",
                "count": success_count,
            })
        return success_count

    def action_import_deals(self):
        """
        Import HubSpot deals into Odoo (crm.lead).
        """
        client = self._get_hubspot_client()
        needed_fields = ["dealname", "amount", "closedate", "hs_priority", "dealtype", "pipeline", "dealstage"]
        try:
            hub_deals = client.crm.deals.get_all(properties=needed_fields)
        except Exception as e:
            raise AccessError(_("Failed to fetch HubSpot deals: %s") % str(e))

        existing = self.env["crm.lead"].search([]).mapped("hs_object_id")
        deals_to_create = []
        success_count = 0

        priority_map = {"low": "1", "medium": "2", "high": "3"}
        type_map = {"newbusiness": "lead", "existingbusiness": "opportunity"}

        for rec in hub_deals:
            hs_id = rec.properties.get("hs_object_id") or rec.id
            if not hs_id:
                continue
            if hs_id not in existing:
                priority = priority_map.get(rec.properties.get("hs_priority"))
                dtype = type_map.get(rec.properties.get("dealtype"), "lead")
                deals_to_create.append({
                    "name": rec.properties.get("dealname") or "Lead",
                    "expected_revenue": rec.properties.get("amount"),
                    "date_deadline": rec.properties.get("closedate"),
                    "priority": priority,
                    "type": dtype,
                    "hs_object_id": hs_id,
                    "sync_mode": "import"
                })
                success_count += 1

        if deals_to_create:
            self.env["crm.lead"].sudo().create(deals_to_create)

        self.deals_last_imported = datetime.now()
        if success_count > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": self.deals_last_imported,
                "res_model_id": self.env.ref("crm.model_crm_lead").id,
                "sync_mode": "import",
                "state": "success",
                "count": success_count,
            })
        return success_count

    def action_update_hub_deals(self):
        """
        Update HubSpot deals based on Odoo changes (batch).
        Uses pipeline/stage auto-detection.
        """
        client = self._get_hubspot_client()
        pipeline_id, stage_map = self._get_default_pipeline_and_stage_map()
        odoo_deals = self.env["crm.lead"].search([])
        odoo_ids = odoo_deals.mapped("hs_object_id")
        try:
            hub_deals = client.crm.deals.get_all()
        except Exception as e:
            raise AccessError(_("Failed to fetch HubSpot deals for update: %s") % str(e))

        hub_by_id = {d.properties.get("hs_object_id") or d.id: d for d in hub_deals}
        update_success = 0
        batch_data = []

        for rec in odoo_deals:
            if not rec.hs_object_id or rec.hs_object_id not in hub_by_id:
                continue
            hub = hub_by_id.get(rec.hs_object_id)
            if not hub:
                continue
            last_hub_updated = hub.updated_at.astimezone(timezone.utc).replace(tzinfo=None) if getattr(hub, "updated_at", None) else None
            if rec.write_date and (rec.write_date > (self.hub_deal_last_updated or last_hub_updated)):
                closedate = ""
                if rec.date_deadline:
                    closedate = datetime.combine(rec.date_deadline, datetime.min.time()).astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                hub_stage_id = stage_map.get(rec.stage_id.name.lower()) if rec.stage_id and rec.stage_id.name else None
                props = {
                    "dealname": rec.name,
                    "amount": rec.expected_revenue or None,
                    "closedate": closedate or None,
                    "dealstage": hub_stage_id,
                    "pipeline": pipeline_id,
                }
                batch_data.append({"id": rec.hs_object_id, "properties": props})
                update_success += 1

        def chunks(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        for chunk in chunks(batch_data, 100):
            try:
                client.crm.deals.batch_api.update(batch_input_simple_public_object_batch_input=BatchInputSimplePublicObjectBatchInput(chunk))
            except Exception as e:
                _logger.warning("Failed to batch update deals: %s", str(e))

        self.hub_deal_last_updated = datetime.now()
        if update_success > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": self.hub_deal_last_updated,
                "res_model_id": self.env.ref("crm.model_crm_lead").id,
                "sync_mode": "hub_updated",
                "state": "success",
                "count": update_success,
            })
        return update_success

    def action_update_odoo_deals(self):
        """
        Update Odoo deals from HubSpot when HubSpot has newer data.
        """
        client = self._get_hubspot_client()
        needed_fields = ["dealname", "hs_object_id", "amount", "closedate", "hs_priority", "dealtype", "pipeline", "dealstage"]
        try:
            hub_deals = client.crm.deals.get_all(properties=needed_fields)
        except Exception as e:
            raise AccessError(_("Failed to fetch HubSpot deals for Odoo update: %s") % str(e))

        hub_map = {rec.properties.get("hs_object_id") or rec.id: rec for rec in hub_deals}
        update_success = 0

        for rec in self.env["crm.lead"].search([]):
            if not rec.hs_object_id or rec.hs_object_id not in hub_map:
                continue
            hub = hub_map.get(rec.hs_object_id)
            last_hub_updated = hub.updated_at.astimezone(timezone.utc).replace(tzinfo=None) if getattr(hub, "updated_at", None) else None
            if last_hub_updated and last_hub_updated > rec.write_date:
                priority_map = {"low": "1", "medium": "2", "high": "3"}
                type_map = {"newbusiness": "lead", "existingbusiness": "opportunity"}
                vals = {
                    "name": hub.properties.get("dealname") or "Lead",
                    "expected_revenue": hub.properties.get("amount"),
                    "date_deadline": hub.properties.get("closedate"),
                    "priority": priority_map.get(hub.properties.get("hs_priority")),
                    "type": type_map.get(hub.properties.get("dealtype")),
                }
                try:
                    with self.env.cr.savepoint():
                        rec.write(vals)
                        update_success += 1
                except Exception as e:
                    _logger.warning("Failed to update Odoo deal from HubSpot: %s", str(e))

        self.odoo_deal_last_updated = datetime.now()
        if update_success > 0:
            self.env["hubspot.sync.history"].sudo().create({
                "date": self.odoo_deal_last_updated,
                "res_model_id": self.env.ref("crm.model_crm_lead").id,
                "sync_mode": "odoo_updated",
                "state": "success",
                "count": update_success,
            })
        return update_success

