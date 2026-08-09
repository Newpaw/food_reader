# Food Reader

Food Reader is a mobile-first personal nutrition and health application. It combines meal logging, profile-based nutrition targets, Oura recovery/activity data, optional Withings body measurements, an action-first Health screen, and a private AI assistant.

The product direction is deliberately **action first**: the app should answer **“What should I do now?”** before showing charts and historical detail.

## Product principles

1. **Mobile / PWA first** – primary flows are designed for a phone and installed-app usage first, then expanded for desktop.
2. **Action before analysis** – today’s useful action and today’s state appear before long-term charts.
3. **User data before generic advice** – recommendations are grounded in the authenticated user’s logged food, targets and wearable data.
4. **Deterministic metrics first, LLM second** – calories, targets, health summaries and correlations are calculated in application code; the LLM interprets the result.
5. **Read-only AI access** – the AI assistant can inspect the current user’s data through scoped tools, but does not modify meals, OAuth connections or profile data.
6. **Privacy by design** – OAuth tokens are encrypted locally, AI tools are user-scoped, and the AI assistant uses the OpenAI Responses API with `store=false`.

## Main features

### Meal logging

- Add a meal from a photo or free-form text.
- AI-assisted calorie and macro estimation.
- Review and edit the estimate before relying on it.
- Re-analyze an existing meal with additional context/corrections.
- Meal history, templates and daily nutrition summaries.
- Profile-based calorie, protein, carbohydrate, fat and fiber targets.

### Health

`health.html` is the action-first health dashboard.

The mobile hierarchy is intentionally:

1. **What should I do now?** – Health Coach recommendation.
2. **Today at a glance** – calories, protein, readiness and sleep.
3. **Trend window** – 14 / 30 / 90 days or a custom range.
4. **Charts and personal patterns** – energy, recovery and HRV trends.
5. **Detailed daily data** – lower-priority drill-down.

The Health screen avoids keeping connection metadata or filter controls permanently dominant on a small viewport. Oura sync/connect status remains available, but the primary screen real estate is reserved for decisions and current state.

### Health Coach

Health Coach generates **one concrete next action for today**, for example a food portion, short walk, easy workout, recovery action or “stop for today” when appropriate.

It uses:

- today’s logged calories and protein,
- nutrition targets,
- Oura readiness, sleep, steps and workouts,
- recent trends and deterministic health insights,
- local time.

The frontend automatically prepares/caches the current recommendation and exposes **Refresh advice** for an explicit recalculation.

The prompt is intentionally restrictive: short recommendation, at most two supporting evidence points, no diagnosis, medication/supplement advice, extreme restriction or invented measurements.

### Private AI assistant

`assistant.html` is a read-only chat over the authenticated user’s Food Reader data.

The assistant can query scoped tools for:

- data inventory,
- profile and targets,
- meals,
- Withings measurements,
- Oura daily metrics,
- combined health summaries.

The assistant is instructed to answer briefly and action-first. It should prefer one direct recommendation plus only the most decision-relevant evidence instead of dumping raw daily data.

#### OpenAI API architecture

The AI assistant uses the **OpenAI Responses API** for reasoning + function calling. Food Reader manually manages the visible chat history and tool loop.

Important implementation details:

- `store=false` – response application state is not intentionally persisted by the Responses API.
- GPT-5-family assistant calls use low reasoning effort with `context=current_turn`.
- `text.verbosity=low` keeps the product output concise.
- Function calls are executed only against server-side, authenticated, user-scoped Food Reader tools.
- Every response output item is replayed across tool rounds so reasoning/tool state is preserved correctly when `store=false`.
- Provider/API failures return a safe user-facing unavailable state instead of an unhandled HTTP 500.

Meal analysis and Health Coach remain separate workloads and can use their own model configuration.

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

## AI model routing

AI models are configurable from environment variables without changing code.

```dotenv
OPENAI_API_KEY=...

# Default model for every AI workload
LLM_MODEL=gpt-5.6-terra

# Optional per-workload overrides; blank means inherit LLM_MODEL
MEAL_ANALYSIS_MODEL=
HEALTH_COACH_MODEL=
ASSISTANT_MODEL=
```

Effective routing is:

```text
meal analysis  -> MEAL_ANALYSIS_MODEL or LLM_MODEL
Health Coach   -> HEALTH_COACH_MODEL or LLM_MODEL
AI assistant   -> ASSISTANT_MODEL or LLM_MODEL
```

The current production-oriented default is `gpt-5.6-terra`; the three workloads can be benchmarked and upgraded/downgraded independently.

## PWA and navigation

The frontend is static HTML/CSS/JavaScript and can be installed as a Progressive Web App.

Primary navigation is shared across the main pages:

- Add meal
- History
- Overview
- Health
- AI Assistant
- Profile

The bottom navigation is optimized for mobile/PWA use, while desktop navigation remains available on larger screens.

The service worker caches the application shell so the installed app can reopen when connectivity is temporarily unavailable. Meal offline behavior is handled separately from server-backed AI/OAuth features.

## Project structure

```text
food_reader/
├─ .github/workflows/
│  └─ release-container.yml          # tests + GHCR image release
├─ deploy/
│  ├─ docker-compose.prod.yml        # image-based production compose
│  └─ .env.example                   # production environment template
├─ tests/
│  ├─ backend/                       # FastAPI/service tests
│  └─ frontend/                      # navigation/integration checks
├─ calorie-tracker/
│  ├─ backend/
│  │  ├─ app/
│  │  │  ├─ main.py
│  │  │  ├─ settings.py              # env config + model routing
│  │  │  ├─ ai_analyzer.py           # meal photo/text AI analysis
│  │  │  ├─ health_service.py        # deterministic health aggregation
│  │  │  ├─ health_coach.py          # action-first LLM interpretation
│  │  │  ├─ assistant_service.py     # assistant data tools + shared prompt
│  │  │  ├─ assistant_responses_service.py # Responses API tool loop
│  │  │  ├─ oura_service.py
│  │  │  ├─ oura_models.py
│  │  │  └─ routers/
│  │  └─ uploads/
│  ├─ frontend/
│  │  ├─ index.html / home.js
│  │  ├─ history.html / history.js
│  │  ├─ metrics.html / metrics.js
│  │  ├─ health.html / health.js / health.css / health-action.css
│  │  ├─ assistant.html / assistant.js
│  │  ├─ profile.html / profile.js
│  │  ├─ navigation.js
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

For an image-based production deployment, start from:

```bash
cp deploy/.env.example deploy/.env
```

Important variables:

```dotenv
# Runtime
BACKEND_PORT=18000
FRONTEND_PORT=18080
DATABASE_URL=sqlite:////app/data/app.db

# Authentication
JWT_SECRET=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# OpenAI
OPENAI_API_KEY=...
LLM_MODEL=gpt-5.6-terra
MEAL_ANALYSIS_MODEL=
HEALTH_COACH_MODEL=
ASSISTANT_MODEL=

# Oura
OURA_CLIENT_ID=...
OURA_CLIENT_SECRET=...
OURA_REDIRECT_URI=https://food.example.com/oura/callback
OURA_FRONTEND_URL=https://food.example.com/health.html

# Withings
WITHINGS_CLIENT_ID=...
WITHINGS_CLIENT_SECRET=...
WITHINGS_REDIRECT_URI=https://food.example.com/withings/callback
APP_FRONTEND_URL=https://food.example.com/profile.html
```

### Important JWT/OAuth rule

Keep `JWT_SECRET` stable after users connect Oura/Withings. Food Reader derives the local OAuth token-encryption key from this secret; changing it invalidates previously encrypted OAuth credentials.

Never commit `.env` or real OAuth/OpenAI secrets.

## Running locally

### Prerequisites

- Python 3.12
- `uv`
- Node.js 20+ for frontend tests
- Docker + Docker Compose for container workflows

### Backend

```bash
uv sync
cd calorie-tracker
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Static frontend

```bash
cd calorie-tracker/frontend
python3 -m http.server 8080
```

Open:

```text
http://localhost:8080
```

The frontend detects the common split local setup and sends API requests to port `8000`.

To override the backend location in a development browser:

```js
localStorage.setItem('food-reader-api-base', 'http://YOUR-HOST:8000')
```

## Docker

Build directly:

```bash
docker build -f calorie-tracker/Dockerfile -t food-reader .
```

The application container exposes:

- backend: `8000`
- Nginx/static frontend: `8080`

Persistent production data should be mounted for:

```text
/app/data
/app/calorie-tracker/backend/uploads
```

## Production image deployment

`deploy/docker-compose.prod.yml` runs:

```text
ghcr.io/newpaw/food_reader:latest
```

Example:

```bash
cd deploy
docker compose -f docker-compose.prod.yml pull app
docker compose -f docker-compose.prod.yml up -d app
```

The production compose expects an existing external Docker network named `cloudflare`. Adjust the network section if your environment uses another reverse-proxy topology.

The container includes a `/health` backend health check.

## CI/CD

A push to `master` triggers `.github/workflows/release-container.yml`.

The workflow:

1. installs locked Python dependencies with `uv`,
2. runs backend `pytest` tests,
3. checks frontend JavaScript syntax,
4. verifies shared navigation integration,
5. builds the `linux/amd64` Docker image,
6. publishes `ghcr.io/newpaw/food_reader:latest`,
7. also publishes a commit-SHA image tag,
8. attaches provenance and SBOM metadata.

A production host can periodically pull `latest` and recreate only the application container while preserving mounted SQLite/upload data.

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

Frontend E2E:

```bash
cd calorie-tracker/frontend
E2E_EMAIL="your-email@example.com" \
E2E_PASSWORD="your-password" \
npm run test:e2e
```

The release workflow additionally executes JavaScript syntax checks and the shared-navigation regression test.

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
- Oura/Withings tool access is scoped to the currently authenticated user.
- OAuth access/refresh tokens are encrypted before being stored in SQLite.
- OAuth secrets and OpenAI keys stay server-side.
- AI assistant tools do not expose OAuth credentials, API keys, passwords or database paths.
- The AI assistant is read-only.
- Responses API calls use `store=false` and the app manages the visible conversation context itself.
- Health Coach receives a compact health/nutrition context rather than raw OAuth credentials or uploaded meal photos.

See `privacy.html` and `terms.html` for user-facing legal pages.

## Health-data caveat

Food Reader is a personal wellness/nutrition tool, not a medical device. Oura/Withings values and calorie estimates are useful signals but are not exact physiological measurements. Personal correlations are presented as patterns, not proof of causality or diagnosis.

Energy trend calculations use:

```text
logged Food Reader calories - Oura total calories
```

Interpret this primarily over multi-day trends rather than as a precise single-day energy balance.

## Troubleshooting

### AI assistant returns an error

Check backend logs first:

```bash
docker logs --since 15m food-reader
```

The assistant now uses the Responses API because GPT-5.6 tool calling with reasoning is designed for that API. Do not switch it back to Chat Completions merely to suppress a tool/reasoning compatibility error.

### Health Coach works but Assistant fails

These are separate OpenAI workloads and API paths. Verify the effective model routing and backend logs independently.

### Oura is connected but data is stale

Use **Sync Oura**. Automatic Oura webhooks/background synchronization are not implemented yet.

### OAuth stops decrypting after configuration change

Verify that `JWT_SECRET` was not changed after the OAuth connection was created.

### Production image does not update

Verify the GHCR pull, container image digest, and the host-side update scheduler. The repository publishes images but does not install a host scheduler automatically.

## Security checklist for production

- Use a long random `JWT_SECRET` and keep it stable.
- Protect `.env` (for example mode `600` on a single-host deployment).
- Never commit API/OAuth secrets.
- Use HTTPS for all public OAuth callbacks.
- Keep OAuth redirect URIs exact.
- Persist SQLite/uploads outside the container filesystem.
- Keep user-scoped authorization tests enabled.
- Add rate limiting/abuse controls before broad public exposure.
- Back up persistent data before schema/deployment changes.

## Technologies

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, SQLite
- **AI:** OpenAI API, GPT-5.6-family configurable routing, Responses API function calling for the assistant
- **Wearables:** Oura OAuth/API, optional Withings OAuth/API
- **Frontend:** HTML, CSS, vanilla JavaScript modules, PWA service worker/manifest
- **Testing:** pytest, Vitest, Playwright, frontend syntax/regression checks
- **Infrastructure:** Docker, Nginx, Docker Compose, GitHub Actions, GHCR

## License

MIT License – see `LICENSE`.
