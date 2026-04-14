# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.session import Session


class FitnessSession(Session):
    """Hook into Odoo logout to auto check-out Fitness members."""

    @http.route('/web/session/logout', type='http', auth='none', readonly=True)
    def logout(self, redirect='/odoo'):
        uid = request.session.uid
        if uid:
            request.env['fitness.attendance'].sudo().portal_check_out_for_user(uid)
        return super().logout(redirect=redirect)

    @http.route('/web/session/destroy', type='jsonrpc', auth='user', readonly=True)
    def destroy(self):
        uid = request.session.uid
        if uid:
            request.env['fitness.attendance'].sudo().portal_check_out_for_user(uid)
        return super().destroy()

