#!/bin/bash
set -euo pipefail
PROJECT=$1
REGION=$2
AUTH_MODE=${AUTH_MODE:-hmac}
BACKEND_SERVICE=${BACKEND_SERVICE:-backend}
FRONTEND_SERVICE=${FRONTEND_SERVICE:-frontend}
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-*}

# enable apis
gcloud services enable \
  run.googleapis.com \
  serviceusage.googleapis.com \
  secretmanager.googleapis.com \
  texttospeech.googleapis.com \
  --project $PROJECT

# service accounts
if ! gcloud iam service-accounts describe sa-core@$PROJECT.iam.gserviceaccount.com --project $PROJECT >/dev/null 2>&1; then
  gcloud iam service-accounts create sa-core --project $PROJECT
fi
gcloud projects add-iam-policy-binding $PROJECT --member serviceAccount:sa-core@$PROJECT.iam.gserviceaccount.com --role roles/serviceusage.serviceUsageViewer >/dev/null
if ! gcloud iam service-accounts describe sa-tts@$PROJECT.iam.gserviceaccount.com --project $PROJECT >/dev/null 2>&1; then
  gcloud iam service-accounts create sa-tts --project $PROJECT
fi
gcloud projects add-iam-policy-binding $PROJECT --member serviceAccount:sa-tts@$PROJECT.iam.gserviceaccount.com --role roles/texttospeech.user >/dev/null

# build images
gcloud builds submit app/backend --tag gcr.io/$PROJECT/backend --project $PROJECT
gcloud builds submit app/frontend --tag gcr.io/$PROJECT/frontend --project $PROJECT

# deploy backend
gcloud run deploy $BACKEND_SERVICE \
  --image gcr.io/$PROJECT/backend \
  --region $REGION \
  --project $PROJECT \
  --service-account sa-tts@$PROJECT.iam.gserviceaccount.com \
  --set-env-vars AUTH_MODE=$AUTH_MODE,ALLOWED_ORIGINS=$ALLOWED_ORIGINS \
  --set-secrets ACCESS_SECRET=ACCESS_SECRET:latest,FIREBASE_JSON=FIREBASE_JSON:latest \
  --min-instances=1 \
  --allow-unauthenticated

backend_url=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --project $PROJECT --format='value(status.url)')

# deploy frontend
gcloud run deploy $FRONTEND_SERVICE \
  --image gcr.io/$PROJECT/frontend \
  --region $REGION \
  --project $PROJECT \
  --set-env-vars NEXT_PUBLIC_API_BASE=$backend_url,NEXT_PUBLIC_AUTH_MODE=$AUTH_MODE \
  --min-instances=1 \
  --allow-unauthenticated
