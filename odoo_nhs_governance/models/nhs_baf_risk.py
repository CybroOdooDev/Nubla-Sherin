# -*- coding: utf-8 -*-
from odoo import api, fields, models


SCORE_SELECTION = [(str(i), str(i)) for i in range(1, 6)]


class NhsBafRisk(models.Model):
    _name = 'nhs.baf.risk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'NHS Board Assurance Framework Principal Risk'
    _order = 'current_score desc, reference'

    name = fields.Char(required=True, tracking=True, help="Principal strategic risk recorded on the Board Assurance Framework.")
    reference = fields.Char(
        required=True,
        default='New',
        copy=False,
        help="Sequenced BAF risk reference.",
    )
    objective_id = fields.Many2one(
        'nhs.baf.objective',
        required=True,
        ondelete='cascade',
        help="Strategic objective threatened by this principal risk.",
    )
    company_id = fields.Many2one(
        related='objective_id.company_id',
        store=True,
        help="Owning company inherited from the strategic objective.",
    )
    owning_committee_id = fields.Many2one(
        'nhs.committee',
        help="Committee responsible for scrutinising and reviewing this risk.",
    )
    lead_director_id = fields.Many2one('nhs.director', help="Executive risk owner.")
    consequence = fields.Selection(
        SCORE_SELECTION,
        default='1',
        required=True,
        tracking=True,
        help="Current consequence score on the 1 to 5 risk matrix.",
    )
    likelihood = fields.Selection(
        SCORE_SELECTION,
        default='1',
        required=True,
        tracking=True,
        help="Current likelihood score on the 1 to 5 risk matrix.",
    )
    current_score = fields.Integer(
        compute='_compute_scores',
        store=True,
        help="Current risk score calculated as consequence multiplied by likelihood.",
    )
    target_consequence = fields.Selection(
        SCORE_SELECTION,
        default='1',
        help="Target consequence score after controls and improvement actions.",
    )
    target_likelihood = fields.Selection(
        SCORE_SELECTION,
        default='1',
        help="Target likelihood score after controls and improvement actions.",
    )
    target_score = fields.Integer(
        compute='_compute_scores',
        store=True,
        help="Target residual score calculated from target consequence and target likelihood.",
    )
    rag_status = fields.Selection([
        ('green', 'Green'),
        ('amber', 'Amber'),
        ('red', 'Red'),
    ], compute='_compute_scores', store=True, help="RAG band derived from the current risk score.")
    controls = fields.Html(help="Controls in place to mitigate the principal risk.")
    assurance_ids = fields.One2many(
        'nhs.baf.assurance',
        'risk_id',
        help="Assurances showing whether controls are operating effectively, mapped to the three lines of defence.",
    )
    control_gaps = fields.Text(help="Known gaps in controls for this risk.")
    assurance_gaps = fields.Text(help="Known gaps in assurance for this risk.")
    gap_action_ids = fields.One2many(
        'nhs.meeting.action',
        'baf_risk_id',
        help="Actions raised to close control or assurance gaps.",
    )
    assurance_rating = fields.Selection([
        ('sufficient', 'Sufficient'),
        ('partial', 'Partial'),
        ('insufficient', 'Insufficient'),
    ], default='partial', help="Overall assurance rating: sufficient, partial or insufficient.")
    operational_risk_ref = fields.Char(
        string='Operational Risk Reference',
        help="Optional soft reference to related operational risks in Incident & Risk where that module is present.",
    )
    last_reviewed = fields.Date(help="Date this BAF risk was last reviewed by committee or board.")
    active = fields.Boolean(default=True, help="Archive flag for BAF risks no longer active.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('nhs.baf.risk') or 'New'
        return super().create(vals_list)

    @api.depends('consequence', 'likelihood', 'target_consequence', 'target_likelihood')
    def _compute_scores(self):
        for rec in self:
            rec.current_score = int(rec.consequence or 0) * int(rec.likelihood or 0)
            rec.target_score = int(rec.target_consequence or 0) * int(rec.target_likelihood or 0)
            rec.rag_status = 'red' if rec.current_score >= 15 else 'amber' if rec.current_score >= 8 else 'green'

    def action_review_today(self):
        self.write({'last_reviewed': fields.Date.context_today(self)})
