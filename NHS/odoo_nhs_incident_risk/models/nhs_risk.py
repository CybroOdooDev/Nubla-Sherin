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
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

SCORE_BANDS = [
    (range(1, 4), 'low', 'success'),
    (range(4, 7), 'moderate', 'warning'),
    (range(8, 13), 'high', 'danger'),
    (range(15, 26), 'extreme', 'danger'),
]
REVIEW_DAYS = {'extreme': 30, 'high': 90, 'moderate': 180, 'low': 365}

SCORE_FIELDS = [
    ('inherent_consequence', 'inherent_likelihood', 'inherent_rating', 'inherent_band'),
    ('current_consequence', 'current_likelihood', 'current_rating', 'current_band'),
    ('target_consequence', 'target_likelihood', 'target_rating', 'target_band'),
]

SCORE_SEL = [(str(i), str(i)) for i in range(1, 6)]
BAND_SEL = [('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('extreme', 'Extreme')]


def _band(rating):
    """Return the risk band name for the given consequence x likelihood rating."""
    for r, band, _ in SCORE_BANDS:
        if rating in r:
            return band
    return 'low'


class NhsRisk(models.Model):
    """Risk register entry scored on the 5x5 NPSA consequence/likelihood matrix."""
    _name = 'nhs.risk'
    _description = 'Risk Register Entry (5×5 NPSA Matrix)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'current_rating desc, id'

    name = fields.Char(string='Reference', required=True, readonly=True,
                       copy=False, default='New',
                       help='Auto-generated unique reference for this risk entry (e.g. RISK/2026/00001).')
    title = fields.Char(string='Risk Title', required=True,
                        help='A concise summary of the risk, suitable for board-level reporting '
                             '(e.g. "Risk of medication error in high-dependency unit").')
    cause = fields.Text(string='Cause (IF)', required=True,
                        help='Describe the root cause or trigger condition using the format: '
                             '"IF [cause]..." — what must happen for this risk to materialise.')
    event = fields.Text(string='Event (THEN)', required=True,
                        help='Describe the risk event using the format: '
                             '"THEN [event]..." — what actually goes wrong if the cause is present.')
    effect = fields.Text(string='Effect (RESULTING IN)', required=True,
                         help='Describe the impact using the format: '
                              '"RESULTING IN [effect]..." — the harm, loss, or consequence if the event occurs.')
    category_id = fields.Many2one('nhs.risk.category', string='Category', required=True,
                                  help='The risk category (e.g. Clinical, Financial, Operational). '
                                       'Determines the risk appetite threshold for "Outside Appetite" flagging.')
    register_id = fields.Many2one('nhs.risk.register', string='Register', required=True,
                                  default=lambda self: self.env['nhs.risk.register'].search([('tier', '=', 'local')], limit=1),
                                  help='The register this risk is currently held on. '
                                       'Use the Escalate button to move the risk between registers.')
    risk_owner_id = fields.Many2one('res.users', string='Risk Owner', required=True,
                                    tracking=True,
                                    help='The individual accountable for managing and monitoring this risk. '
                                         'Receives review reminders and overdue notifications.')
    executive_lead_id = fields.Many2one('res.users', string='Executive Lead',
                                        help='The executive director or board-level sponsor for this risk. '
                                             'Required for risks on the Corporate Register and BAF.')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company,
                                 help='The organisation this risk belongs to.')
    incident_ids = fields.Many2many('nhs.incident', string='Evidence Incidents',
                                    help='Incidents that provide evidence for or are directly linked to this risk. '
                                         'Used to demonstrate the real-world impact of the risk.')

    # ── Scores ────────────────────────────────────────────────────────
    inherent_consequence = fields.Selection(SCORE_SEL, string='Inherent Consequence', required=True,
                                            help='The consequence score (1–5) if this risk were to materialise '
                                                 'with NO controls in place. 1 = negligible, 5 = catastrophic.')
    inherent_likelihood = fields.Selection(SCORE_SEL, string='Inherent Likelihood', required=True,
                                           help='The likelihood score (1–5) of this risk materialising '
                                                'with NO controls in place. 1 = rare, 5 = almost certain.')
    inherent_rating = fields.Integer(string='Inherent Rating', compute='_compute_ratings',
                                     store=True,
                                     help='Auto-calculated inherent score (consequence × likelihood) '
                                          'with no controls in place. Range: 1–25.')
    inherent_band = fields.Selection(BAND_SEL, string='Inherent Band', compute='_compute_ratings',
                                     store=True,
                                     help='Risk band derived from inherent rating: Low (1–3), Moderate (4–6), '
                                          'High (8–12), Extreme (15–25).')

    current_consequence = fields.Selection(SCORE_SEL, string='Current Consequence', required=True,
                                           help='The consequence score (1–5) after existing controls are considered. '
                                                '1 = negligible, 5 = catastrophic.')
    current_likelihood = fields.Selection(SCORE_SEL, string='Current Likelihood', required=True,
                                          help='The likelihood score (1–5) after existing controls are considered. '
                                               '1 = rare, 5 = almost certain.')
    current_rating = fields.Integer(string='Current Rating', compute='_compute_ratings',
                                    store=True, tracking=True,
                                    help='Auto-calculated current residual risk score (consequence × likelihood). '
                                         'Range: 1–25. Compared against the category appetite threshold.')
    current_band = fields.Selection(BAND_SEL, string='Current Band', compute='_compute_ratings',
                                    store=True, tracking=True,
                                    help='Risk band derived from current rating: Low (1–3), Moderate (4–6), '
                                         'High (8–12), Extreme (15–25). Drives review frequency.')

    target_consequence = fields.Selection(SCORE_SEL, string='Target Consequence',
                                          help='The desired consequence score (1–5) once planned controls '
                                               'and actions are fully implemented.')
    target_likelihood = fields.Selection(SCORE_SEL, string='Target Likelihood',
                                         help='The desired likelihood score (1–5) once planned controls '
                                              'and actions are fully implemented.')
    target_rating = fields.Integer(string='Target Rating', compute='_compute_ratings', store=True,
                                   help='Auto-calculated target risk score (consequence × likelihood) '
                                        'representing the desired risk level after treatment.')
    target_band = fields.Selection(BAND_SEL, string='Target Band', compute='_compute_ratings',
                                   store=True,
                                   help='Risk band derived from the target rating.')

    outside_appetite = fields.Boolean(string='Outside Appetite', compute='_compute_outside_appetite',
                                      store=True,
                                      help='Automatically set when the current risk rating exceeds the '
                                           'appetite threshold defined on the risk category.')

    # ── Treatment ─────────────────────────────────────────────────────
    control_ids = fields.One2many('nhs.risk.control', 'risk_id', string='Controls',
                                  help='Control measures currently in place to reduce the likelihood or '
                                       'consequence of this risk materialising.')
    assurance_ids = fields.One2many('nhs.risk.assurance', 'risk_id', string='Assurances',
                                    help='Sources of assurance (Three Lines of Defence) providing evidence '
                                         'that controls are effective.')
    action_ids = fields.One2many('nhs.action', 'risk_id', string='Actions',
                                 help='Improvement actions planned or underway to further reduce this risk.')

    # ── Review ────────────────────────────────────────────────────────
    review_frequency_days = fields.Integer(string='Review Frequency (days)',
                                           compute='_compute_review_frequency', store=True,
                                           help='Auto-calculated review interval based on the current risk band: '
                                                'Extreme = 30 days, High = 90 days, Moderate = 180 days, Low = 365 days. '
                                                'Can be overridden manually.')
    last_reviewed_at = fields.Datetime(string='Last Reviewed At',
                                       help='The date and time this risk was last formally reviewed. '
                                            'Updated automatically when a review log entry is created.')
    next_review_date = fields.Date(string='Next Review Date',
                                   compute='_compute_next_review', store=True,
                                   help='Auto-calculated date by which the next review is due, '
                                        'based on last reviewed date plus review frequency.')
    review_ids = fields.One2many('nhs.risk.review', 'risk_id', string='Review Log',
                                 help='Audit trail of all review decisions, score changes, and commentary '
                                      'recorded against this risk.')
    manual_frequency_override = fields.Boolean(string='Manual Frequency Override',
                                               help='Tick to set a custom review frequency that overrides '
                                                    'the band-based default interval.')
    manual_frequency_days = fields.Integer(string='Manual Frequency (days)',
                                           help='Custom review interval in calendar days, applied when '
                                                '"Manual Frequency Override" is ticked.')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', required=True, tracking=True,
       help='The current lifecycle stage of this risk entry.')
    closure_reason = fields.Text(string='Closure Reason',
                                 help='Required when closing a risk. Explain why this risk is no longer active '
                                      '(e.g. controls fully effective, risk no longer applicable, strategy changed).')

    @api.depends('inherent_consequence', 'inherent_likelihood',
                 'current_consequence', 'current_likelihood',
                 'target_consequence', 'target_likelihood')
    def _compute_ratings(self):
        """Compute the inherent, current, and target ratings and bands from their consequence/likelihood scores."""
        for rec in self:
            for c_fld, l_fld, r_fld, b_fld in SCORE_FIELDS:
                c = int(rec[c_fld] or 0)
                l = int(rec[l_fld] or 0)
                rating = c * l
                rec[r_fld] = rating
                rec[b_fld] = _band(rating) if rating else False

    @api.depends('current_rating', 'category_id.appetite_threshold')
    def _compute_outside_appetite(self):
        """Flag the risk as outside appetite when the current rating exceeds the category's threshold."""
        for rec in self:
            threshold = rec.category_id.appetite_threshold if rec.category_id else 6
            rec.outside_appetite = rec.current_rating > threshold

    @api.depends('current_band', 'manual_frequency_override', 'manual_frequency_days')
    def _compute_review_frequency(self):
        """Compute the review interval in days from the current risk band, unless manually overridden."""
        for rec in self:
            if rec.manual_frequency_override and rec.manual_frequency_days:
                rec.review_frequency_days = rec.manual_frequency_days
            else:
                rec.review_frequency_days = REVIEW_DAYS.get(rec.current_band, 365)

    @api.depends('last_reviewed_at', 'review_frequency_days')
    def _compute_next_review(self):
        """Compute the next review due date from the last reviewed date and review frequency."""
        for rec in self:
            if rec.last_reviewed_at and rec.review_frequency_days:
                base = rec.last_reviewed_at.date()
                rec.next_review_date = base + timedelta(days=rec.review_frequency_days)
            else:
                rec.next_review_date = False

    @api.model_create_multi
    def create(self, vals_list):
        """Assign a sequence-based reference to new risk records."""
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('nhs.risk') or 'New'
        return super().create(vals_list)

    @api.constrains('register_id', 'executive_lead_id')
    def _check_executive_lead(self):
        """Ensure an Executive Lead is set for risks on the corporate or BAF register."""
        for rec in self:
            if rec.register_id and rec.register_id.tier in ('corporate', 'baf') \
               and not rec.executive_lead_id:
                raise ValidationError(
                    'An Executive Lead is required for corporate and BAF register risks.')

    @api.constrains('manual_frequency_override', 'manual_frequency_days')
    def _check_manual_frequency(self):
        """Ensure the manual review frequency is a positive number of days when overridden."""
        for rec in self:
            if rec.manual_frequency_override and rec.manual_frequency_days <= 0:
                raise ValidationError(
                    'Manual Frequency (days) must be a positive integer greater than zero.')

    def action_activate(self):
        """Activate the risk and stamp the current time as the last reviewed date."""
        self.write({'state': 'active', 'last_reviewed_at': fields.Datetime.now()})

    def action_open_close_wizard(self):
        """Open the wizard to close this risk (Quality Lead users only)."""
        self.ensure_one()
        if not self.env.user.has_group(
                'odoo_nhs_incident_risk.group_hc_quality_lead'):
            raise UserError('Only Quality Lead users can close risks.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Close Risk',
            'res_model': 'nhs.risk.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_risk_id': self.id},
        }

    def action_close(self):
        """Close the risk after ensuring a closure reason is provided (Quality Lead users only)."""
        if not self.env.user.has_group(
                'odoo_nhs_incident_risk.group_hc_quality_lead'):
            raise UserError('Only Quality Lead users can close risks.')
        for rec in self:
            if not rec.closure_reason:
                raise UserError('A closure reason is required.')
        self.write({'state': 'closed'})

    def action_review_now(self):
        """Open the review wizard for this risk."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Review Risk',
            'res_model': 'nhs.risk.review.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_risk_id': self.id},
        }

    def action_escalate(self):
        """Open the wizard to escalate this risk to a different register."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Escalate Risk',
            'res_model': 'nhs.risk.escalate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_risk_id': self.id},
        }

    @api.model
    def _cron_risk_reviews(self):
        """Schedule a review to-do activity for risk owners whose active risks are due for review."""
        today = fields.Date.today()
        risks = self.search([
            ('state', '=', 'active'),
            ('next_review_date', '<=', today),
        ])
        for risk in risks:
            risk.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=risk.risk_owner_id.id,
                note=f'Risk review due: {risk.name} — {risk.title}')

    @api.model
    def create_from_incident(self, incident):
        """Create a new risk register entry pre-filled from an incident and link the two records."""
        risk = self.create({
            'cause': incident.description or '',
            'event': incident.name,
            'effect': '',
            'title': f'Risk identified from {incident.name}',
            'category_id': self.env['nhs.risk.category'].search([], limit=1).id,
            'register_id': self.env['nhs.risk.register'].search(
                [('tier', '=', 'local')], limit=1).id,
            'risk_owner_id': incident.handler_id.id or self.env.user.id,
            'inherent_consequence': '3',
            'inherent_likelihood': '3',
            'current_consequence': '3',
            'current_likelihood': '3',
        })
        risk.incident_ids = [(4, incident.id)]
        incident.risk_ids = [(4, risk.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Risk',
            'res_model': 'nhs.risk',
            'res_id': risk.id,
            'view_mode': 'form',
        }
