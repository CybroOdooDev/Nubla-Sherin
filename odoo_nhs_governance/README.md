# NHS Governance Management

NHS Governance Management (`odoo_nhs_governance`) is the corporate-governance layer
for the NHS suite. It implements the build specification from:

`/home/cybrosys/Downloads/NHS_Governance_Management_-_Build_Specification(1).docx`

A copy is also included at:

`doc/NHS_Governance_Management_-_Build_Specification.docx`

## Delivered Scope

- Board, committee, sub-committee, group and Council of Governors register.
- Terms of reference, quorum rules, meeting frequency and review dates.
- Directors/officers with appointment dates and FPPR check status.
- Committee membership, roles, voting and NED quorum contribution.
- Meeting lifecycle, attendance capture and computed quoracy.
- Agenda items, papers, confidential Part-II flags, minutes and decisions.
- Cycle of business records and wizard to populate meeting agendas.
- Meeting actions with owners, due dates, statuses and BAF gap linkage.
- Declarations of interest, nil returns, annual and at-meeting declarations.
- Board Assurance Framework objectives, principal risks, controls, assurances,
  gaps, 5x5 scoring, RAG status and review dates.
- Soft operational risk reference field for `odoo_nhs_incident_risk` alignment.
- Governance calendar, dashboard entry points and PDF reports.

## First Run

1. Install `odoo_nhs_governance`.
2. Assign users to Governance Viewer, Governance Officer or Governance Manager.
3. Create the board and committees, then add terms of reference and membership.
4. Add cycle-of-business items and generate meetings.
5. Populate agendas, capture attendance, minutes, declarations and actions.
6. Build BAF objectives and principal risks.
