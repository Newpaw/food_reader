# Food Reader

Food Reader is a mobile-first personal nutrition and health application. It combines meal logging, nutrition targets, Oura recovery/activity data, optional Withings measurements, an action-first Health screen, and a private AI assistant.

The product direction is deliberately **action first**: the app should answer **“What should I do now?”** before it shows charts, filters, or long historical detail.

## Product principles

1. **Mobile / PWA first** – phone and installed-app flows are the primary design target.
2. **Action before analysis** – today’s useful action and current state come before trends.
3. **Progressive disclosure** – detailed filters and drill-down data stay compact until requested.
4. **Stable navigation** – all six main destinations stay visible in one bottom navigation bar on narrow screens.
5. **Readable state changes** – success, info and error states require explicit contrast.
6. **One scroll owner** – complex screens should have one obvious scroll region; the AI chat scrolls messages, not the whole page.
7. **User data before generic advice** – recommendations are grounded in the authenticated user’s own food, goals and wearable data.
8. **Deterministic metrics first, LLM second** – calculations happen in application code; the LLM interprets them.
9. **Read-only AI tools** – the assistant can inspect user-scoped data but does not modify meals, profile or OAuth connections.
10. **Privacy by design** – OAuth tokens are encrypted locally and the AI assistant uses the Responses API with `store=false`.

## Responsive UX contract

The desktop navigation starts at `980px`. Therefore Food Reader treats the entire range below that breakpoint as **narrow-screen app UI**, not just very small phones.

This is important because Android browsers, display scaling and PWA/browser chrome can produce effective CSS viewports wider than a typical 360–430px phone layout. A previous split where mobile overrides ended at `759px` while tablet/Health rules started around `700–720px` created a broken 760–979px zone. The current shared layer explicitly closes that gap.

Shared responsive behavior lives in:

```text
calorie-tracker/frontend/navigation.js
calorie-tracker/frontend/mobile-polish.css
calorie-tracker/frontend/responsive-fix.css
calorie-tracker/frontend/mobile-ux.js
```

`navigation.js` loads the shared styles/scripts on every main application page.

### Bottom navigation

The narrow-screen navigation always contains:

- Add
- History
- Overview
- Health
- AI
- Profile

Rules:

- one row of six destinations,
- fixed to the visual viewport above the safe area,
- appended directly under `body` so page containers cannot become its containing block,
- high stacking order,
- page content reserves bottom space,
- horizontal page overflow is blocked while nested horizontal scrollers can still be used where intentional.

### History

On narrow screens:

- active range + **Custom** share the first row,
- Today / 7 / 30 / 90-day presets use one compact row,
- custom date inputs appear only when requested,
- the three top summary metrics fit in one row.

### Overview / Metrics

The Today card is a compact control panel, not a billboard. Duplicate calorie information and oversized progress areas are reduced so the user can reach the actual macro status quickly.

### Health

The narrow-screen hierarchy is:

1. compact Health/Oura header,
2. **What now?** Health Coach,
3. today-at-a-glance cards,
4. trend window,
5. single-column charts and personal patterns,
6. collapsed detailed daily data.

Health deliberately stays one-column below `980px`. This prevents half-width chart cards and horizontal document overflow on phones with unusually wide effective CSS viewports.

The Health Coach recommendation is concise. Routine “advice is current” success banners are suppressed on narrow screens because they duplicate the visible recommendation; warnings/errors remain visible.

### AI Assistant

The AI Assistant behaves like an app-sized chat window:

- the shell is pinned to the current `window.visualViewport`,
- keyboard resize/offset is tracked,
- the full chat card stays inside the visible viewport,
- only the messages area scrolls,
- the composer remains visible,
- the bottom navigation hides while the input has focus,
- routine success/info banners are suppressed while errors remain visible.

## Main features

### Meal logging

- Add a meal from a photo or free-form text.
- AI-assisted calorie and macro estimation.
- Review/edit before relying on the estimate.
- Re-analyze an existing meal with corrections or extra context.
- Meal history, templates and daily summaries.
- Profile-based calorie, protein, carbohydrate, fat and fiber targets.

### Health Coach

Health Coach generates **one concrete next action for today**, for example a food portion, short walk, easy workout, recovery action, or a data-quality action such as logging today’s meals before making a nutrition decision.

It uses:

- today’s logged calories and protein,
- nutrition targets,
- Oura readiness, sleep, steps and workouts,
- recent trends and deterministic health insights,
- local time.

Important rule: **missing logged food means unknown intake, not zero intake**. If today’s meal log is incomplete, the coach/assistant must not infer that the user has eaten nothing and should not manufacture a calorie/protein prescription from that assumption.

### Private AI Assistant

`assistant.html` is a read-only chat over the authenticated user’s Food Reader data.

Available data tools cover:

- data inventory,
- profile and targets,
- meals,
- Withings measurements,
- Oura daily metrics,
- combined health summaries.

The default output style is intentionally short: one primary action plus only decision-relevant evidence.

## OpenAI architecture

### Model routing

AI models are configurable through environment variables:

```dotenv
OPENAI_API_KEY=...

LLM_MODEL=gpt-5.6-terra
MEAL_ANALYSIS_MODEL=
HEALTH_COACH_MODEL=
ASSISTANT_MODEL=
```

Blank workload overrides inherit `LLM_MODEL`:

```text
meal analysis  -> MEAL_ANALYSIS_MODEL or LLM_MODEL
Health Coach   -> HEALTH_COACH_MODEL or LLM_MODEL
AI Assistant   -> ASSISTANT_MODEL or LLM_MODEL
```

### AI Assistant: Responses API

The tool-enabled assistant uses the **OpenAI Responses API**.

Relevant implementation:

```text
calorie-tracker/backend/app/assistant_service.py
calorie-tracker/backend/app/assistant_responses_service.py
```

Current behavior:

- `store=false`,
- GPT-5-family calls use low reasoning effort with `context=current_turn`,
- `text.verbosity=low`,
- authenticated server-side function tools,
- tool outputs and response items are replayed across tool rounds,
- provider failures return a safe application response instead of HTTP 500,
- plain-text output is preferred for compact mobile rendering.

Meal analysis and Health Coach remain independent workloads and can use separate model overrides.

## Oura integration

Food Reader supports one Oura connection per Food Reader user through OAuth 2.0.

Current integration includes:

- OAuth authorization,
- encrypted access/refresh tokens,
- initial import up to 365 days when available,
- incremental manual sync with a short lookback,
- daily activity score, calories and steps,
- readiness,
- sleep score/duration, HRV and lowest heart rate when available,
- stress/recovery when available,
- workouts,
- combined nutrition + Oura health summaries,
- Health Coach.

Requested scopes:

```text
daily workout personal
```

See `OURA_INTEGRATION.md` for OAuth setup and implementation detail.

## Withings integration

Withings support is optional and provides OAuth-based body measurement synchronization. Supported measurements can feed profile and health context.

## Project structure

```text
food_reader/
├─ .github/workflows/
│  └─ release-container.yml
├─ deploy/
│  ├─ docker-compose.prod.yml
│  └─ .env.example
├─ tests/
│  ├─ backend/
│  └─ frontend/
├─ calorie-tracker/
│  ├─ backend/
│  │  └─ app/
│  │     ├─ main.py
│  │     ├─ settings.py
│  │     ├─ ai_analyzer.py
│  │     ├─ health_service.py
│  │     ├─ health_coach.py
│  │     ├─ assistant_service.py
│  │     ├─ assistant_responses_service.py
│  │     ├─ oura_service.py
│  │     └─ routers/
│  ├─ frontend/
│  │  ├─ index.html / home.js
│  │  ├─ history.html / history.js
│  │  ├─ metrics.html / metrics.js
│  │  ├─ health.html / health.js / health.css / health-action.css
│  │  ├─ assistant.html / assistant.js / assistant.css
│  │  ├─ profile.html / profile.js
│  │  ├─ navigation.js
│  │  ├─ mobile-polish.css
│  │  ├─ responsive-fix.css
│  │  ├─ mobile-ux.js
│  │  ├─ common.js
│  │  ├─ service-worker.js
│  │  └─ manifest.webmanifest
│  ├─ Dockerfile
│  ├─ nginx.conf
│  └─ start.sh
├─ OURA_INTEGRATION.md
├─ pyproject.toml
└─ uv.lock
```

## Configuration

Example production variables:

```dotenv
BACKEND_PORT=18000
FRONTEND_PORT=18080
DATABASE_URL=sqlite:////app/data/app.db

JWT_SECRET=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=10080

OPENAI_API_KEY=...
LLM_MODEL=gpt-5.6-terra
MEAL_ANALYSIS_MODEL=
HEALTH_COACH_MODEL=
ASSISTANT_MODEL=

OURA_CLIENT_ID=...
OURA_CLIENT_SECRET=...
OURA_REDIRECT_URI=https://food.example.com/oura/callback
OURA_FRONTEND_URL=https://food.example.com/health.html

WITHINGS_CLIENT_ID=...
WITHINGS_CLIENT_SECRET=...
WITHINGS_REDIRECT_URI=https://food.example.com/withings/callback
APP_FRONTEND_URL=https://food.example.com/profile.html
```

Keep `JWT_SECRET` stable after users connect Oura/Withings. The local OAuth token-encryption key is derived from this secret; changing it invalidates previously encrypted OAuth credentials.

Never commit `.env` or real secrets.

## Running locally

Prerequisites:

- Python 3.12
- `uv`
- Node.js 20+
- Docker + Docker Compose for container workflows

Backend:

```bash
uv sync
cd calorie-tracker
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Static frontend:

```bash
cd calorie-tracker/frontend
python3 -m http.server 8080
```

Open `http://localhost:8080`.

## Docker / production

Build:

```bash
docker build -f calorie-tracker/Dockerfile -t food-reader .
```

Container ports:

- backend `8000`
- Nginx/static frontend `8080`

Persistent paths:

```text
/app/data
/app/calorie-tracker/backend/uploads
```

Production image:

```text
ghcr.io/newpaw/food_reader:latest
```

`deploy/docker-compose.prod.yml` expects an external Docker network named `cloudflare` unless adapted.

## CI/CD

A push to `master` triggers `.github/workflows/release-container.yml`.

The workflow:

1. installs locked Python dependencies with `uv`,
2. runs backend tests,
3. syntax-checks frontend JavaScript,
4. runs the shared navigation/responsive regression test,
5. builds `linux/amd64`,
6. publishes `ghcr.io/newpaw/food_reader:latest` plus a commit tag,
7. attaches provenance and SBOM metadata.

The service worker uses a versioned app-shell cache. Current responsive assets, including `responsive-fix.css`, are included so installed PWA clients refresh the same UI contract as browser clients.

## Testing

Backend:

```bash
uv run pytest tests/backend
```

Frontend navigation/responsive regression:

```bash
python tests/frontend/test_navigation.py
```

Frontend unit tests:

```bash
cd calorie-tracker/frontend
npm install
npm test
```

Frontend E2E:

```bash
cd calorie-tracker/frontend
E2E_EMAIL="your-email@example.com" \
E2E_PASSWORD="your-password" \
npm run test:e2e
```

## API overview

### Authentication / user

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Register |
| POST | `/auth/login` | Sign in and receive JWT |
| GET | `/users/me` | Current user |

### Meals

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/me/meals` | Add meal from image |
| POST | `/me/meals/text` | Add meal from text |
| GET | `/me/meals` | Read meals |
| GET | `/me/summary` | Nutrition summary |
| PUT | `/me/meals/{meal_id}` | Update meal |
| DELETE | `/me/meals/{meal_id}` | Delete meal |
| POST | `/me/meals/{meal_id}/reanalyze` | Re-run analysis with corrections |

### Oura / Health

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/oura/status` | Connection/sync status |
| POST | `/oura/auth-url` | Begin OAuth |
| GET | `/oura/callback` | OAuth callback |
| POST | `/oura/sync` | Sync Oura data |
| GET | `/oura/daily` | Daily normalized metrics |
| GET | `/oura/health-summary` | Combined nutrition + health summary |
| POST | `/oura/coach` | One action-first recommendation |
| DELETE | `/oura/disconnect` | Remove Oura connection/data |

### AI Assistant

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/assistant/chat` | Read-only tool-enabled conversation over current user data |

### Withings

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/withings/status` | Connection status |
| POST | `/withings/auth-url` | Begin OAuth |
| GET | `/withings/callback` | OAuth callback |
| POST | `/withings/sync` | Sync measurements |
| GET | `/withings/measurements` | Read local measurements |
| DELETE | `/withings/disconnect` | Remove local connection/data |

## Data and privacy model

- Meals, Oura metrics, Withings measurements and OAuth connections are user-scoped.
- OAuth access/refresh tokens are encrypted before SQLite storage.
- OAuth secrets and OpenAI keys remain server-side.
- AI tools do not expose OAuth credentials, API keys, passwords or database paths.
- AI Assistant tools are read-only.
- Responses API calls use `store=false`.
- Health Coach receives compact health/nutrition context rather than raw OAuth credentials or uploaded meal photos.

## Health-data caveat

Food Reader is a personal wellness/nutrition tool, not a medical device. Wearable values and calorie estimates are useful signals but are not exact physiological measurements. Personal correlations are patterns, not proof of causality or diagnosis.

Energy trend calculations use:

```text
logged Food Reader calories - Oura total calories
```

Interpret this mainly over multi-day trends rather than as a precise single-day balance.

## Troubleshooting

### Narrow-screen UI looks like a broken tablet layout

The narrow-screen contract must apply through `979px`. Verify that the latest `navigation.js`, `responsive-fix.css` and `mobile-ux.js` are served. If a client is installed as a PWA, also verify that the latest service worker activated.

### Bottom navigation is incomplete or horizontally shifted

Verify `navigation.js` loaded and that `responsive-fix.css` is present. The navigation should contain six items, be appended under `body`, use viewport width, and remain independent of page-level horizontal overflow.

### Mobile chat jumps when the keyboard opens

Verify the latest `mobile-ux.js`; the Assistant relies on `window.visualViewport` and the `assistant-input-focused` class.

### AI Assistant returns an error

Check backend logs:

```bash
docker logs --since 15m food-reader
```

The Assistant uses Responses API for GPT-5.x reasoning + tool calling.

### Oura is connected but data is stale

Use **Sync Oura**. Automatic Oura webhooks/background synchronization are not implemented yet.

### OAuth stops decrypting after configuration change

Verify that `JWT_SECRET` was not changed after the OAuth connection was created.

### Production image does not update

Verify the GHCR pull, container image digest and host-side update scheduler.

## Security checklist

- Use a long random stable `JWT_SECRET`.
- Protect `.env` (for example mode `600`).
- Never commit API/OAuth secrets.
- Use HTTPS for public OAuth callbacks.
- Keep user-scoped queries on every health/assistant data path.
- Keep AI tools read-only unless a future write flow adds explicit authorization/confirmation semantics.

## License

MIT License – see `LICENSE`.
