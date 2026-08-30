# Food Reader remote MCP server

Food Reader exposes a public, read-only MCP server at `https://<your-domain>/mcp`.
It uses Streamable HTTP and a built-in OAuth authorization server. An external
agent signs in with an existing Food Reader email/password on Food Reader's own
consent page; the password is never sent to the agent.

## Production configuration

Set these values in `deploy/.env` and redeploy:

```dotenv
MCP_PUBLIC_BASE_URL=https://food.example.com
MCP_ACCESS_TOKEN_EXPIRE_MINUTES=60
MCP_REFRESH_TOKEN_EXPIRE_DAYS=30
```

`MCP_PUBLIC_BASE_URL` must be the stable public HTTPS origin that serves the
application. The same origin must route these paths to the backend:

- `/mcp`
- `/.well-known/oauth-protected-resource` and `/.well-known/oauth-protected-resource/mcp`
- `/.well-known/oauth-authorization-server`
- `/authorize`, `/token`, `/register`, `/revoke`
- `/oauth/consent`

The bundled Nginx configuration already proxies these routes. If Cloudflare or
another reverse proxy sits in front of Nginx, do not cache any of them.

## Connect from ChatGPT

1. Enable ChatGPT developer mode.
2. Create a custom app/connector with MCP server URL `https://food.example.com/mcp`.
3. Select OAuth with dynamic client registration.
4. Start the connection, sign in on the Food Reader consent page, review the
   requested read permissions and approve them.

OAuth discovery advertises Authorization Code + PKCE (`S256`), dynamic client
registration, refresh-token rotation, revocation, protected-resource metadata,
and the resource indicator bound to the exact MCP URL.

## Available tools

| Tool | Data |
|---|---|
| `get_data_inventory` | Connections, row counts and date coverage |
| `get_profile` | Profile, goals and current nutrition targets |
| `get_meals` | Meals and macro/micronutrient history |
| `get_withings_measurements` | Weight and body composition |
| `get_oura_daily` | Activity, sleep, readiness, heart rate, SpO2, stress/recovery, cardiovascular, workouts, sessions, tags and rest mode |
| `get_health_summary` | Combined nutrition, Oura and Withings trends and correlations |

Every tool is declared read-only. Every database query uses the user ID from the
validated MCP access token; a client cannot provide or override that ID.

## Security properties

- Access and refresh tokens are random opaque values; only SHA-256 hashes are stored.
- Dynamically issued client secrets are encrypted at rest with the application's
  `JWT_SECRET`-derived key.
- Authorization codes expire after 10 minutes and can be used only once.
- Access tokens default to 60 minutes; refresh tokens default to 30 days and rotate
  on every use.
- Tokens are bound to the exact `/mcp` resource and the requesting Food Reader user.
- Consent pages disable framing, caching, referrers and third-party content.
- Redirect URIs require HTTPS, except loopback localhost URLs for development.

Changing `JWT_SECRET` invalidates encrypted OAuth client secrets and signed consent
requests, so keep it stable and private in production.
