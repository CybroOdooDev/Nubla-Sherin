import base64
import logging
import requests
from odoo import models, fields, exceptions

_logger = logging.getLogger(__name__)


class EpicClinicalNote(models.Model):
    _name = 'epic.clinical.note'
    _description = 'Epic Clinical Note'
    _inherit = ['epic.fhir.mixin']
    _order = 'note_date desc, id desc'

    epic_id = fields.Char(string='Binary FHIR ID', index=True)
    doc_ref_epic_id = fields.Char(string='DocumentReference FHIR ID')
    patient_id = fields.Many2one('epic.patient', string='Patient', ondelete='cascade')
    patient_epic_id = fields.Char(string='Patient Epic ID')

    title = fields.Char(string='Title')
    note_type = fields.Char(string='Note Type')
    note_date = fields.Datetime(string='Note Date')
    author = fields.Char(string='Author')
    status = fields.Selection([
        ('current', 'Current'),
        ('superseded', 'Superseded'),
        ('entered-in-error', 'Entered in Error'),
    ], string='Status', default='current')
    content_type = fields.Char(string='Content Type')
    content_html = fields.Html(string='Content', sanitize=False)
    content_raw = fields.Text(string='Raw Content')

    def action_sync_clinical_notes(self):
        company = self.env.company

        specific_id = (company.epic_clinical_note_search_patient or '').strip()
        if specific_id:
            patient_ids = [specific_id]
        else:
            patient_ids = self.env['epic.patient'].search(
                [('epic_id', '!=', False)]
            ).mapped('epic_id')
            if not patient_ids:
                raise exceptions.UserError(
                    "No patients with Epic FHIR IDs found in Odoo.\n"
                    "Sync patients first, or set a specific Patient Epic ID under "
                    "Settings > Epic Integration > Clinical Notes Sync Defaults."
                )

        doc_scope = (
            'system/DocumentReference.read?category=clinical-notes '
            'system/DocumentReference.search?category=clinical-notes '
            'system/Binary.read'
        )
        access_token, granted_scope = self._epic_get_access_token(company, scope=doc_scope)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        _logger.info("Clinical Notes token scopes granted: %s", granted_scope)

        doc_ref_url = self._epic_fhir_url(company, 'DocumentReference')
        created = updated = skipped = 0
        errors = []

        for patient_epic_id in patient_ids:
            try:
                params = {'patient': patient_epic_id, 'category': 'clinical-notes'}
                if company.epic_clinical_note_search_type:
                    params['type'] = company.epic_clinical_note_search_type
                bundle = self._epic_fhir_get(access_token, doc_ref_url, params=params)
            except Exception as e:
                _logger.warning("Failed to fetch DocumentReferences for patient %s: %s", patient_epic_id, e)
                errors.append(str(e))
                skipped += 1
                continue

            for entry in bundle.get('entry', []):
                resource = entry.get('resource', {})
                if resource.get('resourceType') != 'DocumentReference':
                    continue

                doc_ref_id = resource.get('id')
                if not doc_ref_id:
                    continue

                title, note_type, note_date, author, status = self._parse_doc_ref(resource)
                patient_ref = resource.get('subject', {}).get('reference', '')
                pat_epic_id = patient_ref.split('/')[-1] if '/' in patient_ref else patient_ref
                patient_rec = self.env['epic.patient'].search([('epic_id', '=', pat_epic_id)], limit=1)

                # Get Binary content from content attachments
                binary_id, content_type, content = self._fetch_binary_content(
                    access_token, company, resource
                )

                vals = {
                    'doc_ref_epic_id': doc_ref_id,
                    'title': title,
                    'note_type': note_type,
                    'note_date': note_date,
                    'author': author,
                    'status': status if status in ('current', 'superseded', 'entered-in-error') else 'current',
                    'content_type': content_type,
                    'patient_epic_id': pat_epic_id,
                    'patient_id': patient_rec.id if patient_rec else False,
                }

                if content:
                    if 'html' in (content_type or '').lower():
                        vals['content_html'] = content
                        vals['content_raw'] = content
                    else:
                        vals['content_raw'] = content
                        vals['content_html'] = f'<pre>{content}</pre>'

                existing = self.search([('doc_ref_epic_id', '=', doc_ref_id)], limit=1)
                if existing:
                    if binary_id:
                        vals['epic_id'] = binary_id
                    existing.write(vals)
                    updated += 1
                else:
                    vals['epic_id'] = binary_id or False
                    self.create(vals)
                    created += 1

        if skipped and skipped == len(patient_ids):
            first_error = errors[0] if errors else 'Unknown error'
            raise exceptions.UserError(
                f"Clinical Notes sync failed for all {skipped} patient(s).\n\n"
                f"Error detail:\n{first_error}\n\n"
                f"Token scopes granted: {granted_scope or '(none)'}\n\n"
                "If the error is 403 insufficient_scope, confirm in Epic App Orchard that "
                "DocumentReference.Search (Clinical Notes) (R4), "
                "DocumentReference.Read (Clinical Notes) (R4), and "
                "Binary.Read (Clinical Notes) (R4) are all listed under Incoming APIs "
                "and show status Approved (not just Requested)."
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Clinical Notes Sync Complete',
                'message': (
                    f'Synced clinical notes from Epic across {len(patient_ids)} patient(s). '
                    f'Created: {created}, Updated: {updated}'
                    + (f', Skipped: {skipped}' if skipped else '') + '.'
                ),
                'type': 'success' if not skipped else 'warning',
                'sticky': False,
            },
        }

    def action_fetch_content(self):
        """Fetch/refresh Binary content for this specific note."""
        company = self.env.company
        access_token, _ = self._epic_get_access_token(company)
        if not access_token:
            raise exceptions.UserError("Failed to obtain access token from Epic.")

        for note in self:
            if not note.epic_id:
                raise exceptions.UserError(
                    f"Note '{note.title}' has no Binary FHIR ID — cannot fetch content."
                )
            content_type, content = self._fetch_binary_by_id(access_token, company, note.epic_id)
            if content:
                if 'html' in (content_type or '').lower():
                    note.write({'content_html': content, 'content_raw': content, 'content_type': content_type})
                else:
                    note.write({'content_raw': content, 'content_html': f'<pre>{content}</pre>', 'content_type': content_type})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Content Refreshed',
                'message': 'Clinical note content fetched from Epic.',
                'type': 'success',
                'sticky': False,
            },
        }

    def _parse_doc_ref(self, resource):
        title = resource.get('description', '')
        status = resource.get('status', 'current')

        type_codings = resource.get('type', {}).get('coding', [])
        note_type = type_codings[0].get('display', '') if type_codings else resource.get('type', {}).get('text', '')

        note_date = False
        date_str = resource.get('date') or resource.get('context', {}).get('period', {}).get('start', '')
        if date_str:
            try:
                from dateutil import parser as dateutil_parser
                dt = dateutil_parser.parse(date_str[:19].replace('T', ' '))
                note_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass

        authors = []
        for a in resource.get('author', []):
            display = a.get('display', '')
            if display:
                authors.append(display)
        author = ', '.join(authors) or ''

        if not title and note_type:
            title = note_type

        return title or 'Clinical Note', note_type, note_date, author, status

    def _fetch_binary_content(self, access_token, company, doc_ref_resource):
        """Extract Binary ID from DocumentReference and fetch its content."""
        contents = doc_ref_resource.get('content', [])
        binary_id = None
        content_type = None

        for c in contents:
            attachment = c.get('attachment', {})
            url = attachment.get('url', '')
            content_type = attachment.get('contentType', '')
            if 'Binary/' in url:
                binary_id = url.split('Binary/')[-1]
                break

        if not binary_id:
            return None, content_type, None

        fetched_type, content = self._fetch_binary_by_id(access_token, company, binary_id)
        return binary_id, fetched_type or content_type, content

    def _fetch_binary_by_id(self, access_token, company, binary_id):
        """Fetch Binary resource content by FHIR ID."""
        url = self._epic_fhir_url(company, f'Binary/{binary_id}')
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/fhir+json',
        }
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if not response.ok:
                _logger.warning("Binary fetch failed %s: %s", response.status_code, response.text[:200])
                return None, None

            data = response.json()
            content_type = data.get('contentType', '')
            raw_data = data.get('data', '')

            if raw_data:
                try:
                    decoded = base64.b64decode(raw_data).decode('utf-8', errors='replace')
                    return content_type, decoded
                except Exception:
                    return content_type, raw_data
            return content_type, None
        except Exception as e:
            _logger.warning("Error fetching Binary %s: %s", binary_id, e)
            return None, None
