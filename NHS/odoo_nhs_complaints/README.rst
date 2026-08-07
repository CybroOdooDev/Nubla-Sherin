.. image:: https://img.shields.io/badge/license-LGPL--3-green.svg
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

NHS Complaints & PALS Management
================================
Manage NHS PALS concerns, formal statutory complaints, investigations, KO41a
reporting, and PHSO escalations in a single Odoo 19 application. Track complaint
progress, statutory deadlines, resolutions, and compliance with the NHS
complaint management process — for both Community and Enterprise editions.

Features
========
* **Dual intake pathway** — informal PALS concerns (``PALS/YYYY/#####``) and
  formal statutory complaints (``COMP/YYYY/#####``), each with its own workflow
  and auto-generated reference.
* **Guided workflow** — Received → Acknowledged → Under Investigation →
  Response Draft → Awaiting Sign-off → Response Sent → Closed, with re-open,
  withdraw and PHSO paths. Status changes are driven only through the action
  buttons.
* **Statutory deadline engine** — acknowledgement (received + 3 working days)
  and agreed response deadlines, working-day aware (weekends + ``nhs.holiday``),
  with overdue flags and reminder cron jobs.
* **Complainant & consent handling** — third-party representation, consent
  status gating on response/sign-off, and vexatious-complainant flagging.
* **Investigations** — chronology/timeline, points of complaint, findings,
  upheld status and lessons learned, feeding the formal response letter.
* **Multi-organisation (joint) complaints** — partner-organisation response
  contributions with per-org submission tracking and coordinated sign-off.
* **Incident & risk linkage** — link complaints to ``nhs.incident`` /
  ``nhs.risk`` records and surface a Duty of Candour warning.
* **KO41a annual return** — subject taxonomy mapped to KO41a codes, a board-pack
  QWeb report, and a CSV export wizard with unmapped-subject detection.
* **PHSO escalation** — Ombudsman referral records with outcome, recommendations
  and resulting corrective actions.
* **Public submission form** — optional token-secured ``/complaint/submit/<token>``
  portal form (CSRF-protected, honeypot + per-IP rate limiting).
* **Correspondence log & letter templates** — acknowledgement, holding, closure
  and consent-request templates; statutory records are protected from deletion.
* **Role-based security** — Complaint Handler, Complaint Manager and Complaint
  Quality Lead groups with company scoping.

Configuration
=============
Settings → NHS Complaints:

* **Public Complaint Submission Form** — enable and generate a security token to
  expose ``/complaint/submit/<token>``.
* **Default Response Timescale** — preset applied to new formal complaints.
* **Anonymise Complainant Data After (Years)** — retention period for the
  monthly anonymisation cron (0 = disabled).

Company
-------
* `Cybrosys Techno Solutions <https://cybrosys.com/>`__

License
-------
General Public License, Version 3 (LGPL v3).
(http://www.gnu.org/licenses/lgpl-3.0-standalone.html)

Credits
=======
Developer: (V19) Nubla Sherin K ,

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
