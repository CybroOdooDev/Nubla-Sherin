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
from odoo.exceptions import ValidationError
from datetime import  timedelta
from dateutil.relativedelta import relativedelta

class NHSComplianceTest(models.Model):
    """Model to record specific, completed statutory tests or inspections and their outcomes."""
    _name = 'nhs.compliance.test'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'A completed statutory test / inspection and its outcome'
    _order = 'test_date desc, id desc'

    name = fields.Char(string='Name', required=True, readonly=True, copy=False, default=lambda self: 'New',
                       help='Auto-generated unique reference for this compliance test record.')
    item_id = fields.Many2one('nhs.compliance.item', string='Compliance Item', required=True,
                              ondelete='cascade',help='The compliance item this test was performed against.')
    test_date = fields.Date(string='Test Date', required=True, default=fields.Date.today,
                            help='The date on which the test or inspection was carried out.')
    performed_by_id = fields.Many2one('res.users', string='Performed By',
                                      help='In-house person who performed it')
    discipline_id = fields.Many2one('nhs.compliance.discipline', related='item_id.discipline_id',
                                    string='Discipline', store=True, readonly=True,
                                    help='The compliance discipline inherited from the compliance item.')
    item_delivery_method = fields.Selection(related='item_id.delivery_method',
                                            string='Item Delivery Method', readonly=True,
                                help='The delivery method (in-house vs contractor) configured on the compliance item.')
    contractor_id = fields.Many2one('nhs.compliance.contractor', related='item_id.contractor_id',
                                    string='Contractor', store=True, readonly=True,
                                    help='Contractor who performed it')
    item_site_id = fields.Many2one('nhs.estate.site', related='item_id.site_id',
                                   string='Item Site', store=True, readonly=True,
                                   help='The site of the compliance item.')
    item_building_id = fields.Many2one('nhs.estate.building', related='item_id.building_id',
                                       string='Item Building', store=True, readonly=True,
                                       help='The building of the compliance item.')
    visit_id = fields.Many2one('nhs.contractor.visit', string='Visit',
                    domain="contractor_id and [('contractor_id', '=', contractor_id), ('site_id', '=', item_site_id), "
                           "('building_id', '=', item_building_id)] or [('id', '=', 0)]",
                    help='The contractor visit this test belongs to')
    outcome = fields.Selection([
        ('pass', 'Pass'),
        ('pass_with_observations', 'Pass with Observations'),
        ('fail', 'Fail'),
        ('remedial_required', 'Remedial Required')
    ], string='Outcome', required=True,
       help='The result of the test: Pass, Pass with Observations, Fail, or Remedial Required.')
    certificate_ref = fields.Char(string='Certificate Reference',
                                   help='The unique reference number of the certificate issued for this test.')
    issuing_body = fields.Char(string='Issuing Body',
                               help='The organisation or body that issued the test certificate.')
    certificate_date = fields.Date(string='Certificate Date',
                                   help='The date the certificate was issued.')
    certificate_expiry = fields.Date(string='Certificate Expiry',
                                     help='The date on which the certificate expires and must be renewed.')
    readings = fields.Text(string='Readings', help='Readings like water temperatures, EICR codes C1/C2/C3/FI.')
    notes = fields.Text(string='Notes', help='Observations / findings')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments',
                                       help='Certificate, report, photos')
    remedial_ids = fields.One2many('nhs.compliance.remedial', 'test_id', string='Remedials',
                    help='Remedial actions raised as a result of a failed or remedial-required outcome on this test.')
    active = fields.Boolean(string='Active', default=True,
                            help='Uncheck to archive this test record without deleting it.')
    due_date = fields.Date(string='Target Due Date',
                           help='The target date by which this test should have been completed.')
    completion_status = fields.Selection([
        ('on_time', 'On Time'),
        ('late', 'Late')
    ], string='Completion Status', compute='_compute_completion_status', store=True,
       help='Indicates whether the test was completed on time or late relative to its target due date.')
    remedial_count = fields.Integer(string='Open Remedial', compute='_compute_remedial_count',
                                    help='Number of remedial actions raised from this test.')

    @api.constrains('certificate_ref', 'attachment_ids')
    def _check_certificate_attachment(self):
        """Validate that if a certificate reference is provided, at least one attachment exists."""
        for test in self:
            if test.certificate_ref and not test.attachment_ids:
                raise ValidationError(
                    "Please attach the certificate document(s) when providing a certificate reference.\n"
                    "Certificate Reference: %s" % test.certificate_ref
                )

    @api.onchange('item_id')
    def _onchange_item_id_contractor(self):
        """Clear visit_id if it does not match the contractor of the new compliance item."""
        for test in self:
            new_contractor = test.item_id.contractor_id if test.item_id else False
            if test.visit_id and test.visit_id.contractor_id != new_contractor:
                test.visit_id = False

    @api.onchange('test_date')
    def _onchange_test_date(self):
        """Auto-set the target due date to 5 days after the test date when the test date changes."""
        if self.test_date:
            self.due_date = self.test_date + timedelta(days=5)
        return

    @api.depends('due_date', 'outcome')
    def _compute_completion_status(self):
        """Determine whether the test was completed on time or late based on the due date."""
        today = fields.Date.today()
        for test in self:
            if not test.outcome:
                test.completion_status = False
            elif not test.due_date:
                test.completion_status = 'on_time'
            elif today > test.due_date:
                test.completion_status = 'late'
            else:
                test.completion_status = 'on_time'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-generate a sequence reference, set a default due date, and update the
         parent compliance item."""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq = self.env['ir.sequence'].next_by_code('nhs.compliance.test') or 'New'
                vals['name'] = seq
            if not vals.get('due_date'):
                test_date_val = fields.Date.to_date(vals.get('test_date') or fields.Date.today())
                vals['due_date'] = test_date_val + timedelta(days=5)
        tests = super(NHSComplianceTest, self).create(vals_list)
        for test in tests:
            test._update_parent_item()
        return tests

    @api.constrains('test_date')
    def _check_test_date(self):
        """Validate that the test date is not set in the future."""
        for test in self:
            if test.test_date and test.test_date > fields.Date.today():
                raise ValidationError('Test date cannot be in the future.')

    def write(self, vals):
        """Override write to prevent outcome changes once set, and to re-sync the parent compliance item on
        relevant field updates."""
        if 'outcome' in vals:
            for test in self:
                if test.outcome and test.outcome != vals['outcome']:
                    raise ValidationError("Once a test outcome is set, it cannot be changed.")
        if 'item_id' in vals and 'due_date' not in vals:
            item = self.env['nhs.compliance.item'].browse(vals['item_id'])
            vals['due_date'] = item.next_due_date
        result = super(NHSComplianceTest, self).write(vals)
        for test in self:
            if any(field in vals for field in ['outcome', 'test_date']):
                test._update_parent_item()
        return result

    def _update_parent_item(self):
        """Synchronise the parent compliance item's status and next due date based on this test's outcome.
        For passing outcomes ('pass' or 'pass_with_observations'), the method
        recomputes the last_completed_date, applies any grace-period tolerance
        so that tests performed slightly early lock on to the original schedule,
        calculates the next_due_date from the frequency settings, and closes
        any open preventive maintenance requests linked to the item.
        For failing outcomes ('fail' or 'remedial_required'), the parent item's
        status is set to 'failed'.
        """
        for test in self:
            item = test.item_id
            if test.outcome in ['pass', 'pass_with_observations']:
                prev_due_date = item.next_due_date
                item._compute_last_completed_date()
                base_date = item.last_completed_date or test.test_date
                if prev_due_date and item.grace_days and base_date:
                    early_limit = prev_due_date - timedelta(days=item.grace_days)
                    if early_limit <= base_date <= prev_due_date:
                        base_date = prev_due_date
                if item.frequency_unit == 'day':
                    delta = timedelta(days=item.frequency_value)
                elif item.frequency_unit == 'week':
                    delta = timedelta(weeks=item.frequency_value)
                elif item.frequency_unit == 'month':
                    delta = relativedelta(months=item.frequency_value)
                elif item.frequency_unit == 'year':
                    delta = relativedelta(years=item.frequency_value)
                else:
                    delta = relativedelta(months=1)
                raw_due_date = base_date + delta
                item.next_due_date = item._adjust_to_working_day(raw_due_date)
                if not self.env.context.get('skip_maintenance_sync'):
                    active_requests = self.env['maintenance.request'].search([
                        ('equipment_id', '=', item.equipment_id.id),
                        ('maintenance_type', '=', 'preventive'),
                        ('stage_id.done', '=', False)
                    ])
                    if active_requests:
                        done_stage = self.env['maintenance.stage'].search([('done', '=', True)], limit=1)
                        if done_stage:
                            active_requests.with_context(skip_maintenance_sync=True).write({
                                'stage_id': done_stage.id,
                                'close_date': fields.Date.today(),
                            })
            elif test.outcome in ['fail', 'remedial_required']:
                item.status = 'failed'

    def action_raise_remedial(self):
        """Open a form to raise a new remedial action pre-populated with this test's compliance item and
        a 30-day deadline."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Raise Remedial Action',
            'res_model': 'nhs.compliance.remedial',
            'view_mode': 'form',
            'context': {
                'default_item_id': self.item_id.id,
                'default_test_id': self.id,
                'default_priority': 'high',
                'default_due_date': fields.Date.today() + timedelta(days=30),
            },
            'target': 'new',
        }

    def unlink(self):
        """Prevent deletion of compliance test records to preserve the statutory audit trail."""
        from odoo.exceptions import UserError
        raise UserError("Compliance test records cannot be deleted to preserve the statutory audit trail. "
                        "Please archive them instead if they are no longer needed.")

    @api.depends('remedial_ids')
    def _compute_remedial_count(self):
        """Compute the number of remedial actions linked to this test."""
        for test in self:
            if test.remedial_ids:
                test.remedial_count = len(test.remedial_ids)
            else:
                test.remedial_count = 0

    def action_view_compliance_remedial(self):
        """Open a list/form view of remedial actions for the parent compliance item."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Remedial Actions',
            'res_model': 'nhs.compliance.remedial',
            'view_mode': 'list,form',
            'domain': [('item_id', '=', self.item_id.id)],
            'context': {'default_test_id': self.id},
        }

    def action_view_documents(self):
        """Open documents attached to this test"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'nhs.compliance.test'),
                ('res_id', '=', self.id)
            ],
            'context': {
                'default_res_model': 'nhs.compliance.test',
                'default_res_id': self.id,
            }
        }

    @api.model
    def _check_test_certificate_expiry(self):
        """Scheduled action to check for test certificates expiring within the next 30 days and
         send email notifications and to-do activities."""
        from datetime import timedelta
        today = fields.Date.today()
        warning_limit = today + timedelta(days=30)
        expiring_tests = self.search([
            ('certificate_expiry', '!=', False),
            ('certificate_expiry', '<=', warning_limit),
            ('certificate_expiry', '>=', today),
            ('active', '=', True)
        ])
        template = self.env.ref('odoo_nhs_estate_compliance.mail_template_test_certificate_expiry',
                                raise_if_not_found=False)
        for test in expiring_tests:
            item = test.item_id
            user = item.responsible_person_id or self.env.user
            if template:
                email_to = user.email or self.env.company.email or 'admin@example.com'
                template.send_mail(test.id, email_values={'email_to': email_to}, force_send=True)
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'nhs.compliance.test'),
                ('res_id', '=', test.id),
                ('user_id', '=', user.id),
            ])
            if not existing:
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id if activity_type else False,
                    'res_model_id': self.env['ir.model']._get_id('nhs.compliance.test'),
                    'res_id': test.id,
                    'user_id': user.id,
                    'summary': f"Test Certificate Expiring soon: {test.name}",
                    'note': f"The certificate for compliance item {item.name} expires on {test.certificate_expiry}.",
                    'date_deadline': test.certificate_expiry or today + timedelta(days=30),
                })

    @api.model
    def _send_weekly_test_digest(self):
        """Send a weekly email digest summarising tests performed in the last 7 days and
        certificates expiring within 30 days."""
        recipients = self.env['ir.config_parameter'].sudo().get_param('odoo_nhs_estate_compliance.digest_recipients')
        if not recipients:
            dh_assignments = self.env['nhs.duty.assignment'].search([('duty_role_id.code', '=', 'DH')])
            emails = dh_assignments.mapped('person_id.email')
            recipients = ",".join([e for e in emails if e]) or self.env.company.email or 'admin@example.com'
        today = fields.Date.today()
        last_week = today - timedelta(days=7)
        recent_tests = self.search([
            ('test_date', '>=', last_week),
            ('test_date', '<=', today),
            ('active', '=', True)
        ])
        total_tests = len(recent_tests)
        passed_tests = len(recent_tests.filtered(lambda t: t.outcome in ['pass', 'pass_with_observations']))
        failed_tests = len(recent_tests.filtered(lambda t: t.outcome in ['fail', 'remedial_required']))
        pass_rate = (passed_tests / total_tests * 100.0) if total_tests else 0.0
        expiring_tests = self.search([
            ('certificate_expiry', '!=', False),
            ('certificate_expiry', '<=', today + timedelta(days=30)),
            ('certificate_expiry', '>=', today),
            ('active', '=', True)
        ], order='certificate_expiry ASC')
        expiring_rows = ""
        if expiring_tests:
            for test in expiring_tests:
                days_remaining = (test.certificate_expiry - today).days if test.certificate_expiry else 0
                if days_remaining <= 7:
                    status_class = 'status-urgent'
                    status_label = '<span class="status-label status-urgent-label">URGENT</span>'
                elif days_remaining <= 14:
                    status_class = 'status-warning'
                    status_label = '<span class="status-label status-warning-label">WARNING</span>'
                else:
                    status_class = 'status-normal'
                    status_label = '<span class="status-label status-ok-label">OK</span>'
                item_name = test.item_id.name if test.item_id else 'No Item'
                expiring_rows += f"""
                <tr class="{status_class}">
                    <td><strong>{test.name}</strong></td>
                    <td>{item_name}</td>
                    <td>{test.certificate_expiry.strftime('%Y-%m-%d')}</td>
                    <td>{days_remaining} days</td>
                    <td>{status_label}</td>
                </tr>
                """
            expiring_html = f"""
            <table>
                <thead>
                    <tr>
                        <th>Certificate</th>
                        <th>Compliance Item</th>
                        <th>Expiry Date</th>
                        <th>Days Remaining</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {expiring_rows}
                </tbody>
            </table>
            """
        else:
            expiring_html = '<p class="empty-message">✅ No certificates expiring in the next 30 days.</p>'
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8019')
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    color: #333;
                    line-height: 1.6;
                    background-color: #f5f7fa;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 750px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #1a237e, #0d47a1);
                    color: white;
                    padding: 25px 30px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 22px;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                }}
                .header .subtitle {{
                    margin: 5px 0 0 0;
                    opacity: 0.85;
                    font-size: 14px;
                }}
                .header .date {{
                    float: right;
                    margin-top: -38px;
                    opacity: 0.85;
                    font-size: 13px;
                }}
                .content {{
                    padding: 25px 30px;
                }}
                .summary-grid {{
                    display: flex;
                    gap: 12px;
                    margin: 15px 0 25px 0;
                }}
                .summary-card {{
                    flex: 1;
                    padding: 15px 12px;
                    text-align: center;
                    border-radius: 6px;
                    background: #f8f9fa;
                    border-top: 3px solid #6c757d;
                }}
                .summary-card.total {{
                    border-top-color: #1976d2;
                    background: #e3f2fd;
                }}
                .summary-card.passed {{
                    border-top-color: #2e7d32;
                    background: #e8f5e9;
                }}
                .summary-card.failed {{
                    border-top-color: #c62828;
                    background: #ffebee;
                }}
                .summary-card .number {{
                    font-size: 26px;
                    font-weight: bold;
                    display: block;
                }}
                .summary-card .label {{
                    font-size: 12px;
                    color: #555;
                    font-weight: 500;
                }}
                .pass-rate-bar {{
                    background: #e9ecef;
                    border-radius: 6px;
                    padding: 3px;
                    margin: 5px 0 20px 0;
                    height: 22px;
                }}
                .pass-rate-bar .fill {{
                    background: #2e7d32;
                    height: 100%;
                    border-radius: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    min-width: 40px;
                    width: {pass_rate:.0f}%;
                }}
                .pass-rate-bar .fill.low {{ background: #c62828; }}
                .pass-rate-bar .fill.medium {{ background: #f57c00; }}
                .section-title {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #1a237e;
                    margin: 25px 0 12px 0;
                    padding-bottom: 8px;
                    border-bottom: 2px solid #e8eaf6;
                }}
                .section-title .badge {{
                    display: inline-block;
                    padding: 2px 10px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                    margin-left: 8px;
                }}
                .badge-warning {{
                    background: #f57c00;
                    color: white;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0 15px 0;
                    font-size: 14px;
                    border-radius: 6px;
                    overflow: hidden;
                }}
                th {{
                    background: #263238;
                    color: white;
                    padding: 10px 14px;
                    text-align: left;
                    font-weight: 600;
                    font-size: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                td {{
                    padding: 10px 14px;
                    border-bottom: 1px solid #e8eaf6;
                    vertical-align: middle;
                }}
                tr:hover {{
                    background: #f5f5f5;
                }}
                tr:last-child td {{
                    border-bottom: none;
                }}
                .status-urgent {{
                    background: #ffebee;
                }}
                .status-urgent td:first-child {{
                    border-left: 4px solid #c62828;
                }}
                .status-warning {{
                    background: #fff3e0;
                }}
                .status-warning td:first-child {{
                    border-left: 4px solid #f57c00;
                }}
                .status-normal {{
                    background: #e8f5e9;
                }}
                .status-normal td:first-child {{
                    border-left: 4px solid #2e7d32;
                }}
                .status-label {{
                    display: inline-block;
                    padding: 2px 10px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                    text-align: center;
                }}
                .status-urgent-label {{
                    background: #c62828;
                    color: white;
                }}
                .status-warning-label {{
                    background: #f57c00;
                    color: white;
                }}
                .status-ok-label {{
                    background: #2e7d32;
                    color: white;
                }}
                .empty-message {{
                    text-align: center;
                    color: #999;
                    padding: 15px;
                    font-style: italic;
                }}
                .login-link {{
                    display: block;
                    text-align: center;
                    margin: 25px 0 10px 0;
                    padding: 12px;
                    background: #e8eaf6;
                    border-radius: 6px;
                }}
                .login-link a {{
                    color: #1a237e;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 15px;
                }}
                .login-link a:hover {{
                    text-decoration: underline;
                }}
                .footer {{
                    padding: 15px 30px;
                    background: #f8f9fa;
                    text-align: center;
                    font-size: 12px;
                    color: #999;
                    border-top: 1px solid #e8eaf6;
                }}
                @media only screen and (max-width: 600px) {{
                    .summary-grid {{
                        flex-direction: column;
                    }}
                    .header .date {{
                        float: none;
                        margin-top: 8px;
                        display: block;
                    }}
                    table {{
                        font-size: 12px;
                    }}
                    td, th {{
                        padding: 8px 10px;
                    }}
                    .content {{
                        padding: 15px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Estates Compliance Weekly Test Digest</h1>
                    <div class="subtitle">Test Summary & Certificate Expiry Report</div>
                    <div class="date">Week Ending {today.strftime('%B %d, %Y')}</div>
                </div>
                <div class="content">
                    <div style="margin-bottom: 5px;">
                        <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 500;">
                            <span>Test Pass Rate : </span>
                            <span>{pass_rate:.0f}%</span>
                        </div>
                        <div class="pass-rate-bar">
                            <div class="fill {('low' if pass_rate < 60 else 'medium' if pass_rate < 80 else '')}" 
                                 style="width: {pass_rate:.0f}%;">
                                {pass_rate:.0f}%
                            </div>
                        </div>
                    </div>
                    <div class="summary-grid">
                        <div class="summary-card total">
                            <span class="number">{total_tests}</span>
                            <span class="label">Total Tests Performed</span>
                        </div>
                        <div class="summary-card passed">
                            <span class="number">{passed_tests}</span>
                            <span class="label">✅ Passed</span>
                        </div>
                        <div class="summary-card failed">
                            <span class="number">{failed_tests}</span>
                            <span class="label">❌ Failed / Remedial Required</span>
                        </div>
                    </div>
                    <div class="section-title">
                        ⚠️ Expiring Certificates (Next 30 Days)
                        <span class="badge badge-warning">{len(expiring_tests)} Certificates</span>
                    </div>
                    {expiring_html}
                    <div class="login-link">
                        <a href="{base_url}/web">🔑 Log in to Odoo to view detailed compliance records</a>
                    </div>
                </div>

                <div class="footer">
                    Estates Compliance System • Automated Report • {today.strftime('%B %d, %Y at %H:%M')}
                </div>
            </div>
        </body>
        </html>
        """
        mail_values = {
            'email_to': recipients,
            'subject': f"Estates Compliance Weekly Test Digest - {today.strftime('%Y-%m-%d')}",
            'body_html': html_body,
        }
        self.env['mail.mail'].sudo().create(mail_values).send()
