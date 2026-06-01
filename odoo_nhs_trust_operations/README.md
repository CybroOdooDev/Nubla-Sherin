# NHS Trust Management — Operations & Compliance

**Version:** 19.0.1.0.0  
**Depends on:** `odoo_nhs_trust_management`  
**License:** LGPL-3

## Overview

This module extends the **NHS Trust Management - Foundation** module with the full
operational and compliance picture of an NHS Trust. It must be installed on top of
`odoo_nhs_trust_management`.

## Features Added

| Feature | Details |
|---|---|
| **Sites** | Physical locations (hospital, clinic, ambulance station, etc.) with GPS co-ordinates, A&E type, bed capacity, theatres, specialties |
| **Departments** | Sub-units within sites — clinical, corporate, support, or research — with head, specialty, and staff count |
| **CQC Inspections** | Full inspection history with all 5 KLOE ratings (Safe / Effective / Caring / Responsive / Well-Led) plus Overall |
| **Financials** | Annual budget, income, expenditure, surplus/deficit, capital allocation, PFI obligations |
| **Workforce** | Total FTE (manual) and auto-summed bed capacity aggregated from sites |
| **Clinical Specialties** | Configurable lookup table of NHS specialty codes used on sites and departments |

## Menu Structure Added

```
NHS Trusts
├── Operations
│   ├── Trusts          (action from base module)
│   ├── Sites
│   ├── Departments
│   └── Board Members   (action from base module)
└── Compliance
    ├── CQC Inspections
    └── State Change Audit  (action from base module)
```

## Security

No new groups are introduced — the three base groups (`User / Manager / Admin`) apply.
Three additional record rules scope Site, Department, and CQC records to the
user's allowed ICBs / Health Boards.

## Install Order

1. `odoo_nhs_trust_management` (Foundation)
2. **`odoo_nhs_trust_operations`** (this module)
3. `odoo_nhs_trust_reports` (Reports & Documents — optional)
