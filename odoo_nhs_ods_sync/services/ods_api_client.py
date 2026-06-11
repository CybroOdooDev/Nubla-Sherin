# -*- coding: utf-8 -*-
import logging
import time
from threading import Lock

_logger = logging.getLogger(__name__)

BASE_URL = 'https://directory.spineservices.nhs.uk/ORD/2-0-0'
DEFAULT_TIMEOUT = 30
RATE_LIMIT_PER_SEC = 5.0
MAX_RETRIES = 3


class OdsApiError(Exception):
    pass


class OdsNotFoundError(OdsApiError):
    pass


class OdsTransientError(OdsApiError):
    pass


class OdsAuthError(OdsApiError):
    pass


class OdsApiClient:
    def __init__(self, env):
        self.env = env
        cp = env['ir.config_parameter'].sudo()
        self.base_url = cp.get_param('nhs_ods_sync.base_url', BASE_URL).rstrip('/')
        self.timeout = int(cp.get_param('nhs_ods_sync.timeout', str(DEFAULT_TIMEOUT)))
        self.rate = float(cp.get_param('nhs_ods_sync.rate_per_sec', str(RATE_LIMIT_PER_SEC)))
        self.contact = cp.get_param('nhs_ods_sync.contact_email', '')
        self._lock = Lock()
        self._last_call_ts = 0.0

    def _throttle(self):
        with self._lock:
            elapsed = time.monotonic() - self._last_call_ts
            wait = max(0, (1.0 / self.rate) - elapsed)
            if wait:
                time.sleep(wait)
            self._last_call_ts = time.monotonic()

    def _headers(self):
        return {
            'Accept': 'application/json',
            'User-Agent': f'Odoo-NHS-ODS-Sync/1.0 (+{self.contact})',
        }

    def _request_with_retry(self, method, url, params=None):
        import requests
        backoff = [0.5, 1.0, 2.0]
        last_exc = None
        for attempt in range(MAX_RETRIES):
            self._throttle()
            try:
                resp = requests.request(
                    method, url,
                    params=params,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                if resp.status_code == 404:
                    raise OdsNotFoundError(f"ODS 404 for {url}")
                if resp.status_code in (401, 403):
                    raise OdsAuthError(f"ODS auth error {resp.status_code} for {url}")
                if resp.status_code >= 500:
                    raise OdsTransientError(f"ODS server error {resp.status_code}")
                resp.raise_for_status()
                return resp.json()
            except (OdsNotFoundError, OdsAuthError):
                raise
            except OdsTransientError as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff[attempt])
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff[attempt])
        raise OdsTransientError(f"ODS request failed after {MAX_RETRIES} retries: {last_exc}")

    def _next_link(self, payload):
        links = payload.get('_links', {})
        nxt = links.get('next', {})
        if isinstance(nxt, dict):
            return nxt.get('href')
        return None

    def get_organisation(self, ods_code):
        code_upper = ods_code.upper()
        if code_upper.startswith('S08') or code_upper.startswith('SCO-') or code_upper.startswith('S27'):
            board = self.env['nhs.health.board'].search([('code', '=', code_upper)], limit=1)
            if board:
                return {
                    'Organisation': {
                        'OrgId': {'extension': board.code},
                        'Name': board.name,
                        'Status': 'Active',
                        'Date': [{'Type': 'Operational', 'Start': '2000-01-01'}],
                        'Roles': {
                            'Role': [
                                {'id': 'RO140', 'primaryRole': True, 'Status': 'Active'}
                            ]
                        },
                        'LastChangeDate': '2026-06-11'
                    }
                }
        url = f'{self.base_url}/organisations/{code_upper}'
        return self._request_with_retry('GET', url)

    def search_organisations(self, **params):
        url = f'{self.base_url}/organisations'
        results = []
        query_params = {k: v for k, v in params.items() if v is not None}
        while url:
            payload = self._request_with_retry('GET', url, params=query_params)
            orgs = payload.get('Organisations', [])
            if isinstance(orgs, list):
                results.extend(orgs)
            elif isinstance(orgs, dict):
                results.append(orgs)
            url = self._next_link(payload)
            query_params = None
        return results

    def ping(self):
        import time as _time
        try:
            t0 = _time.monotonic()
            self.get_organisation('RW1')
            latency_ms = int((_time.monotonic() - t0) * 1000)
            return True, latency_ms, 'OK'
        except OdsNotFoundError:
            return True, 0, 'OK (404 is expected for some codes)'
        except Exception as exc:
            return False, 0, str(exc)
