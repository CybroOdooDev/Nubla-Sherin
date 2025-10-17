# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError


class HospitalPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if 'appointment_count' in counters:
            values['appointment_count'] = request.env['hospital.appointment'].search_count([]) \
                if request.env['hospital.appointment'].check_access_rights('read', raise_exception=False) else 0

        if 'prescription_count' in counters:
            values['prescription_count'] = request.env['hospital.prescription'].search_count([]) \
                if request.env['hospital.prescription'].check_access_rights('read', raise_exception=False) else 0

        if 'lab_result_count' in counters:
            values['lab_result_count'] = request.env['hospital.lab.request'].search_count([('state', '=', 'completed')]) \
                if request.env['hospital.lab.request'].check_access_rights('read', raise_exception=False) else 0

        return values

    @http.route(['/my/appointments', '/my/appointments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_appointments(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Appointment = request.env['hospital.appointment']

        domain = []

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'appointment_date desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count for pager
        appointment_count = Appointment.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/appointments",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=appointment_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        appointments = Appointment.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'appointments': appointments,
            'page_name': 'appointments',
            'pager': pager,
            'default_url': '/my/appointments',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return request.render("hospital_management.portal_my_appointments", values)

    @http.route(['/my/appointment/<int:appointment_id>'], type='http', auth="user", website=True)
    def portal_appointment_detail(self, appointment_id, access_token=None, **kw):
        try:
            appointment_sudo = self._document_check_access('hospital.appointment', appointment_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'appointment': appointment_sudo,
            'page_name': 'appointments',
        }

        return request.render("hospital_management.portal_appointment_detail", values)

    @http.route(['/my/prescriptions', '/my/prescriptions/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_prescriptions(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        Prescription = request.env['hospital.prescription']

        domain = []

        prescription_count = Prescription.search_count(domain)

        pager = portal_pager(
            url="/my/prescriptions",
            total=prescription_count,
            page=page,
            step=self._items_per_page
        )

        prescriptions = Prescription.search(domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'prescriptions': prescriptions,
            'page_name': 'prescriptions',
            'pager': pager,
        })

        return request.render("hospital_management.portal_my_prescriptions", values)

    @http.route(['/my/lab-results', '/my/lab-results/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_lab_results(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        LabRequest = request.env['hospital.lab.request']

        domain = [('state', '=', 'completed')]

        lab_count = LabRequest.search_count(domain)

        pager = portal_pager(
            url="/my/lab-results",
            total=lab_count,
            page=page,
            step=self._items_per_page
        )

        lab_results = LabRequest.search(domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'lab_results': lab_results,
            'page_name': 'lab_results',
            'pager': pager,
        })

        return request.render("hospital_management.portal_my_lab_results", values)