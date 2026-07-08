.. image:: https://img.shields.io/badge/license-OPL--1-blue.svg
    :target: https://www.odoo.com/documentation/user/legal/licenses/licenses.html#odoo-apps
    :alt: License: OPL-1

NHS Mandatory Training Register
================================
Tracks whether every member of staff holds the statutory and mandatory training
their role requires — and, crucially, whether it is still in date. Turns the
near-universal "training matrix spreadsheet" into a live, role-driven compliance
system: requirements defined by post/staff group, completions recorded with
expiry dates, and compliance percentages rolled up by team for the board and
for CQC.

Builds on the NHS Establishment Register: posts, staff groups and the org
hierarchy are reused, not duplicated, because training requirements attach to
POSTS and staff groups the Establishment Register already defines::

    odoo_nhs_establishment    (workforce foundation — posts, staff groups)
       -> odoo_nhs_training   (this module — requirements attach to posts)
            ... then Recruitment, Staff Bank, e-Rostering

Data-minimised by design: a workforce member here is a light record — name,
role, team and training status only, optionally linked to ``res.users`` /
``hr.employee`` — not a full HR file.

Features
========
* Training-subject catalogue seeded with the eleven UK Core Skills Training
  Framework (CSTF) subjects, levels, statutory/mandatory classification and
  editable default refresh frequencies (or one-off, no-expiry, for induction).
* Requirement matrix: reusable Requirement Profiles bundling subjects by role,
  assignable to a post or a staff group, plus individual-level add/waive
  overrides with a reason and review date.
* Training completion records with method, provider, certificate evidence and
  an automatic expiry date (manually overridable), full renewal history kept.
* Automatic status engine: compliant / due soon / expired / not done / exempt,
  recomputed daily against a configurable due-soon window.
* Professional-registration tracking (NMC / GMC / HCPC / GPhC / GDC and more)
  with its own expiry/revalidation logic, surfaced alongside training.
* Individual, team, department and organisation compliance % roll-ups against
  a configurable board target, aggregated up the Establishment org hierarchy.
* The signature **Training Matrix** — members x subjects, colour-coded by
  status, filterable by team, click a cell to record a completion.
* A Compliance Dashboard: weakest subjects, weakest teams, expiring-soon
  planner, expired/overdue register, lapsed registrations.
* Reminders, line-manager escalation on teams below target, and a weekly
  compliance digest.
* Board Assurance, Team Training Matrix and Individual Training Record PDF
  reports, plus pivot/graph analysis by team, subject and staff group.
* Bulk-record a training session for many members at once.
* Import templates for workforce members, completions and registrations.
* Three-tier security (User / Officer / Manager) with company isolation,
  line-manager team scoping via the Establishment hierarchy, and optional
  portal self-view of a member's own record. No hard delete on training
  records or registrations — archived to preserve the evidence trail.

Configuration
=============
#. Install from Apps — pulls in ``odoo_nhs_establishment`` if not already
   installed.
#. Review the seeded CSTF subjects, refresh frequencies and regulator list;
   add any local or role-specific subjects.
#. Build Requirement Profiles (e.g. Ward Nurse, Administrator, Consultant)
   and assign them to posts, or set requirements directly by staff group.
#. Import or create workforce members, assigning each to a post/team so they
   inherit their requirements.
#. Import existing training completions and professional registrations to
   establish the starting compliance position.
#. Set the compliance target and due-soon window under
   Configuration > Settings, and assign security groups.

Usage
=====
* **Training > Compliance > Training Matrix** — the day-to-day view: click any
  cell to record a completion for that member/subject.
* **Training > Compliance > Workforce Members** — add members, see their
  compliance %, drill into required subjects, records and registrations.
* **Training > Reporting > Compliance Dashboard** — the board-level picture.
* **Training > Compliance > Bulk-Record Training Session** — record a whole
  classroom session in one go.

Credits
=======

Developer
---------
Cybrosys Techno Solutions <https://www.cybrosys.com>

Contacts
--------
* Mail Contact: odoo@cybrosys.com
* Website: https://www.cybrosys.com

Maintainer
----------
This module is maintained by Cybrosys Technologies.

For support and more information, please visit `Our Website <https://cybrosys.com>`__

Further information
====================
HTML Description: `<static/description/index.html>`__
