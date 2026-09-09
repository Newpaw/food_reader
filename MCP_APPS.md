# Food Reader MCP App dashboard

Food Reader exposes a self-contained dashboard UI for MCP Apps-capable hosts while preserving the existing structured MCP tool responses for text-only clients.

## UI resources

- `ui://foodreader/health-dashboard.html` — standard MCP Apps resource served as `text/html;profile=mcp-app`.
- `ui://foodreader/health-dashboard-openai.html` — compatibility resource served as `text/html+skybridge` for ChatGPT/OpenAI Apps hosts that still use the older contract.

The HTML is self-contained. It does not load scripts, fonts, images, or data from external origins.

## Tools with dashboard presentation

The dashboard is attached to existing read tools rather than adding a separate model-visible tool:

- `get_health_summary` — combined nutrition + Oura + latest Withings view.
- `get_oura_daily` — readiness, sleep, activity and steps trends.
- `get_withings_measurements` — weight/body-composition trends.
- `get_meals` — daily calorie and protein trends from the returned meal window.

Each tool keeps its original OAuth `securitySchemes` metadata. The presentation layer adds the standard `_meta.ui.resourceUri` plus compatibility metadata for older MCP Apps/OpenAI Apps hosts.

## Rendering

The widget reads the originating tool's `structuredContent` and renders KPI cards plus an inline SVG chart. It supports both:

- standard MCP Apps tool-result `postMessage` delivery, and
- the ChatGPT/OpenAI `window.openai.toolOutput` compatibility surface.

Clients without UI support continue to receive the same normal MCP tool result; the dashboard is only an additional presentation layer.
