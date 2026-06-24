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


def _cleanup_duplicate_locations(env):
    """Remove duplicate bridge-created locations caused by reinstalls.

    For each trust site / department, keeps only the FIRST (oldest) location
    created from it. Unused duplicates are deleted; any duplicate that is
    currently selected on an incident has its bridge back-reference cleared
    (becomes a standalone location) rather than being deleted so the incident
    does not lose its location link.
    """
    Location = env['nhs.location']

    #  Deduplicate site locations
    for site in env['nhs.trust.site'].search([]):
        locs = Location.search(
            [('trust_site_id', '=', site.id)], order='id asc'
        )
        if len(locs) <= 1:
            continue
        keep = locs[0]
        duplicates = locs[1:]
        in_use = duplicates.filtered(
            lambda l: env['nhs.incident'].search_count(
                [('location_id', '=', l.id)]
            ) > 0
        )
        in_use.write({'trust_site_id': False})          # orphan safely
        (duplicates - in_use).unlink()                  # delete unused dups
        site.with_context(no_location_sync=True).write({'location_id': keep.id})

    #  Deduplicate department locations
    for dept in env['nhs.trust.department'].search([]):
        locs = Location.search(
            [('trust_department_id', '=', dept.id)], order='id asc'
        )
        if len(locs) <= 1:
            continue
        keep = locs[0]
        duplicates = locs[1:]
        in_use = duplicates.filtered(
            lambda l: env['nhs.incident'].search_count(
                [('location_id', '=', l.id)]
            ) > 0
        )
        in_use.write({'trust_department_id': False})
        (duplicates - in_use).unlink()
        dept.with_context(no_location_sync=True).write({'location_id': keep.id})


def post_init_hook(env):
    """Create nhs.location mirror records for all pre-existing Trust Sites
    and Trust Departments that don't yet have a linked location.

    Also cleans up duplicate locations that may exist from a previous
    install/uninstall cycle before creating any new ones.
    """
    # Clean up any duplicates left over from a previous reinstall first.
    _cleanup_duplicate_locations(env)

    # Sites
    sites = env['nhs.trust.site'].search([('location_id', '=', False)])
    for site in sites:
        # Guard: a location may already exist for this site even though
        # site.location_id is null (e.g. column reset by uninstall).
        existing = env['nhs.location'].search(
            [('trust_site_id', '=', site.id)], limit=1
        )
        if existing:
            site.with_context(no_location_sync=True).write(
                {'location_id': existing.id}
            )
        else:
            loc = env['nhs.location'].create({
                'name': site.name,
                'location_type': 'site',
                'trust_id': site.trust_id.id,
                'ods_site_code': site.code or False,
                'trust_site_id': site.id,
            })
            site.with_context(no_location_sync=True).write(
                {'location_id': loc.id}
            )

    #  Departments
    departments = env['nhs.trust.department'].search(
        [('location_id', '=', False)]
    )
    for dept in departments:
        existing = env['nhs.location'].search(
            [('trust_department_id', '=', dept.id)], limit=1
        )
        if existing:
            dept.with_context(no_location_sync=True).write(
                {'location_id': existing.id}
            )
        else:
            parent_loc = dept.site_id.location_id if dept.site_id else False
            loc = env['nhs.location'].create({
                'name': dept.name,
                'location_type': 'unit',
                'trust_id': dept.trust_id.id,
                'parent_id': parent_loc.id if parent_loc else False,
                'trust_department_id': dept.id,
            })
            dept.with_context(no_location_sync=True).write(
                {'location_id': loc.id}
            )


def uninstall_hook(env):
    """Delete bridge-created locations when this module is uninstalled so
    that a reinstall starts from a clean slate with no duplicates.

    Safety: locations that are currently selected on an incident record are
    NOT deleted — their bridge back-references (trust_site_id /
    trust_department_id) are cleared instead, converting them to standalone
    manually-created locations so incident data is not lost.
    """
    Location = env['nhs.location']
    bridge_locs = Location.search([
        '|',
        ('trust_site_id', '!=', False),
        ('trust_department_id', '!=', False),
    ])

    in_use = bridge_locs.filtered(
        lambda l: env['nhs.incident'].search_count(
            [('location_id', '=', l.id)]
        ) > 0
    )
    unused = bridge_locs - in_use

    # Locations referenced by incidents: orphan rather than delete.
    in_use.write({'trust_site_id': False, 'trust_department_id': False})
    # Everything else: clean delete.
    unused.unlink()
