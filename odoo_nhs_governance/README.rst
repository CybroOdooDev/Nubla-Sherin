.. image:: https://img.shields.io/badge/license-LGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

NHS Governance Management
==========================

**Board & committee management, meeting cycles, actions, declarations of interest and the Board Assurance Framework — the corporate-governance layer of the NHS suite, built natively on Odoo 19.**

`odoo_nhs_governance` is the system the Company Secretary's office runs the board and its committees on: the committee structure and Terms of Reference, the meeting cycle (agendas, papers, minutes), the actions arising, declarations of interest, and the Board Assurance Framework (BAF) that links strategic risks to their controls and assurances.

---

## Why this module?

Large trusts use board-portal products for paperless meetings and pack distribution — polished but expensive, and focused on the pack rather than the full governance record. The BAF and Declarations of Interest register are very commonly maintained in Word/Excel, separate from the meeting tooling. Smaller providers, ICBs and the wider sector often have no board-governance system at all.

This module is an affordable, integrated governance system that covers the WHOLE record — committees, Terms of Reference, cycle of business, meetings, actions, declarations of interest and the BAF — in one place, linked to the operational risk register where present.

---

## Key features

### Committee & board register
- Board → committee → sub-committee/group → council of governors hierarchy, with reporting line.
- Terms of Reference per committee: purpose, delegated authority, reporting line.
- Membership register with roles (chair / vice-chair / member / attendee / in-attendance / secretary).
- Quorum rule per committee (minimum members / minimum NEDs) with a live quoracy indicator.
- ToR review date with automatic reminders; committee status history (active / dormant / disbanded).

### Membership & directors
- Director/officer record with appointment and term dates, executive vs. non-executive flag — held on the
  standard Contact (`res.partner`) record rather than a separate model, so the same board member is one
  record across Trust Management, Governance, Sales/Invoicing, etc. (appointment/term dates and board role
  live on the Contact via Trust Management; executive flag and FPPR fields are added by this module).
- Fit and Proper Person Requirement (FPPR) check status and date per director.
- A member's committee portfolio view across every board and committee they sit on.
- Committee membership (`nhs.committee.member`) links to the person via `partner_id` on `res.partner`,
  not a dedicated director model — reusing the same Contact used for board membership.

### Meeting cycle management
- Generate a recurring meeting series from a committee's configured frequency.
- Meeting lifecycle: scheduled → agenda-set → held → minuted → closed, with a cancellation path.
- Attendance capture (present / apologies / absent) with a live quoracy indicator against the rule.

### Agenda & annual cycle of business
- Build an agenda from standing items (auto-populated from the cycle of business) plus ad-hoc items.
- Agenda item purpose (decision / assurance / information / discussion), presenter and time allocation.
- Carry-forward of deferred items to the next meeting.

### Papers & board-pack assembly
- Attach papers/reports to agenda items with version control via standard attachments.
- Assemble the full board/committee pack (agenda + papers + minutes) as a single PDF.
- Confidential / Part-II item handling, separated from the public pack section.

### Minutes, decisions & actions
- Item-level minutes and formal decisions/resolutions.
- Actions raised from a meeting — owner, due date, status — reusing the suite's CAPA action pattern.
- Overdue-action escalation and "matters arising" reporting back to the next meeting.

### Declarations of interest
- A register per member: financial, non-financial professional, non-financial personal, loyalty, indirect and nil-return.
- Declaration events on appointment, at the annual refresh, and at a specific meeting/agenda item.
- Conflict management (noted / withdrew from item / left the room) and a curated published register output.

### Board Assurance Framework (BAF)
- Strategic objectives → principal risks → controls → assurances → gaps → actions.
- 5×5 risk scoring aligned to the same matrix used across the NHS suite, with RAG banding.
- Assurances categorised by the three lines of defence, with an assurance rating per risk.
- Optional soft link to operational risks in NHS Incident & Risk — never a hard dependency.

### Governance calendar, dashboard & reporting
- A calendar across all committees: meetings, ToR reviews, DoI refreshes and statutory cycle items.
- Governance dashboard: upcoming meetings, overdue actions, DoI refreshes due, un-reviewed BAF risks.
- Reports: Board Pack (PDF), BAF Report (PDF), DoI Register (PDF), Action Log (PDF), Attendance analysis.

### Security
- Three-tier groups: Governance Viewer, Committee Secretary/Governance Officer, Governance Manager.
- Committee members see their own committees' packs, their own actions and their own declarations.
- Confidential (Part-II) items restricted to entitled members; multi-company record isolation.
- No hard delete on minutes, decisions, declarations or BAF records — archived, never destroyed.

---

## Part of the Nubla NHS suite

`odoo_nhs_governance` depends on **NHS Trust Management** for the organisation, board and director structure, and soft-links to **NHS Incident & Risk** so the BAF can reference the real operational risk register where that module is installed — an optional link, never a hard dependency.

---

## Support

For questions, issues, demos or feature requests, please contact **Cybrosys Technologies** at `https://www.cybrosys.com <https://www.cybrosys.com>`__.

---

Author
------
* `Cybrosys Techno Solutions <https://cybrosys.com/>`__

License
-------
General Public License, Version 3 (LGPL v3).
(http://www.gnu.org/licenses/lgpl-3.0-standalone.html)

Credits
=======
Developer: (V19) Nubla (governance track)

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

*Part of the **NHS Back Office Management Suite** by Cybrosys Technologies — purpose-built NHS modules for Odoo 19.*
