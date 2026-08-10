.. image:: https://img.shields.io/badge/license-OPL--1-blue.svg
    :target: https://www.odoo.com/documentation/user/legal/licenses/licenses.html#odoo-apps
    :alt: License: OPL-1

NHS Establishment Register
===========================
The master record of an organisation's FUNDED POSTS — the budgeted shape of the
workforce, defined in positions rather than people. Tracks funded establishment
against staff actually in post, exposing the vacancy gap that drives recruitment,
safe staffing and pay-budget planning. Foundation of the NHS Workforce vertical:
Training, Recruitment, Staff Bank and e-Rostering all build on the post model
this module owns.

Depends only on ``base`` and ``mail`` — it holds organisational and post-level
data, NOT personal HR records, so it can be built, sold and run independently
of any HR system.

Features
========
* Organisational hierarchy: Directorate -> Division -> Department -> Team, with
  breadcrumb naming, managers, cost centres and archive-not-delete history.
* Funded-post register: job title, Agenda for Change band, contracted hours/FTE,
  staff group, cost centre, contract type, effective dates, notes and job
  description attachment.
* Funded vs in-post vs vacant FTE and headcount, computed and rolled up at
  every level of the hierarchy.
* Vacancy register with vacancy-rate, time-vacant and frozen-post tracking
  (frozen posts are excluded from true-vacancy counts).
* Establishment change control: create / delete / increase FTE / decrease FTE /
  re-band / transfer requests, with a draft -> submitted -> workforce approved ->
  finance approved -> applied workflow (single-stage option for smaller
  providers), indicative cost impact, and a full audit trail.
* Agenda for Change reference data (Bands 1-9) with editable indicative annual
  salary, an on-cost factor for total employment cost, and support for
  Medical / Non-AfC posts with a manual pay value.
* Dashboards & reporting: establishment summary, by staff group, by band,
  vacancy hotspots, indicative pay-budget view, establishment vs in-post trend,
  and PDF establishment / vacancy register reports (Excel via the standard
  list export).
* Import & onboarding: standard Odoo CSV importer templates for the org
  hierarchy and posts (``static/import_templates/``), with bulk inline editing
  of funded/in-post FTE from the list view.
* Security: Workforce User (read), Workforce Officer (maintain posts and
  in-post figures, raise changes) and Workforce Manager (approve changes,
  configure reference data) groups, with company-scoped record rules.

Configuration
=============
* Settings > NHS Establishment Register: full-time hours basis (default 37.5),
  on-cost factor, whether establishment changes must go through change control,
  and single-stage vs two-stage approval.
* Configuration > Agenda for Change Bands / Staff Groups / Cost Centres:
  reference data maintained by Workforce Managers. Review the seeded AfC
  indicative pay values against the current national pay circular after
  install — they are placeholders, not fixed constants.

Note on import templates
-------------------------
The build specification calls for ``.xlsx`` import templates; this environment
has no XLSX-writing library available, so the templates under
``static/import_templates/`` are provided as ``.csv`` instead. Odoo's standard
importer accepts CSV identically to XLSX, so no functionality is lost.

Company
-------
* `Cybrosys Techno Solutions <https://cybrosys.com/>`__

License
-------
Odoo Proprietary License v1.0 (OPL-1).
(https://www.odoo.com/documentation/user/legal/licenses/licenses.html#odoo-apps)

Credits
=======
Developer: (V19) Nubla Sherin K

Contact: odoo@cybrosys.com

Contacts
--------
* Mail Contact : odoo@cybrosys.com
* Website : https://cybrosys.com

Bug Tracker
-----------
Bugs are tracked on GitHub Issues. In case of trouble, please check there if your issue has already been reported.

Maintainer
==========
.. image:: https://cybrosys.com/images/logo.png
   :target: https://cybrosys.com

This module is maintained by Cybrosys Technologies.

For support and more information, please visit `Our Website <https://cybrosys.com/>`__

Further information
===================
HTML Description: `<static/description/index.html>`__
