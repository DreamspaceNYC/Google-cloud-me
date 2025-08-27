# GCP Control Plane

Minimal monorepo deploying a FastAPI backend and static Next.js frontend to Cloud Run.

## Quickstart
Prereqs: gcloud CLI, project ID, region.

```bash
bash app/infra/seed_secrets.sh PROJECT_ID REGION
bash app/infra/deploy.sh PROJECT_ID REGION AUTH_MODE=hmac
```

### Test (HMAC mode)
```bash
TS=$(date +%s)
SIG=$(printf "GET\n/apis\n$TS" | openssl dgst -sha256 -hmac "<ACCESS_SECRET>" -hex | awk '{print $2}')
curl https://BACKEND_URL/apis -H "x-ts: $TS" -H "x-sig: $SIG"
```

### Test (secure mode)
```bash
TOKEN=$(gcloud auth print-identity-token)
curl https://BACKEND_URL/apis -H "Authorization: Bearer $TOKEN"
```

## Add new function
1. Create backend route using dedicated service account and client library.
2. Add frontend form and renderer.
3. Update IAM roles and redeploy.
