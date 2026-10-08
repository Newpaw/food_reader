# Google Health integration

Food Reader supports the **Google Health API v4**, the successor to the Fitbit Web API. This is not an Android Health Connect integration and does not read arbitrary data from every Google Account.

## Availability and activation

As of 8 October 2026, Google's documentation says that new projects are not being onboarded. Code can be deployed before access is available, but real OAuth consent and data access require an approved Google Health project. With no credentials, Food Reader displays an inactive integration and disables connection/download buttons.

1. Obtain access and register the application following the Google Health onboarding instructions. Enable the API in the approved project and configure the Google OAuth consent screen (application name, support contact, privacy policy and authorized domains).
2. Create a **Web application** OAuth client and register the exact callback: `https://YOUR_FOOD_READER_HOST/google-health/callback`.
3. Request only the three implemented read scopes:
   - `https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly`
   - `https://www.googleapis.com/auth/googlehealth.sleep.readonly`
   - `https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly`
4. Configure the deployment's environment:
   ```dotenv
   GOOGLE_HEALTH_CLIENT_ID=your-web-client-id
   GOOGLE_HEALTH_CLIENT_SECRET=your-web-client-secret
   GOOGLE_HEALTH_REDIRECT_URI=https://YOUR_FOOD_READER_HOST/google-health/callback
   ```
   Keep the existing strong `JWT_SECRET` unchanged. It is used by the application's existing token encryption scheme. Do not commit credentials to GitHub. The frontend, OAuth callback and API should share the same HTTPS origin for the browser-bound authorization cookie.
5. Deploy the reviewed application image and restart with these variables. New tables are created by the application's existing `init_db()` startup path; installations managed exclusively with Alembic can apply revision `008` instead. Do not run both creation paths against unstamped tables.
6. Open **Health → Google Health / Fitbit** (also linked from Profile). Connect a Google Account that has a linked Google Health profile, choose permissions, select 1–90 days and download. To retrieve older history, repeat with successive periods of at most 90 days.
7. Verify the real grant with a test account before public release, then complete Google's required application verification/launch review. OAuth credentials alone do not guarantee Health API access.

## User functionality

- Connect and reauthorize using Google OAuth, PKCE and a browser-bound, expiring, one-use state.
- Download **steps, exercise sessions, sleep, weight, body fat, daily resting heart rate and daily HRV**. Availability depends on consent, device support and what has synced to Google Health.
- Daily table, steps total, average recorded sleep, per-record expandable details and type filter.
- JSON export of the selected period, including original reconciled records and daily values. Missing data stays missing; real zeros are preserved.
- Disconnect revokes the Google grant and deletes the local Google Health connection, records and pending authorizations. If revocation temporarily fails, retry; the UI does not falsely report a completed disconnect.
- English and Czech interface. Records retain their source's local date; sleep belongs to its wake-up day. Weight is converted from grams to kilograms. HRV is the documented average RMSSD value in milliseconds, if present.

## Storage and sync behavior

Tokens are encrypted on the backend using the established Food Reader Fernet scheme. Every status, query, export and sync is scoped to the authenticated Food Reader user. The service worker excludes `/google-health` API traffic; data responses have `Cache-Control: no-store`. The integration does not persist health payloads in browser local storage or automatically forward them to AI tools/coaching.

Sync is manual. `/dataPoints:reconcile` is used instead of summing overlapping raw device records. All pages are downloaded before replacing a data type's requested date range. Successful downloads replace the old range, including when Google returns no records, so removed provider records do not remain indefinitely. Failed types preserve existing data and report a warning. Repeated downloads are idempotent. A 50,000-record/type limit prevents unbounded downloads; choose a shorter period if needed. Other existing health providers retain their own independent stores; their values are not combined or double-counted with Google Health.

This application had no legacy Fitbit connection to migrate, so it does not introduce a legacy Fitbit OAuth flow or attempt to transfer legacy tokens. Google can require a user to create/link their Health profile first; `ACCOUNT_NOT_LINKED`, cancellation, missing permissions and expired grants have recovery messages.

Live Google OAuth, provider approval and actual device data cannot be verified without an approved project. Automated tests mock provider responses and cover authorization binding/replay, consent, encrypted tokens, pagination, refresh, date ranges, user isolation, export, repeat sync, failed downloads, deletion and UI rendering.

## Official references

- [Migration and current availability](https://developers.google.com/health/migration)
- [Scopes](https://developers.google.com/health/scopes)
- [Supported data types](https://developers.google.com/health/data-types)
- [Reconciled records](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/reconcile)
- [Filter syntax](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list)
- [Payload schema and units](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints)
