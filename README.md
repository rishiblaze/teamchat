# TeamChat AI — Multi-Tenant Collaborative AI Chat Platform

A production-grade multi-tenant chat platform where teams participate in the same room and interact with **Gemini AI** together. Built for the Technical Assessment (Staff/Principal Full-Stack Engineer).

## Features

- **Multi-tenancy**: Organizations with isolated data (rooms, messages, users)
- **Real-time collaborative chat**: Firestore listeners for instant messages, typing indicators, presence
- **Gemini AI**: Invoke with `@Gemini` or `@AI`; streaming responses visible to all room participants with user attribution
- **Auth**: Firebase Auth (email/password); no signup flow — use pre-seeded test users

## Tech Stack

| Component      | Choice                    |
|---------------|---------------------------|
| Frontend      | React 18, TypeScript, Vite, Firestore real-time |
| Backend       | Python, FastAPI           |
| Auth          | Firebase Auth             |
| Real-time DB  | Firestore                 |
| AI            | Vertex AI (Gemini)        |
| Deploy        | Cloud Run (backend), Firebase Hosting (frontend) |

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  React (Vite)   │────▶│  Firebase Auth   │     │  Firestore      │
│  Firebase SDK   │     │  Firestore       │◀────│  (rooms,        │
│  (presence,     │     │  (messages,      │     │   messages,     │
│   typing, msgs) │     │   presence)       │     │   presence)     │
└────────┬────────┘     └──────────────────┘     └─────────────────┘
         │
         │  POST /api/chat/invoke (Bearer token)
         ▼
┌─────────────────┐     ┌──────────────────┐
│  FastAPI         │────▶│  Vertex AI        │
│  (Cloud Run)     │     │  (Gemini)         │
│  - Verify token  │     │  Streaming        │
│  - Tenant check  │     └──────────────────┘
│  - Write AI msg  │
└─────────────────┘
```

- **Tenant isolation**: Every Firestore read/write is scoped by `orgId`; security rules enforce `memberIds` and `orgId`. Backend validates org/room access on each invoke.
- **Real-time**: Clients subscribe to `rooms/{roomId}/messages`, `presence`, and `typing`; AI message doc is updated token-by-token by the backend so all participants see streaming.

## Live Demo & Test Credentials

**Live URL**: After deploying to GCP (see [Deploy to GCP](#deploy-to-gcp)), your app will be available at:
- **`https://YOUR_PROJECT_ID.web.app`** (or the URL shown by `firebase deploy --only hosting`)

Replace the placeholder below with that URL before sharing with evaluators.

| Item | Value |
|------|--------|
| **Live app** | `https://_______________.web.app` |
| **Backend API** | Cloud Run URL (e.g. `https://teamchat-api-xxxxx-uc.a.run.app`) |

**Test logins** (after running seed + create_auth_users):

| Organization | Email                     | Password     | Role   |
|-------------|----------------------------|--------------|--------|
| Acme Corp   | sarah@acme.example.com     | TestPass123! | admin  |
| Acme Corp   | mike@acme.example.com      | TestPass123! | member |
| Acme Corp   | lisa@acme.example.com      | TestPass123! | member |
| Globex Inc  | alice@globex.example.com   | TestPass123! | admin  |
| Globex Inc  | bob@globex.example.com     | TestPass123! | member |

**Verify tenant isolation**: Log in as Sarah (Acme), see only Acme rooms. Log in as Alice (Globex), see only Globex rooms.

## Local Development

### Prerequisites

- Python 3.11+
- Node 18+
- Firebase project + GCP project (same or linked)
- Service account key with Firestore + Auth admin + Vertex AI

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# Edit .env: GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT, VERTEX_AI_LOCATION
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with Firebase config and VITE_API_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:5173`, log in with a test user.

### Seed data

1. Create Firebase Auth users (once):

   ```bash
   cd backend
   set GOOGLE_APPLICATION_CREDENTIALS=path\to\serviceAccountKey.json
   python -m scripts.create_auth_users
   ```

2. Seed Firestore (orgs, user docs, rooms, sample messages):

   ```bash
   python -m scripts.seed_data
   ```

### Firestore rules & indexes

```bash
firebase deploy --only firestore
```

## Deploy to GCP (shareable live URL)

To get a **workable public URL** for evaluators:

1. **Backend** → Cloud Run  
2. **Frontend** → Firebase Hosting  
3. **Firestore** → rules and indexes  
4. **Seed** → test users and rooms (run locally after deploy)

**Full step-by-step:** see **[DEPLOY.md](DEPLOY.md)**.

Quick checklist:

- [ ] Enable APIs (Cloud Run, Firestore, Firebase, Vertex AI)
- [ ] `firebase deploy --only firestore`
- [ ] `gcloud run deploy teamchat-api --source backend/ --allow-unauthenticated` (+ env vars)
- [ ] Set `VITE_API_URL` in `frontend/.env.production` to your Cloud Run URL
- [ ] `cd frontend && npm run build && cd .. && firebase deploy --only hosting`
- [ ] Run seed scripts (create_auth_users, seed_data) locally
- [ ] Add **Live URL** and **test credentials** to this README and submission email

### What to submit (per assessment)

1. **Live URL** – Firebase Hosting URL (e.g. `https://YOUR_PROJECT_ID.web.app`)
2. **Test credentials** – e.g. Acme: sarah@acme.example.com / TestPass123!; Globex: alice@globex.example.com / TestPass123!
3. **Repo** – GitHub link (add evaluators as collaborators if private)
4. **Email** – gonzalo.alessandrelli@doctustech.com, cc Himadri Sharma

## Project Layout

```
backend/
  app/
    api/          # health, chat (invoke)
    core/         # firebase, auth
    services/     # tenant, gemini
  scripts/
    create_auth_users.py
    seed_data.py
frontend/
  src/
    components/   # Login, Chat
    lib/          # firebase, api
firestore.rules
firestore.indexes.json
```

## License

Proprietary — Technical Assessment.
