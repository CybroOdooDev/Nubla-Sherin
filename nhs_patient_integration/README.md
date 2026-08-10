# NHS Patient Simple — Odoo 19 Module

The simplest possible Odoo module that fetches patient demographics from the
NHS Personal Demographics Service when you click a button.

## What you get

- A **Patients** menu with list and form views
- Patient form with: name, NHS Number, DOB, gender, phone, email, address
- A green **Fetch from NHS** button at the top of the form
- Click the button → calls NHS PDS Sandbox → fields populate automatically
- A "Verified with NHS" ribbon appears once synced
- Audit log of every API call (NHS Patient → Configuration → API Log)
- Settings page for environment + API key + Test Connection

## Install

1. Drop the `nhs_patient_simple` folder in your Odoo 19 addons path.
2. Make sure `requests` Python library is installed:
   ```
   sudo pip3 install --break-system-packages requests
   ```
3. Restart Odoo.
4. Apps → Update Apps List → search "NHS Patient" → Install.

## Configure

1. Get your API key from **digital.nhs.uk/developer**:
   - Sign in → My applications → your app → Active API keys → Edit → Copy
   - Make sure your application is subscribed to **Personal Demographics
     Service - FHIR API (Sandbox)**
2. In Odoo, go to **Settings → NHS Patient**.
3. Set Environment = **Sandbox**.
4. Paste the API key.
5. Save.
6. Click **Test NHS Connection** (calls Hello World API).

## Try it

1. Go to **NHS Patient → Patients → Create**.
2. Type a placeholder name like "Test Patient".
3. In NHS Number field, enter `9000000009`.
4. Click **Save**.
5. Click **Fetch from NHS**.
6. After 1-2 seconds, the form auto-fills with name, DOB, gender, address,
   phone — all pulled from NHS PDS sandbox.
7. The green "Verified with NHS" ribbon appears.

Other valid sandbox NHS Numbers:
- 9000000009
- 9000000017
- 9000000025
- 9000000033

## How it works

The button calls `action_fetch_from_nhs` on the patient model. That method:

1. Reads the API key and environment from system parameters.
2. Builds the NHS PDS URL: `https://sandbox.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient/{nhs_number}`.
3. Sends a GET request with header `apikey: <your_key>`.
4. Logs the request + response to `nhs.simple.log`.
5. Parses the FHIR Patient resource and writes the fields to the Odoo record.
6. Posts a chatter message and returns a green notification.

## Switching to Production later

Once approved by NHS Digital:
1. Settings → NHS Patient
2. Change Environment to **Production**
3. Update API Key with production value

The code is identical — only config changes.

## License

LGPL-3
