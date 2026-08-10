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
from odoo import api, fields, models
from odoo.exceptions import UserError

STATUSES = [
    ('current', 'Current'),
    ('expiring_soon', 'Expiring Soon'),
    ('lapsed', 'Lapsed'),
]


class NhsRegistration(models.Model):
    _name = 'nhs.registration'
    _inherit = ['mail.thread']
    _description = 'Professional Registration'
    _order = 'expiry_date, id'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
    )
    member_id = fields.Many2one(
        'nhs.workforce.member',
        string='Member',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        help="The registered member."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='member_id.company_id',
        store=True,
    )
    regulator_id = fields.Many2one(
        'nhs.regulator',
        string='Regulator',
        required=True,
        tracking=True,
        help="NMC / GMC / HCPC / GPhC / GDC / other."
    )
    registration_number = fields.Char(
        string='Registration Number',
        help="PIN / registration number. Treated as sensitive — officer/manager and the"
             " member only."
    )
    registered_from = fields.Date(
        string='Registered From',
    )
    expiry_date = fields.Date(
        string='Expiry / Renewal Date',
        required=True,
        tracking=True,
    )
    revalidation_date = fields.Date(
        string='Revalidation Date',
        help="Next revalidation/appraisal date (e.g. NMC revalidation, medical appraisal)."
    )
    status = fields.Selection(
        STATUSES,
        string='Status',
        compute='_compute_status',
        store=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Evidence',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    @api.depends('member_id.name', 'regulator_id.code', 'regulator_id.name')
    def _compute_name(self):
        for reg in self:
            regulator = reg.regulator_id.code or reg.regulator_id.name
            reg.name = ' — '.join(filter(None, [reg.member_id.name, regulator]))

    @api.depends('expiry_date')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        lead_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'odoo_nhs_training.due_soon_days', 60))
        for reg in self:
            if not reg.expiry_date:
                reg.status = 'current'
            elif reg.expiry_date < today:
                reg.status = 'lapsed'
            elif (reg.expiry_date - today).days <= lead_days:
                reg.status = 'expiring_soon'
            else:
                reg.status = 'current'

    def unlink(self):
        raise UserError((
            'Professional registrations cannot be deleted, to preserve the compliance'
            ' evidence trail. Archive the record instead.'))

    @api.model
    def _cron_recompute_status(self):
        self.search([])._compute_status()

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template for Professional Registrations',
            'template': '/odoo_nhs_training/static/import_templates/professional_registrations_import_template.xlsx',
        }]

    @api.model
    def _cron_send_expiry_reminders(self):
        template = self.env.ref(
            'odoo_nhs_training.mail_template_registration_expiring', raise_if_not_found=False)
        if not template:
            return
        expiring = self.search([('status', '=', 'expiring_soon')])
        for reg in expiring:
            if reg.member_id.email or (reg.member_id.user_id and reg.member_id.user_id.email):
                template.send_mail(reg.id, force_send=True)
