NHS Staff Bank Management
==========================

The internal flexible-staffing bank — bank members, open shifts, offer &
booking, availability, rates, the compliance gate, and bank-vs-agency spend.
The NHS's own alternative to agency.

What it delivers
-----------------
* A bank-member register — flexible/bank workers, their roles, skills, and
  which areas they can work.
* Availability management — when each bank member is available to work.
* An open-shift register — shifts needing cover, by area, date, band and
  role.
* Shift offer & booking — offer shifts to eligible bank members,
  accept/decline, confirm the booking.
* The compliance gate — only members with current mandatory training and
  professional registration can be booked (reads odoo_nhs_training where
  installed; degrades gracefully when it is not).
* Rate management — bank pay rates by band, role and shift type (incl.
  enhancements), effective-dated.
* Bank-vs-agency tracking — record when a shift went to bank vs agency, and
  the cost, for the displacement story.
* Timesheet / worked-shift confirmation feeding pay and cost.
* Spend, fill-rate and utilisation reporting — the board-facing
  agency-reduction metrics.
* Bank-member self-service portal.

Dependencies
------------
* odoo_nhs_establishment (posts / areas / bands) — hard dependency.
* odoo_nhs_training — soft link only, for the compliance gate. The module
  installs and runs without it, falling back to a light in-module
  compliance flag.

License: LGPL-3
