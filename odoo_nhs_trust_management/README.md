# NHS Trust Management — Foundation

A clean, foundational NHS Trust management module built for Odoo 19.

## Modules Summary

This module establishes the foundational data model, record rules, workflows, leadership tracking, and geographic classifications for the NHS Trust Management suite.

- **Regions**: Classification for England and Scotland NHS regions.
- **Trust Types**: Segmented by English and Scottish healthcare categories.
- **Integrated Care Boards (ICBs) & Systems (ICSs)**: Complete statutory seed data for England's region subdivisions.
- **Scottish Health Boards**: Territorial and National seed data for Scotland.
- **NHS Trusts**: Base model with state tracking, governance validation, and dynamic form layouts.
- **Leadership Tracking**: Extension of `res.partner` to track executive board roles and voting privileges.
- **Workflow State Auditing**: Log records capturing transition histories and justification text.
