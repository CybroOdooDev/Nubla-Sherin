# NHS Trust Management — Reports & Documents

**Version:** 19.0.1.0.0  
**Depends on:** `odoo_nhs_trust_operations`  
**License:** LGPL-3  
**External dependency:** `xlsxwriter` (`pip install xlsxwriter`)

## Overview

This module adds the document and output layer to the NHS Trust Management family.
It must be installed on top of both `odoo_nhs_trust_management` and `odoo_nhs_trust_operations`.

## Features

### Trust Profile PDF (QWeb)

NHS blue-branded PDF automatically bound to the `nhs.trust` model. Appears in the
**Print** menu on every Trust form.

| Section | Content |
|---|---|
| Header band | Trust name, ODS code, Foundation Trust badge, Status |
| 1. Identification | Legal name, short name, health system, type, status, dates |
| 2. Organisational Hierarchy | Region, ICB, ICS (England) / Health Board (Scotland) |
| 3. Contact | Address, phone, email, website |
| 4. Governance | Chair, CEO, Medical Director, DoN, Finance Director + board members table |
| 5. Financials | Budget, income, expenditure, surplus/deficit (coloured green/red), capital, PFI |
| 6. Workforce & Capacity | FTE, bed capacity, site count, department count |
| 7. Sites | Code, name, type, city, beds, A&E badge |
| 8. CQC Inspection History | Date, type, all 6 ratings (England only) |
| Footer | Generation timestamp |

### Trust Directory Excel Export

Accessible via **NHS Trusts → Reports → Export Trust Directory**.

- **Filters:** Health System (All/England/Scotland), Status (All/Active/Exclude Dissolved), Regions (optional m2m)
- **Output:** Single sheet `NHS Trust Directory`, NHS-blue header row, auto-filter, top row + 2 columns frozen
- **23 columns:** ODS Code, Trust Name, Short Name, Health System, Trust Type, Foundation, Region, ICB / Health Board, CQC Rating, Latest CQC Date, Status, Chair, CEO, Sites, Departments, Workforce (FTE), Bed Capacity, Annual Budget, Surplus/Deficit, City, Postcode, Phone, Website
- Surplus/Deficit coloured green (surplus) / red (deficit)

### Document Attachments

No custom model — standard Odoo `ir.attachment` via chatter on the Trust form.
CQC Inspection records also have a dedicated `report_attachment_ids` Many2many.

## Install Order

1. `odoo_nhs_trust_management` (Foundation)
2. `odoo_nhs_trust_operations` (Operations & Compliance)
3. **`odoo_nhs_trust_reports`** (this module)
