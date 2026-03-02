# Deploy TeamChat AI to GCP (Live URL)

Follow these steps to deploy the app to GCP and get a **workable public URL** to share.

## Prerequisites

- **Google Cloud SDK** (`gcloud`) installed and logged in: `gcloud auth login`
- **Firebase CLI**: `npm install -g firebase-tools` then `firebase login`
- **Node.js 18+** and **Python 3.11+** (for local build and seed)
- A **GCP project** with billing enabled (same project for Firebase and Cloud Run)

---

## 1. One-time GCP setup

### 1.1 Set project and enable APIs

```bash
export GCP_PROJECT=your-gcp-project-id
gcloud config set project $GCP_PROJECT

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable firebase.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable identitytoolkit.googleapis.com
```

### 1.2 Create Firebase project (if not already)

- Go to [Firebase Console](https://console.firebase.google.com), add/select project (use same `GCP_PROJECT`).
- Enable **Authentication** → Sign-in method → **Email/Password**.
- Create **Firestore Database** (Native mode, choose region).
- In Project settings, copy the **Firebase config** (apiKey, authDomain, projectId, etc.) for the frontend.

### 1.3 Service account for Cloud Run

Cloud Run will use its default service account, or a custom one. Ensure it has:

- **Firebase Admin / Firestore**: e.g. roles `Cloud Datastore User`, `Firebase Authentication Admin` (or a custom role that can verify ID tokens and read/write Firestore).
- **Vertex AI**: e.g. `Vertex AI User`.

Optional: use a **Firebase service account key** (JSON) and pass it to Cloud Run as base64 (see step 3).

---

## 2. Deploy Firestore rules and indexes

From the **repository root** (`e:\Doctustech`):

```bash
# Link Firebase to your project (once)
cp .firebaserc.example .firebaserc
# Edit .firebaserc and set "default" to your GCP project ID

firebase deploy --only firestore
```

---

## 3. Deploy backend to Cloud Run

From the repository root:

```bash
cd backend

# Build and push the container (replace REGION if needed, e.g. us-central1)
export REGION=us-central1
gcloud run deploy teamchat-api \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$GCP_PROJECT" \
  --set-env-vars "VERTEX_AI_LOCATION=$REGION"
```

If you use a **Firebase service account JSON key** (recommended for Auth):

```bash
# Encode the key (run from backend folder, key file in current dir)
# PowerShell:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("path\to\serviceAccountKey.json"))

# Then set the secret on Cloud Run:
gcloud run services update teamchat-api --region $REGION \
  --set-env-vars "FIREBASE_SERVICE_ACCOUNT_JSON=<paste-base64-string>"
```

**Copy the Cloud Run URL** (e.g. `https://teamchat-api-xxxxx-uc.a.run.app`). You need it for the frontend.

---

## 4. Build and deploy frontend to Firebase Hosting

Set the **backend API URL** and **Firebase config** at build time, then deploy.

From the repository root:

```bash
cd frontend

# Create .env.production (use your real values)
# Replace CLOUD_RUN_URL with the URL from step 3 (no trailing slash)
cat > .env.production << 'EOF'
VITE_API_URL=https://teamchat-api-xxxxx-uc.a.run.app
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-gcp-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abc123
EOF

npm install
npm run build
cd ..
```

Deploy hosting:

```bash
firebase deploy --only hosting
```

Firebase CLI will output the **Hosting URL**, e.g.:

- `https://your-project-id.web.app`
- or `https://your-project-id.firebaseapp.com`

**This is the workable URL to share.**

---

## 5. Seed data (test users and rooms)

Run the seed scripts **locally** (with a service account key that has Firestore and Auth admin access):

```bash
cd backend
# Set path to your service account JSON
$env:GOOGLE_APPLICATION_CREDENTIALS = "path\to\serviceAccountKey.json"   # PowerShell
# export GOOGLE_APPLICATION_CREDENTIALS="path/to/serviceAccountKey.json"  # Bash

# Create Firebase Auth users (password: TestPass123!)
python -m scripts.create_auth_users

# Seed Firestore (orgs, user docs, rooms, sample messages)
python -m scripts.seed_data
```

---

## 6. Add authorized domain (Firebase Auth)

In **Firebase Console** → Authentication → Settings → **Authorized domains**, ensure your Hosting domain is listed (e.g. `your-project-id.web.app`). It is usually added automatically when you deploy Hosting.

---

## Summary: URLs and credentials to share

| What | Value |
|------|--------|
| **Live app URL** | `https://YOUR_PROJECT_ID.web.app` (or from `firebase deploy --only hosting` output) |
| **Test logins** | See README: e.g. sarah@acme.example.com / TestPass123! (Acme), alice@globex.example.com / TestPass123! (Globex) |
| **Tenant isolation** | Log in as Acme user → only Acme rooms. Log in as Globex user → only Globex rooms. |

Put the **Live app URL** and **test credentials** in the README (section "Live Demo & Test Credentials") and in your submission email.
