from odoo import models, fields, api

class FitnessSocialPost(models.Model):
    _name = 'fitness.social.post'
    _description = 'Member Social Feed Post'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True)
    member_id = fields.Many2one('fitness.member', string='Author', required=True)
    
    content = fields.Html(string='Post Content')
    image = fields.Image(string='Attached Photo')
    
    workout_log_id = fields.Many2one('fitness.workout.log', string='Linked Workout')
    
    kudos_ids = fields.One2many('fitness.social.kudos', 'post_id', string='Kudos')
    kudos_count = fields.Integer(string='Kudos Count', compute='_compute_kudos_count', store=True)

    @api.depends('kudos_ids')
    def _compute_kudos_count(self):
        for post in self:
            post.kudos_count = len(post.kudos_ids)

    def action_give_kudos(self):
        self.ensure_one()
        # Find the logged-in user's fitness member profile (simplified)
        member = self.env['fitness.member'].search([('user_id', '=', self.env.user.id)], limit=1)
        if member:
            existing = self.env['fitness.social.kudos'].search([
                ('post_id', '=', self.id),
                ('member_id', '=', member.id)
            ])
            if not existing:
                self.env['fitness.social.kudos'].create({
                    'post_id': self.id,
                    'member_id': member.id
                })
