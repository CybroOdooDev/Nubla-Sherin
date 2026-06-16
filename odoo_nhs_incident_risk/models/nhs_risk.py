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
    for r, band, _ in SCORE_BANDS:
        if rating in r:
            return band
    return 'low'


class NhsRisk(models.Model):
    _name = 'nhs.risk'
    _description = 'Risk Register Entry (5×5 NPSA Matrix)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'current_rating desc, id'

    name = fields.Char(string='Reference', required=True, readonly=True,
                       copy=False, default='New')
    title = fields.Char(string='Risk Title', required=True)
    cause = fields.Text(string='Cause (IF …)', required=True)
    event = fields.Text(string='Event (THEN …)', required=True)
    effect = fields.Text(string='Effect (RESULTING IN …)', required=True)
    category_id = fields.Many2one('nhs.risk.category', string='Category', required=True)
    register_id = fields.Many2one('nhs.risk.register', string='Register', required=True)
    risk_owner_id = fields.Many2one('res.users', string='Risk Owner', required=True,
                                    tracking=True)
    executive_lead_id = fields.Many2one('res.users', string='Executive Lead')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    incident_ids = fields.Many2many('nhs.incident', string='Evidence Incidents')

    # ── Scores ────────────────────────────────────────────────────────
    inherent_consequence = fields.Selection(SCORE_SEL, string='Inherent Consequence', required=True)
    inherent_likelihood = fields.Selection(SCORE_SEL, string='Inherent Likelihood', required=True)
    inherent_rating = fields.Integer(string='Inherent Rating', compute='_compute_ratings',
                                     store=True)
    inherent_band = fields.Selection(BAND_SEL, string='Inherent Band', compute='_compute_ratings',
                                     store=True)

    current_consequence = fields.Selection(SCORE_SEL, string='Current Consequence', required=True)
    current_likelihood = fields.Selection(SCORE_SEL, string='Current Likelihood', required=True)
    current_rating = fields.Integer(string='Current Rating', compute='_compute_ratings',
                                    store=True, tracking=True)
    current_band = fields.Selection(BAND_SEL, string='Current Band', compute='_compute_ratings',
                                    store=True, tracking=True)

    target_consequence = fields.Selection(SCORE_SEL, string='Target Consequence')
    target_likelihood = fields.Selection(SCORE_SEL, string='Target Likelihood')
    target_rating = fields.Integer(string='Target Rating', compute='_compute_ratings', store=True)
    target_band = fields.Selection(BAND_SEL, string='Target Band', compute='_compute_ratings',
                                   store=True)

    outside_appetite = fields.Boolean(string='Outside Appetite', compute='_compute_outside_appetite',
                                      store=True)

    # ── Treatment ─────────────────────────────────────────────────────
    control_ids = fields.One2many('nhs.risk.control', 'risk_id', string='Controls')
    assurance_ids = fields.One2many('nhs.risk.assurance', 'risk_id', string='Assurances')
    action_ids = fields.One2many('nhs.action', 'risk_id', string='Actions')

    # ── Review ────────────────────────────────────────────────────────
    review_frequency_days = fields.Integer(string='Review Frequency (days)',
                                           compute='_compute_review_frequency', store=True)
    last_reviewed_at = fields.Datetime(string='Last Reviewed At')
    next_review_date = fields.Date(string='Next Review Date',
                                   compute='_compute_next_review', store=True)
    review_ids = fields.One2many('nhs.risk.review', 'risk_id', string='Review Log')
    manual_frequency_override = fields.Boolean(string='Manual Frequency Override')
    manual_frequency_days = fields.Integer(string='Manual Frequency (days)')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', required=True, tracking=True)
    closure_reason = fields.Text(string='Closure Reason')

    @api.depends('inherent_consequence', 'inherent_likelihood',
                 'current_consequence', 'current_likelihood',
                 'target_consequence', 'target_likelihood')
    def _compute_ratings(self):
        for rec in self:
            for c_fld, l_fld, r_fld, b_fld in SCORE_FIELDS:
                c = int(rec[c_fld] or 0)
                l = int(rec[l_fld] or 0)
                rating = c * l
                rec[r_fld] = rating
                rec[b_fld] = _band(rating) if rating else False

    @api.depends('current_rating', 'category_id.appetite_threshold')
    def _compute_outside_appetite(self):
        for rec in self:
            threshold = rec.category_id.appetite_threshold if rec.category_id else 6
            rec.outside_appetite = rec.current_rating > threshold

    @api.depends('current_band', 'manual_frequency_override', 'manual_frequency_days')
    def _compute_review_frequency(self):
        for rec in self:
            if rec.manual_frequency_override and rec.manual_frequency_days:
                rec.review_frequency_days = rec.manual_frequency_days
            else:
                rec.review_frequency_days = REVIEW_DAYS.get(rec.current_band, 365)

    @api.depends('last_reviewed_at', 'review_frequency_days')
    def _compute_next_review(self):
        for rec in self:
            if rec.last_reviewed_at and rec.review_frequency_days:
                base = rec.last_reviewed_at.date()
                rec.next_review_date = base + timedelta(days=rec.review_frequency_days)
            else:
                rec.next_review_date = False

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('nhs.risk') or 'New'
        return super().create(vals_list)

    @api.constrains('register_id', 'executive_lead_id')
    def _check_executive_lead(self):
        for rec in self:
            if rec.register_id and rec.register_id.tier in ('corporate', 'baf') \
               and not rec.executive_lead_id:
                raise ValidationError(
                    'An Executive Lead is required for corporate and BAF register risks.')

    def action_activate(self):
        self.write({'state': 'active', 'last_reviewed_at': fields.Datetime.now()})

    def action_close(self):
        if not self.env.user.has_group(
                'odoo_nhs_incident_risk.group_hc_quality_lead'):
            raise UserError('Only Quality Lead users can close risks.')
        for rec in self:
            if not rec.closure_reason:
                raise UserError('A closure reason is required.')
        self.write({'state': 'closed'})

    def action_review_now(self):
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
