# Oura integration

Food Reader can connect an Oura account through OAuth 2.0, store selected daily health metrics in the existing SQLite database, and combine them with nutrition and Withings weight data in the **Health Insights** dashboard.

## What is included

- Oura OAuth 2.0 authorization with encrypted access and refresh tokens
- Initial historical import (up to 365 days)
- Incremental manual sync with a short lookback window so recently changed Oura days are refreshed
- Daily activity: activity score, active calories, total calories, steps
- Daily readiness score
- Daily sleep score
- Sleep detail where available: total sleep duration, average HRV, lowest heart rate
- Daily stress/recovery where available
- Workout count, calories and duration where available
- Health Insights API combining Food Reader nutrition + Oura + latest Withings weight
- Personal trend analysis:
  - logged calorie intake vs Oura total expenditure
  - energy balance vs next-day readiness
  - protein vs next-day readiness
  - calorie intake vs next-day readiness
  - late last meal (21:00+) vs next-day sleep score
- Optional **Health Coach** using the application's existing OpenAI configuration to turn the deterministic metrics into one short recommendation for today
- Czech and English dashboard copy

The analytics intentionally require a minimum number of observations before calculating correlations. Correlations are displayed as patterns in the user's own data, not as medical conclusions or proof of causality.

## Oura developer setup

1. Sign in to the Oura Cloud developer portal and create an OAuth application.
2. Configure the redirect URI to exactly match the public backend callback URL, for example:

   ```text
   https://food.example.com/oura/callback
   ```

3. Add these variables to `calorie-tracker/.env`:

   ```dotenv
   OURA_CLIENT_ID=...
   OURA_CLIENT_SECRET=...
   OURA_REDIRECT_URI=https://food.example.com/oura/callback
   OURA_FRONTEND_URL=https://food.example.com/health.html
   ```

4. Keep `JWT_SECRET` stable. Food Reader derives the local token-encryption key from it; changing the secret invalidates already stored encrypted OAuth credentials.
5. Rebuild/restart the application.
6. Open `/health.html` and select **Connect Oura**.

Requested Oura scopes are:

```text
daily workout personal
```

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/oura/status` | Connection and sync status |
| POST | `/oura/auth-url` | Start OAuth authorization |
| GET | `/oura/callback` | OAuth callback |
| POST | `/oura/sync` | Import/refresh Oura data |
| GET | `/oura/daily` | Read locally stored daily Oura metrics |
| GET | `/oura/health-summary` | Combined nutrition/recovery analytics |
| POST | `/oura/coach` | Generate one data-grounded Health Coach recommendation |
| DELETE | `/oura/disconnect` | Remove local Oura tokens and imported Oura data |

Example health summary:

```text
GET /oura/health-summary?start_date=2026-07-01&end_date=2026-08-01&timezone=Europe/Prague&locale=cs
```

Example coach request:

```text
POST /oura/coach?start_date=2026-07-01&end_date=2026-08-01&timezone=Europe/Prague&locale=cs
```

## Data model

`oura_connections` stores one OAuth connection per Food Reader user. Tokens are encrypted before being written to SQLite.

`oura_daily_metrics` stores one normalized row per user and local Oura day. This keeps dashboard requests fast and prevents the frontend from depending directly on Oura availability.

Meals stay in the existing `meals` table. The Health Insights service aggregates meals in the browser's IANA timezone and joins them to Oura's daily metrics by date.

## Health Coach and data sent to OpenAI

The Health Coach is an interpretation layer. It does **not** calculate the source metrics itself: Food Reader first calculates the energy balance, coverage and personal correlations deterministically and only then asks the configured LLM to summarize the most useful action.

When the user explicitly selects **Generate recommendation**, the backend sends a compact aggregated context to the OpenAI API configured through the existing `OPENAI_API_KEY` / `LLM_MODEL` settings. The context contains:

- selected date range and aggregate summary
- deterministic insight text
- at most the latest 14 days of numeric signals: calories, protein, last-meal time, energy balance, readiness, sleep score, HRV, steps and workout count

It intentionally does **not** send meal photos, meal descriptions, notes, upload paths, Oura OAuth credentials or raw access/refresh tokens. If no OpenAI API key is configured, Health Coach returns a safe unavailable state and the deterministic dashboard continues to work normally.

The Health Coach prompt explicitly forbids diagnosis, claiming causality, medication/supplement recommendations and extreme restriction. Its output should still be treated as a wellness interpretation of the user's own data, not medical advice.

## Energy balance caveat

The dashboard calculates:

```text
logged Food Reader calories - Oura total calories
```

This is useful as a trend signal, but neither food logging nor wearable expenditure is exact enough to treat a single day's number as a precise physiological energy balance. Use multi-day trends and body-weight development for decisions.

## Webhooks

This first integration performs a historical import when OAuth completes and exposes incremental sync through `/oura/sync`. Oura recommends webhooks for ongoing updates. A production follow-up should add webhook subscriptions so the local cache refreshes automatically after Oura Cloud receives new data, instead of depending on the user pressing Sync.

## Tests

Oura/Health Coach backend coverage is in `tests/backend/test_oura.py` and `tests/backend/test_health_coach.py` and covers:

- missing configuration
- OAuth callback and initial sync
- normalized daily metrics
- Food Reader + Oura health summary
- user data isolation
- disconnect cleanup
- Health Coach context minimization (raw meal text/photos/paths are not included)
- Health Coach fallback when OpenAI is unavailable
