# TeamChat AI - GCP deployment helper (PowerShell)
# Run from repository root. Set variables below before running.

param(
    [string]$GCP_PROJECT = $env:GCP_PROJECT,
    [string]$REGION = "us-central1",
    [string]$CLOUD_RUN_URL = ""  # Fill after first backend deploy, then re-run for frontend
)

if (-not $GCP_PROJECT) {
    Write-Host "Set GCP_PROJECT (e.g. `$env:GCP_PROJECT = 'my-project-id')" -ForegroundColor Yellow
    exit 1
}

Write-Host "Project: $GCP_PROJECT Region: $REGION" -ForegroundColor Cyan

# 1. Firestore
Write-Host "`n1. Deploying Firestore rules and indexes..." -ForegroundColor Green
firebase deploy --only firestore

# 2. Backend (Cloud Run)
Write-Host "`n2. Deploying backend to Cloud Run..." -ForegroundColor Green
Push-Location backend
gcloud run deploy teamchat-api --source . --region $REGION --allow-unauthenticated `
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$GCP_PROJECT,VERTEX_AI_LOCATION=$REGION"
Pop-Location

$serviceUrl = (gcloud run services describe teamchat-api --region $REGION --format "value(status.url)" 2>$null)
if ($serviceUrl) {
    Write-Host "Backend URL: $serviceUrl" -ForegroundColor Cyan
    Write-Host "If this was your first deploy, set CLOUD_RUN_URL and run again to build frontend with this URL." -ForegroundColor Yellow
}

# 3. Frontend (only if CLOUD_RUN_URL is set)
if ($CLOUD_RUN_URL) {
    Write-Host "`n3. Building frontend with API URL: $CLOUD_RUN_URL" -ForegroundColor Green
    if (-not (Test-Path "frontend\.env.production")) {
        Write-Host "Create frontend\.env.production with VITE_API_URL=$CLOUD_RUN_URL and Firebase config. See .env.production.example" -ForegroundColor Yellow
        exit 1
    }
    Push-Location frontend
    npm run build
    Pop-Location
    Write-Host "`n4. Deploying frontend to Firebase Hosting..." -ForegroundColor Green
    firebase deploy --only hosting
    Write-Host "`nDone. Your live URL is above (Hosting URL)." -ForegroundColor Green
} else {
    Write-Host "`n3. Skipping frontend. After first run, set CLOUD_RUN_URL to the Cloud Run URL and run:" -ForegroundColor Yellow
    Write-Host "   .\deploy.ps1 -CLOUD_RUN_URL 'https://teamchat-api-xxxxx-uc.a.run.app'" -ForegroundColor White
}
