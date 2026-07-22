# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NhsCommittee(models.Model):
    _name = 'nhs.committee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'NHS Board, Committee or Group'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(
        required=True,
        tracking=True,
        help="Committee or board name, for example Audit Committee or Trust Board.",
    )
    complete_name = fields.Char(
        compute='_compute_complete_name',
        store=True,
        help="Breadcrumb reporting line built from the parent committee structure.",
    )
    parent_id = fields.Many2one(
        'nhs.committee',
        string='Reports To',
        index=True,
        ondelete='restrict',
        help="Parent board, committee or group this committee reports to.",
    )
    parent_path = fields.Char(index=True, help="Technical path used for committee hierarchy searches.")
    child_ids = fields.One2many(
        'nhs.committee',
        'parent_id',
        help="Sub-committees and groups reporting to this committee.",
    )
    committee_type_id = fields.Many2one(
        'nhs.governance.committee.type',
        required=True,
        string='Committee Type',
        help="Classifies the body as board, standing committee, sub-committee, group or Council of Governors.",
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        help="Owning organisation; record rules use this for multi-company isolation.",
    )
    trust_id = fields.Many2one(
        'nhs.trust',
        string='Trust / Organisation',
        help="Trust Management organisation that owns this governance body.",
    )
    terms_of_reference = fields.Html(
        help="Committee terms of reference: purpose, delegated authority, membership, quorum, frequency and reporting line.",
    )
    tor_review_date = fields.Date(
        string='Next ToR Review',
        tracking=True,
        help="Next scheduled review date for the terms of reference, normally annual.",
    )
    quorum_min = fields.Integer(
        string='Minimum Members',
        help="Minimum number of present voting members required for the meeting to be quorate.",
    )
    quorum_min_ned = fields.Integer(
        string='Minimum NEDs',
        help="Minimum number of present non-executive directors required for quoracy, where applicable.",
    )
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('bi_monthly', 'Bi-monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('ad_hoc', 'Ad-hoc'),
    ], default='quarterly', help="Expected meeting frequency used when generating recurring meeting series.")
    chair_id = fields.Many2one(
        'nhs.committee.member',
        help="Committee member holding the chair role.",
    )
    member_ids = fields.One2many(
        'nhs.committee.member',
        'committee_id',
        help="Membership register with roles, terms, voting and quoracy contribution.",
    )
    meeting_ids = fields.One2many(
        'nhs.meeting',
        'committee_id',
        help="Meetings scheduled or held for this committee.",
    )
    cycle_item_ids = fields.One2many(
        'nhs.cycle.of.business',
        'committee_id',
        help="Standing annual cycle-of-business items due to this committee.",
    )
    baf_risk_ids = fields.One2many(
        'nhs.baf.risk',
        'owning_committee_id',
        help="Principal BAF risks scrutinised by this committee.",
    )
    state = fields.Selection([
        ('active', 'Active'),
        ('dormant', 'Dormant'),
        ('disbanded', 'Disbanded'),
    ], default='active', tracking=True, help="Current lifecycle status of the committee.")
    active = fields.Boolean(default=True, help="Archive flag; disused committees are archived rather than deleted.")

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for rec in self:
            rec.complete_name = '%s / %s' % (rec.parent_id.complete_name, rec.name) if rec.parent_id else rec.name
