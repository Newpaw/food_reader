# Oura integration

Food Reader connects an Oura account through OAuth 2.0, stores normalized daily metrics in the existing SQLite database, and combines them with nutrition targets, logged meals and optional Withings weight data in the **Health** screen.

The current product hierarchy is action-first: the user sees **what to do now**, then today’s state, and only then trends and detailed history.

## What is included

- Oura OAuth 2.0 authorization with encrypted access and refresh tokens
- One Oura connection per Food Reader user
- Initial historical import (up to 365 days, limited by data available in Oura)
- Incremental manual sync with a short lookback so recently changed Oura days are refreshed
- Daily activity: score, calories, steps, distance targets, MET totals, inactivity and activity zones
- Daily readiness: score, temperature deviations and all contributors
- Daily sleep: score, contributors, stages, latency, efficiency, bedtime, HRV, heart rate, breathing and score deltas
- Suggested optimal bedtime, recommendation and sleep-time status
- Daily stress/recovery, long-term resilience and rest-mode periods
- SpO₂ average and breathing disturbance index (BDI)
- Cardiovascular age, pulse-wave velocity and VO₂ max
- Daytime heart-rate aggregates with source counts
- Workouts, sessions and tags with compact per-day detail
- Oura profile data allowed by the `personal` scope (age, weight, height and biological sex)
- Ring generation/design/color/firmware/size and the latest battery/charging state
- Combined Food Reader nutrition + Oura + latest Withings health summary
- Personal trend analysis such as energy balance, protein, meal timing and next-day recovery patterns
- **Action-first Health Coach** using today’s food, targets, Oura signals and recent trends
- Automatic Health Coach preparation/cache on the Health screen, plus explicit **Refresh advice**
- Czech and English dashboard copy

The analytics intentionally require a minimum number of observations before calculating correlations. Correlations are displayed as patterns in the user’s own data, not as medical conclusions or proof of causality.

## Oura developer setup

1. Sign in to the Oura Cloud developer portal and create an OAuth application.
2. Configure the redirect URI to exactly match the public backend callback URL, for example:

   ```text
   https://food.example.com/oura/callback
   ```

3. Configure the server environment:

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
daily workout personal heartrate tag session spo2Daily
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
| POST | `/oura/coach` | Generate one data-grounded recommendation for today |
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

`oura_connections` stores one OAuth connection per Food Reader user. Tokens are encrypted before being written to SQLite. The same row stores the latest profile, ring configuration and battery snapshot. Oura email is neither requested nor stored.

`oura_daily_metrics` stores one normalized row per user and local Oura day. It contains the main numeric signals as columns and compact structured context (contributors, workouts, sessions, tags and rest-mode episodes) in `details_json`. Large raw sample arrays are not persisted; heart-rate and battery time series are reduced to useful summaries.

Meals remain in the existing `meals` table. The Health service aggregates meals in the browser’s IANA timezone and joins them to Oura daily metrics by local date.

## Health screen behavior

On mobile, the Health screen is intentionally ordered as:

1. **What should I do now?** – Health Coach
2. **Today at a glance** – calories, protein, readiness, sleep
3. **Trend range** – 14 / 30 / 90 days or custom range
4. **Charts / personal patterns**
5. **Detailed daily data**

Oura connection metadata and sync controls remain available but are visually secondary. Sync feedback uses explicit success/info/error states so the result remains readable on a small screen.

The Health Coach recommendation is cached in browser `localStorage` against a fingerprint containing the selected range, today’s relevant nutrition/Oura data, targets, locale and latest Oura sync. When those inputs change, a new recommendation is generated. The user can also force a refresh explicitly.

## Health Coach and data sent to OpenAI

Health Coach is an interpretation layer. It does **not** calculate the source metrics itself: Food Reader first calculates nutrition totals, remaining targets, coverage and personal correlations deterministically and only then asks the configured LLM for one practical next action.

Model routing is configured through:

```dotenv
LLM_MODEL=gpt-5.6-terra
HEALTH_COACH_MODEL=
```

When `HEALTH_COACH_MODEL` is blank, it inherits `LLM_MODEL`.

The backend sends a compact aggregated context containing:

- local time
- selected date range and aggregate summary
- nutrition targets
- deterministic insight text
- at most the latest 14 days of numeric signals such as calories, protein, last-meal time, energy balance, readiness, sleep score, HRV, steps and workouts

It intentionally does **not** send Oura OAuth credentials or raw access/refresh tokens. Meal photos are not part of Health Coach context.

The Health Coach prompt is action-first and intentionally restrictive:

- one short recommendation
- at most two short evidence points
- concrete portion/duration/step target when supported by data
- no diagnosis
- no medication/supplement advice
- no extreme calorie restriction
- do not treat an incomplete current day as a finished daily deficit/surplus

If no OpenAI API key is configured, Health Coach returns a safe unavailable state and the deterministic Health dashboard continues to work normally.

## Energy balance caveat

The dashboard calculates:

```text
logged Food Reader calories - Oura total calories
```

This is useful as a trend signal, but neither food logging nor wearable expenditure is exact enough to treat a single day’s number as a precise physiological energy balance. Use multi-day trends and body-weight development for decisions.

## Webhooks / automatic Oura sync

The current integration performs a historical import when OAuth completes and exposes incremental sync through `/oura/sync`.

Automatic Oura webhook/background synchronization is **not implemented yet**. Until it is added, the user refreshes wearable data through **Sync Oura**. This is separate from Health Coach auto-generation: the Coach can refresh automatically from the latest locally available Oura data, but it does not itself pull new Oura Cloud data.

## Tests

Oura/Health Coach backend coverage lives mainly in:

```text
tests/backend/test_oura.py
tests/backend/test_health_coach.py
```

Coverage includes:

- missing configuration
- OAuth callback and initial sync
- normalized daily metrics
- Food Reader + Oura health summary
- user data isolation
- disconnect cleanup
- Health Coach context minimization
- Health Coach fallback when OpenAI is unavailable
