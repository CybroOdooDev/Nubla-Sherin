from odoo import models, fields

class FitnessSocialKudos(models.Model):
    _name = 'fitness.social.kudos'
    _description = 'Social Kudos (Likes)'

    post_id = fields.Many2one('fitness.social.post', string='Post', required=True, ondelete='cascade')
    member_id = fields.Many2one('fitness.member', string='Given By', required=True, ondelete='cascade')
    
    _sql_constraints = [
        ('unique_kudos_per_member', 'unique(post_id, member_id)', 'You can only give kudos once per post!')
    ]
