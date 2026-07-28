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
#    You should have received a copy of the GNU LESSER PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models
from odoo.exceptions import UserError

SCORE_SEL = [(str(i), str(i)) for i in range(1, 6)]
SCORE_BANDS = [
    (range(1, 4), 'low'),
    (range(4, 7), 'moderate'),
    (range(8, 13), 'high'),
    (range(15, 26), 'extreme'),
]


class NhsBafRisk(models.Model):
    _name = 'nhs.baf.risk'
    _description = 'A principal (strategic) risk on the Board Assurance Framework'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'current_score desc'

    name = fields.Char(string='Principal Risk', required=True, tracking=True,
                       help='Principal-risk description.')
    reference = fields.Char(string='Reference', readonly=True, copy=False, default='New',
                            help='Auto-generated BAF risk reference (e.g. BAF/2026/00001).')
    objective_id = fields.Many2one('nhs.baf.objective', string='Strategic Objective', required=True,
                                   ondelete='cascade', help='The objective this risk threatens.')
    company_id = fields.Many2one(related='objective_id.company_id', string='Company', store=True,
                                 help='Company owning the related strategic objective.')
    owning_committee_id = fields.Many2one('nhs.committee', string='Owning Committee',
                                          help='The committee that scrutinises this risk.')
    lead_director_id = fields.Many2one('nhs.director', string='Executive Risk Owner',
                                       help='Executive risk owner.')
    consequence = fields.Selection(SCORE_SEL, string='Consequence', required=True, default='1',
                                   help='Consequence score (1-5), aligned to the 5×5 matrix used in '
                                        'Incident & Risk. 1 = negligible, 5 = catastrophic.')
    likelihood = fields.Selection(SCORE_SEL, string='Likelihood', required=True, default='1',
                                  help='Likelihood score (1-5). 1 = rare, 5 = almost certain.')
    current_score = fields.Integer(string='Current Score', compute='_compute_current_score', store=True,
                                   help='consequence × likelihood; RAG-banded.')
    current_band = fields.Selection([
        ('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('extreme', 'Extreme'),
    ], string='Current Band', compute='_compute_current_score', store=True,
       help='RAG band derived from the current score.')
    target_score = fields.Integer(string='Target Score', help='Target residual score.')
    controls = fields.Html(string='Controls', help='Controls in place to control the risk.')
    assurance_ids = fields.One2many('nhs.baf.assurance', 'risk_id', string='Assurances',
                                    help='Assurances mapped to controls.')
    control_gaps = fields.Text(string='Gaps In Control', help='Identified gaps in control.')
    assurance_gaps = fields.Text(string='Gaps In Assurance', help='Identified gaps in assurance.')
    gap_action_ids = fields.One2many('nhs.meeting.action', 'baf_risk_id', string='Gap Actions',
                                     help='Actions raised to close control/assurance gaps.')
    assurance_rating = fields.Selection([
        ('sufficient', 'Sufficient'),
        ('partial', 'Partial'),
        ('insufficient', 'Insufficient'),
    ], string='Assurance Rating', tracking=True,
       help='Overall assurance rating for this principal risk.')
    operational_risk_ref = fields.Char(
        string='Linked Operational Risk',
        help="Optional link to an operational risk in odoo_nhs_incident_risk, stored as "
             "'nhs.risk,<id>'. A plain Char (not a Many2one/Reference) so this field never has to "
             "resolve the odoo_nhs_incident_risk model — it degrades gracefully when that module "
             "is not installed, which a Reference field cannot do since it eagerly resolves its "
             "target model as soon as a value is assigned.")
    last_reviewed = fields.Date(string='Last Reviewed', tracking=True, help='Last BAF review date.')
    active = fields.Boolean(string='Active', default=True, help='Archive flag.')

    @api.depends('consequence', 'likelihood')
    def _compute_current_score(self):
        """Derive the current risk score and RAG band from consequence and likelihood."""
        for rec in self:
            score = int(rec.consequence or 1) * int(rec.likelihood or 1)
            rec.current_score = score
            band = 'low'
            for score_range, band_name in SCORE_BANDS:
                if score in score_range:
                    band = band_name
                    break
            rec.current_band = band

    @api.model_create_multi
    def create(self, vals_list):
        """Assign an auto-generated BAF risk reference before creating the records."""
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = seq.next_by_code('nhs.baf.risk') or 'New'
        return super().create(vals_list)

    def action_mark_reviewed(self):
        """Stamp this principal risk as reviewed today."""
        self.write({'last_reviewed': fields.Date.today()})

    def action_view_operational_risk(self):
        """Open the linked operational risk record, if any and if the module is installed."""
        self.ensure_one()
        if not self.operational_risk_ref:
            return False
        installed = self.env['ir.module.module'].sudo().search_count(
            [('name', '=', 'odoo_nhs_incident_risk'), ('state', '=', 'installed')])
        if not installed:
            raise UserError('The NHS Incident & Risk module is not installed — the linked '
                            'operational risk cannot be opened.')
        model_name, _, res_id = self.operational_risk_ref.partition(',')
        return {
            'type': 'ir.actions.act_window',
            'res_model': model_name,
            'res_id': int(res_id),
            'view_mode': 'form',
        }

    def unlink(self):
        """Prevent deletion of BAF principal risks unless the user is a system administrator."""
        if not self.env.user.has_group('base.group_system'):
            raise UserError('BAF principal risks cannot be deleted — archive them instead to '
                            'preserve the governance record.')
        return super().unlink()
