.. image:: https://img.shields.io/badge/license-LGPL--3-green.svg
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

NHS Recruitment Pipeline
=========================
Vacancy-to-hire recruitment for the NHS — vacancy approval against funded
posts, adverts, portal applications, shortlisting, interviews, offers and the
NHS Employment Check Standards, with onboarding into the establishment, for
both Community and Enterprise editions of Odoo 19.

It depends on the Establishment Register: a vacancy IS an unfilled funded
post, and a completed hire updates in-post FTE. Its NHS-specific heart is the
pre-employment checks — the NHS Employment Check Standards (identity, right
to work, professional registration, references/employment history,
criminal-record/DBS and occupational health) — which is what distinguishes it
from a generic recruitment tool and from Odoo's base ``hr_recruitment``. It
is deliberately standalone of ``hr_recruitment``, using the Establishment
Register as its backbone.

Features
========
* **Vacancy management & control** — raise a vacancy against a funded
  establishment post, with a workforce → finance approval workflow that
  checks the post is funded, not frozen and has vacant capacity before
  opening; indicative cost shown at approval; vacancy ageing and
  time-to-hire tracking.
* **Person specification & advert** — essential/desirable criteria by
  category (qualification/experience/skill/values), job description
  attachment, advert text, advertising-channel reference data, opening/closing
  dates, internal-only flag.
* **Public portal application capture** — a token-gated, rate-limited,
  CSRF-protected public form (``/jobs/apply/<token>/<vacancy_id>``) reusing
  the suite's proven public-form pattern, plus internal applications,
  duplicate-application detection, and eligibility pre-screen flags.
* **Equality & diversity monitoring, segregated** — collected on a
  deliberately separate model with its own access control (``nhs.equality.monitoring``)
  so it can never influence, or appear to influence, selection; reported only
  in aggregate.
* **Shortlisting & scoring** — score applications against the person
  specification, an anonymised-shortlisting option, bulk shortlist decisions
  via wizard, and bulk-communicate outcomes to applicants.
* **Interview management** — panels, scheduling, per-criterion per-panellist
  scoring, outcome (appointable/not appointable/hold/reserve) and ranking.
* **Offer management** — conditional/unconditional offers, offer-letter PDF,
  reserve-candidate handling, and the embedded pre-employment check set with
  an ``all_checks_cleared`` gate before an offer can be made unconditional.
* **NHS Employment Check Standards** — the six mandatory pre-employment
  checks (identity, right to work, professional registration, references,
  criminal record/DBS, occupational health), generated per-hire from a
  configurable check profile; a 'concern' outcome pauses progression;
  sensitive (DBS/occupational-health) data is restricted to the
  Pre-Employment Checks role and Recruitment Manager.
* **Onboarding handoff** — confirming a hire increments the funded post's
  in-post FTE in the Establishment Register, closes the vacancy, and can
  optionally create a workforce-member record in the NHS Mandatory Training
  module so training requirements attach from day one.
* **Dashboards & analytics** — vacancies by stage, applications in flight,
  time-to-hire, stage-conversion funnel, vacancy ageing and outstanding
  pre-employment checks.
* **Reporting** — vacancy advert/pack, shortlisting & interview summary,
  offer letter, and pre-employment-check completion summary, all as QWeb PDF
  reports.
* **Data protection & retention** — configurable retention period for
  unsuccessful-applicant data with a monthly anonymisation cron, unless the
  candidate has consented to the talent pool.
* **Role-based security** — Recruitment Viewer (hiring managers, scoped to
  their own vacancies), Recruitment Officer, Pre-Employment Checks (sensitive
  data) and Recruitment Manager groups, with company-scoped multi-organisation
  isolation.

Configuration
=============
Settings → NHS Recruitment:

* **Vacancy Approval** — require workforce and/or finance sign-off before a
  vacancy can be opened.
* **Pre-Employment Checks** — hard-gate (block) or soft-gate (advisory only)
  unconditional offers/starts on all required checks being cleared.
* **Data Protection & Retention** — months after which an unsuccessful
  applicant's personal data is anonymised.
* **Public Application Form** — enable and generate a security token to
  expose ``/jobs/apply/<token>``.

Company
-------
* `Cybrosys Techno Solutions <https://cybrosys.com/>`__

License
-------
General Public License, Version 3 (LGPL v3).
(http://www.gnu.org/licenses/lgpl-3.0-standalone.html)
