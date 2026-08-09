# Food Reader

Food Reader is a mobile-first personal nutrition and health application. It combines meal logging, profile-based nutrition targets, Oura recovery/activity data, optional Withings body measurements, an action-first Health screen, and a private AI assistant.

The product direction is deliberately **action first**: the app should answer **“What should I do now?”** before it shows charts, filters, or long historical detail.

## Product principles

1. **Mobile / PWA first** – primary flows are designed for a phone and installed-app usage first, then expanded for desktop.
2. **Action before analysis** – today’s useful action and today’s state appear before long-term charts.
3. **Progressive disclosure** – secondary filters, custom date ranges and detailed daily data stay compact until the user asks for them.
4. **Stable navigation** – the six-item bottom navigation is fixed above the safe area on mobile and content reserves space for it.
5. **Readable state changes** – success, info and error states must use explicit contrast and must not disappear into background colors.
6. **One scroll owner** – complex screens should have one obvious scroll region. The AI chat frame stays inside the viewport and only the message list scrolls.
7. **User data before generic advice** – recommendations are grounded in the authenticated user’s logged food, targets and wearable data.
8. **Deterministic metrics first, LLM second** – calories, targets, health summaries and correlations are calculated in application code; the LLM interprets them.
9. **Read-only AI access** – the AI assistant can inspect the current user’s data through scoped tools, but does not modify meals, OAuth connections or profile data.
10. **Privacy by design** – OAuth tokens are encrypted locally, AI tools are user-scoped, and the AI assistant uses the OpenAI Responses API with `store=false`.

## Mobile UX contract

The shared mobile behavior lives in:

```text
calorie-tracker/frontend/navigation.js
calorie-tracker/frontend/mobile-polish.css
calorie-tracker/frontend/mobile-ux.js
```

`navigation.js` loads the shared polish layer on every main application page.

### Bottom navigation

The mobile navigation always contains:

- Add
- History
- Overview
- Health
- AI
- Profile

On phone-sized layouts it is fixed above `env(safe-area-inset-bottom)`, has a high stacking order, and every target keeps a roughly touch-sized hit area. Pages reserve bottom padding so content is not hidden behind the bar.

### History

History intentionally keeps the date selector compact on mobile:

- current active range and **Custom** action share the first row,
- Today / 7 / 30 / 90-day presets use one compact row,
- custom date fields open only when requested,
- the three summary metrics fit in one row instead of leaving an empty fourth quadrant.

### Overview / Metrics

The Today card is a control panel, not a billboard. Large duplicate calorie numbers and oversized progress areas are visually reduced so current targets and macro progress are visible sooner. The selected-range filter uses the same compact pattern as History.

### Health

The mobile hierarchy is:

1. compact Health/Oura connection header,
2. **What now?** Health Coach,
3. today-at-a-glance cards,
4. trend window,
5. charts and personal patterns,
6. detailed daily data.

The Health Coach card is intentionally concise. The first screen should prioritize the recommended action and today’s state instead of configuration metadata.

### AI Assistant

The AI Assistant behaves like an app-sized chat window, not a long web page:

- the application shell is pinned to the current visual viewport,
- `window.visualViewport` is used to react to the mobile keyboard,
- the chat card remains fully inside the visible viewport,
- only the messages area scrolls,
- the composer stays visible,
- the bottom navigation hides while the text input is focused so the keyboard does not squeeze the composer unnecessarily,
- routine success/info banners are visually suppressed because the response and source chips already communicate success; errors remain visible.

This is implemented in `mobile-ux.js` and `mobile-polish.css` so keyboard behavior is not duplicated in individual pages.

## Main features

### Meal logging

- Add a meal from a photo or free-form text.
- AI-assisted calorie and macro estimation.
- Review and edit the estimate before relying on it.
- Re-analyze an existing meal with additional context/corrections.
- Meal history, templates and daily nutrition summaries.
- Profile-based calorie, protein, carbohydrate, fat and fiber targets.

### Health Coach

Health Coach generates **one concrete next action for today**, for example a food portion, short walk, easy workout, recovery action, or a data-quality action such as logging today’s meals before making a nutrition decision.

It uses:

- today’s logged calories and protein,
- nutrition targets,
- Oura readiness, sleep, steps and workouts,
- recent trends and deterministic health insights,
- local time.

Important rule: **missing logged food means unknown intake, not zero intake**. If today’s meal log is clearly incomplete, the coach/assistant must not infer that the user has eaten nothing and should not manufacture a calorie or protein prescription from that assumption.

### Private AI assistant

`assistant.html` is a read-only chat over the authenticated user’s Food Reader data.

The assistant can query scoped tools for:

- data inventory,
- profile and targets,
- meals,
- Withings measurements,
- Oura daily metrics,
- combined health summaries.

The default product style is deliberately short: one primary action plus only the most decision-relevant evidence.

## OpenAI architecture

### Model routing

AI models are configurable from environment variables without changing code:

```dotenv
OPENAI_API_KEY=...

# Default for every AI workload
LLM_MODEL=gpt-5.6-terra

# Optional per-workload overrides; blank means inherit LLM_MODEL
MEAL_ANALYSIS_MODEL=
HEALTH_COACH_MODEL=
ASSISTANT_MODEL=
```

Effective routing:

```text
meal analysis  -> MEAL_ANALYSIS_MODEL or LLM_MODEL
Health Coach   -> HEALTH_COACH_MODEL or LLM_MODEL
AI assistant   -> ASSISTANT_MODEL or LLM_MODEL
```

### AI Assistant: Responses API

The tool-enabled AI Assistant uses the **OpenAI Responses API** rather than Chat Completions.

Relevant implementation:

```text
calorie-tracker/backend/app/assistant_service.py
calorie-tracker/backend/app/assistant_responses_service.py
```

Behavior:

- `store=false`,
- GPT-5-family calls use low reasoning effort with `context=current_turn`,
- `text.verbosity=low`,
- server-side authenticated function tools,
- tool outputs are replayed with the response items across tool rounds,
- provider failures return a safe application response instead of an unhandled HTTP 500,
- plain-text output is preferred for the compact mobile chat UI.

Meal analysis and Health Coach are separate workloads and can use independent model overrides.

## Oura integration

Food Reader supports one Oura connection per Food Reader user through OAuth 2.0.

Current integration includes:

- OAuth authorization,
- encrypted access and refresh tokens,
- initial import of up to 365 days when available,
- incremental manual sync with a short lookback,
- daily activity score, active/total calories and steps,
- readiness,
- sleep score,
- sleep duration, HRV and lowest heart rate when available,
- stress/recovery when available,
- workout count, duration and calories,
- combined nutrition + Oura health summaries,
- action-first Health Coach.

Requested Oura scopes:

```text
daily workout personal
```

See [`OURA_INTEGRATION.md`](OURA_INTEGRATION.md) for implementation detail and OAuth setup.

## Withings integration

Withings support is optional and provides OAuth-based body measurement synchronization. Synced values can include weight and supported body-composition measurements and can feed profile/health context.

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
│  │     ├─ oura_models.py
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
│  │  ├─ mobile-ux.js
│  │  ├─ common.js
│  │  ├─ service-worker.js
│  │  ├─ manifest.webmanifest
│  │  ├─ privacy.html
│  │  └─ terms.html
│  ├─ Dockerfile
│  ├─ nginx.conf
│  └─ start.sh
├─ OURA_INTEGRATION.md
├─ pyproject.toml
└─ uv.lock
```

## Configuration

For image-based production deployment start from:

```bash
cp deploy/.env.example deploy/.env
```

Important variables:

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

### JWT/OAuth rule

Keep `JWT_SECRET` stable after users connect Oura/Withings. Food Reader derives the local OAuth token-encryption key from this secret; changing it invalidates previously encrypted OAuth credentials.

Never commit `.env` or real OAuth/OpenAI secrets.

## Running locally

Prerequisites:

- Python 3.12
- `uv`
- Node.js 20+ for frontend tests
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

## Docker / production image

Build directly:

```bash
docker build -f calorie-tracker/Dockerfile -t food-reader .
```

The container exposes:

- backend: `8000`
- Nginx/static frontend: `8080`

Persistent production paths:

```text
/app/data
/app/calorie-tracker/backend/uploads
```

`deploy/docker-compose.prod.yml` runs:

```text
ghcr.io/newpaw/food_reader:latest
```

The production compose expects an existing external Docker network named `cloudflare` unless the deployment file is adapted.

## CI/CD

A push to `master` triggers `.github/workflows/release-container.yml`.

The workflow:

1. installs locked Python dependencies with `uv`,
2. runs backend `pytest` tests,
3. syntax-checks `navigation.js`, `mobile-ux.js`, `health.js`, `assistant.js` and the service worker,
4. verifies shared navigation integration,
5. builds the `linux/amd64` Docker image,
6. publishes `ghcr.io/newpaw/food_reader:latest`,
7. publishes a commit-SHA image tag,
8. attaches provenance and SBOM metadata.

The service worker uses a versioned app-shell cache and includes the shared mobile polish assets.

## Testing

Backend:

```bash
uv run pytest tests/backend
```

Frontend unit tests:

```bash
cd calorie-tracker/frontend
npm install
npm test
```

Frontend navigation regression:

```bash
python tests/frontend/test_navigation.py
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
| GET | `/users/me` | Current authenticated user |

### Meals

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/me/meals` | Add meal from image |
| POST | `/me/meals/text` | Add meal from text |
| GET | `/me/meals` | Read meals |
| GET | `/me/summary` | Nutrition summary |
| PUT | `/me/meals/{meal_id}` | Update meal |
| DELETE | `/me/meals/{meal_id}` | Delete meal |
| POST | `/me/meals/{meal_id}/reanalyze` | Re-run AI analysis with corrections |

### Oura / Health

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/oura/status` | Oura connection/sync status |
| POST | `/oura/auth-url` | Begin Oura OAuth |
| GET | `/oura/callback` | OAuth callback |
| POST | `/oura/sync` | Sync Oura data |
| GET | `/oura/daily` | Daily normalized Oura metrics |
| GET | `/oura/health-summary` | Combined nutrition + health summary |
| POST | `/oura/coach` | One action-first Health Coach recommendation |
| DELETE | `/oura/disconnect` | Remove connection and local Oura data |

### AI assistant

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/assistant/chat` | Read-only, tool-enabled conversation over the current user’s data |

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

- Every meal, Oura metric, Withings measurement and OAuth connection is associated with a Food Reader user ID.
- Oura/Withings tool access is scoped to the authenticated user.
- OAuth access/refresh tokens are encrypted before being stored in SQLite.
- OAuth secrets and OpenAI keys stay server-side.
- AI Assistant tools do not expose OAuth credentials, API keys, passwords or database paths.
- AI Assistant is read-only.
- Responses API calls use `store=false`; the app manages visible conversation history itself.
- Health Coach receives compact health/nutrition context rather than raw OAuth credentials or uploaded meal photos.

## Health-data caveat

Food Reader is a personal wellness/nutrition tool, not a medical device. Oura/Withings values and calorie estimates are useful signals but are not exact physiological measurements. Personal correlations are patterns, not proof of causality or diagnosis.

Energy trend calculations use:

```text
logged Food Reader calories - Oura total calories
```

Interpret this primarily over multi-day trends rather than as a precise single-day energy balance.

## Troubleshooting

### AI Assistant returns an error

Check backend logs:

```bash
docker logs --since 15m food-reader
```

The Assistant uses Responses API for GPT-5.x reasoning + tool calling. Do not switch it back to Chat Completions merely to suppress a tool/reasoning compatibility error.

### Mobile chat jumps when the keyboard opens

Verify that the latest `mobile-ux.js` and `mobile-polish.css` are served and that the active service worker cache has updated. The Assistant relies on `window.visualViewport` and the `assistant-input-focused` class.

### Bottom navigation is missing or content is underneath it

Verify that `navigation.js` loaded successfully. It loads the global mobile polish stylesheet, which fixes the nav position and reserves page bottom space.

### Oura is connected but data is stale

Use **Sync Oura**. Automatic Oura webhooks/background synchronization are not implemented yet.

### OAuth stops decrypting after configuration change

Verify that `JWT_SECRET` was not changed after the OAuth connection was created.

### Production image does not update

Verify the GHCR pull, container image digest and host-side update scheduler.

## Security checklist

- Use a long random `JWT_SECRET` and keep it stable.
- Protect `.env` (for example mode `600` on a single-host deployment).
- Never commit API/OAuth secrets.
- Use HTTPS for public OAuth callbacks.
- Keep user-scoped queries on every health/assistant data path.
- Keep AI tools read-only unless a future write workflow adds explicit authorization and confirmation semantics.

## License

MIT License – see `LICENSE`.
