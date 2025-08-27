#!/bin/bash
set -euo pipefail
PROJECT=$1
REGION=$2
ACCESS_SECRET=$(openssl rand -hex 32)
if gcloud secrets describe ACCESS_SECRET --project $PROJECT >/dev/null 2>&1; then
  echo -n "$ACCESS_SECRET" | gcloud secrets versions add ACCESS_SECRET --project $PROJECT --data-file=- >/dev/null
else
  echo -n "$ACCESS_SECRET" | gcloud secrets create ACCESS_SECRET --project $PROJECT --data-file=- >/dev/null
fi
if [ -f firebase.json ]; then
  if gcloud secrets describe FIREBASE_JSON --project $PROJECT >/dev/null 2>&1; then
    gcloud secrets versions add FIREBASE_JSON --project $PROJECT --data-file=firebase.json >/dev/null
  else
    gcloud secrets create FIREBASE_JSON --project $PROJECT --data-file=firebase.json >/dev/null
  fi
fi
echo "ACCESS_SECRET=$ACCESS_SECRET"
