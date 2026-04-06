# -*- coding: utf-8 -*-
{
    'name': 'Fitness Center Management',
    'version': '19.0.1.0.0',
    'category': 'Management',
    'summary': 'Comprehensive Fitness Center and Gym Management System',
    'description': """
        This module provides a complete solution for managing a fitness center, including:
        - Member Profiles and Health Notes
        - Membership Plans and Subscriptions
        - Trainer Management and Specializations
        - Attendance Tracking
        - Class Scheduling and Bookings
        - Equipment and Maintenance Management
        - Payment Tracking
    """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base', 'mail', 'contacts', 'hr', 'hr_skills'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/fitness_menus.xml',
        'views/fitness_member_views.xml',
        'views/fitness_membership_plan_views.xml',
        'views/fitness_subscription_views.xml',
        'views/fitness_trainer_views.xml',
        'views/fitness_attendance_views.xml',
        'views/fitness_class_views.xml',
        'views/fitness_class_schedule_views.xml',
        'views/fitness_class_booking_views.xml',
        'views/fitness_equipment_views.xml',
        'views/fitness_equipment_maintenance_views.xml',
        'views/fitness_payment_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'AGPL-3',
}
