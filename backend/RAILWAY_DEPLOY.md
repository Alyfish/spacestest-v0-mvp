# Railway Deploy Runbook (Backend)

This backend is ready for Railway with config in:
- `/Users/aly/Desktop/newtest/backend/railway.json`

## 1) Supabase pre-req
Run migration SQL files in `/Users/aly/Desktop/newtest/backend/migrations` (001-005) in your Supabase project.

## 2) Create Railway service
1. Create a Railway project from this GitHub repo.
2. Create/select backend service.
3. Set **Root Directory** to `backend`.
4. In service settings, set **Config as Code File Path** to:
   - `/backend/railway.json`

## 3) Environment variables in Railway
Minimum required:
- `ENVIRONMENT=production`
- `USE_SUPABASE_DATA=true`
- `USE_SUPABASE_JOBS=true`
- `SUPABASE_URL=...`
- `SUPABASE_SERVICE_KEY=...`
- `GOOGLE_API_KEY=...`
- `SERP_API_KEY=...` (or `EXA_API_KEY`, ideally both)
- `CORS_ALLOW_ORIGINS=https://your-ios-web-origin-if-needed`
- `CORS_ALLOW_CREDENTIALS=true`

Optional:
- `OPENAI_API_KEY`
- `IMGBB_API_KEY`
- `ANTHROPIC_API_KEY` (or legacy `CLAUDE_API_KEY`)

## 4) Deploy + verify
After deploy, verify:

```bash
curl -i https://<railway-domain>/health
curl -i https://<railway-domain>/api/health
```

Both should return HTTP 200.

You can also run:

```bash
cd /Users/aly/Desktop/newtest/backend
./scripts/railway_smoke_check.sh https://<railway-domain>
```

## 5) Point iOS app to Railway
Build/run with:

```bash
--dart-define=API_BASE_URL=https://<railway-domain>/api
```

Default localhost behavior remains unchanged for local development.
