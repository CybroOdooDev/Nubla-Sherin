.. image:: https://img.shields.io/badge/license-LGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

NHS Incident & Risk Management
==============================

**A Datix-class incident reporting and risk register system, built natively on Odoo 19 — for NHS trusts and every CQC-registered provider.**

`odoo_nhs_incident_risk` brings patient-safety incident reporting, PSIRF investigations, statutory compliance and a full 5×5 risk register into Odoo. It is modelled on the workflows NHS governance teams know from Datix / RLDatix, but at an open, affordable price point — and it works just as well for GP practices, care homes, hospices and independent providers as it does for NHS trusts.

---

## Why this module?

Incident and risk management in UK health and care is a web of statutory duties — PSIRF, LFPSE, Duty of Candour, RIDDOR and CQC notifications — and the established systems are priced for large trusts, leaving primary care and social care on spreadsheets and paper.

This module does the substance of a heavyweight incident system, natively in Odoo:

- **Unlimited free reporters** — anyone can report an incident through a public web form; no licensed seat required.
- **The frameworks that matter, built in** — PSIRF response levels, LFPSE event taxonomy, Duty of Candour, RIDDOR and CQC notifications.
- **Connected** — an incident can reference a risk, raise a corrective action, or link to other records, all in one system.
- **Affordable and open** — built on Odoo Community; no six-figure licences, no per-module pricing.
- **Data-minimised by design** — a safety-management system, not a clinical record; person data is kept to the minimum needed.

---

## Key features

### Incident capture (the reporter form)
- **Public web form** — report an incident without an Odoo login; optionally anonymously.
- **Fast, mobile-friendly capture** — what / when / where / who / description / immediate action, with persons-affected and attachments.
- **Provider-aware** — the form adapts its terminology and categories to the provider type (Patient / Resident / Service user).
- **Reference number & acknowledgement** — reporters receive a reference and, where an email is given, confirmation and closure feedback.

### Triage & handling
- **Triage queue** — a kanban workspace with SLA colouring and badge counts.
- **Validation** — accept, reject (with reason fed back to the reporter), or mark as duplicate.
- **Harm grading** — NPSA scale plus LFPSE physical and psychological harm.
- **Linked records** — relate incidents to each other and to risks; "create risk from incident".

### Investigation (PSIRF-aligned)
- **Proportionate responses** — SWARM huddle, After Action Review, MDT review or full Patient Safety Incident Investigation (PSII).
- **Structured investigation** — lead investigator, timeline, contributing factors, findings, lessons learned and good-practice capture.
- **Sign-off chain** — investigator submits, quality lead approves, incident can close.

### Statutory engines
- **Duty of Candour** — auto-created at moderate+ harm, with a 10-working-day deadline clock, staged notifications and letter generation.
- **RIDDOR** — a guided determination wizard, reportable category and HSE deadline, with submission tracking.
- **CQC notifications** — rule-driven "notification required" tracking with type, submission and reference.
- **LFPSE** — event-type and harm fields aligned to the LFPSE taxonomy, with batch export.

### Risk register
- **5×5 NPSA scoring** — consequence × likelihood, with inherent, current and target scores and automatic RAG banding.
- **Controls & assurances** — including the three-lines-of-defence model.
- **Tiered registers** — local → directorate → corporate → Board Assurance Framework, with escalation.
- **Review cycles** — review frequency driven by risk rating, with reminders and overdue tracking.
- **Heatmap & analytics** — 5×5 matrix views and pivot/graph analysis.

### Actions, dashboards & reporting
- **CAPA actions** — corrective/preventive/improvement actions with owners, due dates, evidence and overdue escalation.
- **Dashboards** — incident trends, harm distribution, risk heatmap, open Duty of Candour clocks, overdue actions.
- **Board pack** — a monthly quality & safety summary PDF.
- **Excel export** — all list and pivot data exports natively.

---

## Compliance frameworks covered

| Area | Supported |
|---|---|
| Patient safety | PSIRF (SWARM, AAR, MDT, PSII), LFPSE event taxonomy, Never Events |
| Candour | Duty of Candour (CQC Regulation 20) with working-day deadline tracking |
| Health & safety | RIDDOR 2013 determination and reporting |
| Regulatory notifications | CQC statutory notifications |
| Risk | NHS 5×5 matrix, Board Assurance Framework, three lines of defence |

---

## Who it's for

Built for the **NHS**, ready for **every CQC-registered provider**:

- NHS trusts and foundation trusts
- GP practices and Primary Care Networks
- Care homes and domiciliary care providers
- Hospices
- Independent hospitals and clinics
- Pharmacies and dental practices

The module adapts its terminology, categories and notification rules to the selected provider type.

---

## Requirements

- **Odoo 19.0** (Community or Enterprise)
- Depends on Odoo core modules: `base`, `mail`, `portal`
- No third-party Python dependencies beyond Odoo's own
- Standalone — does **not** require the NHS Trust Management suite (an optional bridge links the two when both are present)

---

## Installation

1. Place `odoo_nhs_incident_risk` in your Odoo addons path.
2. Update the Apps list (developer mode) or restart the server.
3. Search for **"NHS Incident & Risk Management"** and click **Install**.

### First run

1. Run the **Provider Setup** wizard from the banner — choose your provider type (NHS trust, care home, GP practice, etc.). This activates the right categories, terminology and notification rules and generates your public-form token and a "Scan to report" QR poster.
2. Create your **locations** (site → unit → room) or import them.
3. Assign the **security groups** — Reporter, Handler, Investigator, Risk Manager, Quality Lead, Safeguarding — and set handler allowed-locations on user records.
4. Optionally enable the scheduled reminders (Duty of Candour deadlines, action and risk-review escalation) and set board-pack recipients.
5. **Smoke test:** submit a report from a phone, triage it, raise an action and close it.

---

## Security roles

| Role | What they can do |
|---|---|
| **Reporter** | Submit incidents; see only their own reports. The public form needs no account at all. |
| **Handler** | Triage and manage incidents in their locations; run the RIDDOR wizard; cannot close. |
| **Investigator** | Own and complete assigned investigations. |
| **Risk Manager** | Manage the risk registers they own; run escalation and review. |
| **Quality Lead** | Everything — approve investigations, close incidents, resolve notifications, edit configuration. |
| **Safeguarding** | Additional access to safeguarding-flagged incidents. |

---

## Data protection & scope

This is a **safety-management** system, not a clinical record. It is designed around data minimisation: age bands rather than dates of birth, initials encouraged over full names, and no duplication of clinical records. The public form is token-gated per organisation, rate-limited and CSRF-protected. Statutory records are archived, never deleted, and a retention/anonymisation helper is available.

It is not, and does not replace, an Electronic Patient Record (EPR) or clinical system.

---

## Part of the NHS Back Office suite

`odoo_nhs_incident_risk` is a standalone module that also forms part of the wider **NHS Back Office Management Suite**. The companion **NHS Complaints & PALS Management** module integrates directly with it — a complaint can reveal an incident, and an incident can generate a complaint — and an optional bridge links incidents to the NHS Trust Management suite where both are installed.

---

## Support

For questions, issues, demos or feature requests, please contact **Cybrosys Technologies** at [https://www.cybrosys.com](https://www.cybrosys.com).

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

*Part of the **NHS Back Office Management Suite** by Cybrosys Technologies — purpose-built NHS modules for Odoo 19.*
-------
