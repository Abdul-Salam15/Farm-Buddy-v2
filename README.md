# FarmBuddy

**AI-powered agricultural advisor for Nigerian smallholder farmers**

FarmBuddy is a full-stack agricultural assistant that delivers personalised, real-time advice to smallholder farmers in Nigeria and West Africa. It combines a Next.js Progressive Web App with a Django REST backend, Google Gemini AI, live weather data, voice interaction in four Nigerian languages, and a full-featured Telegram bot — all designed for low-connectivity, low-literacy environments.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Telegram Bot](#telegram-bot)
- [Progressive Web App](#progressive-web-app)
- [Deployment](#deployment)
- [Author](#author)

---

## Features

| Category | Feature | Description |
|---|---|---|
| 🤖 **AI Advice** | Personalised Chat | Advice tailored to the farmer's soil type, location, crop history, and pest profile |
| 🌍 **Localisation** | 4 Languages | Full UI and AI support for English, Hausa, Igbo, and Yoruba |
| 📸 **Vision** | Plant Diagnosis | Upload a leaf photo — Gemini Vision identifies diseases and recommends treatments |
| 🔊 **Voice I/O** | Speech In & Out | Speak questions via Gemini STT; listen to replies in Nigerian voices via YarnGPT |
| 🌦️ **Weather** | Contextual Forecasts | Live weather and 5-day forecasts injected automatically into AI responses |
| 👤 **Accounts** | Cross-Platform Auth | Web signup, Telegram signup, and account linking between platforms |
| 🔐 **Recovery** | Security Question | Password recovery via a secret question — no email required |
| 📁 **Chat History** | Conversation Management | Create, rename, delete, and switch between persistent chat threads |
| 📱 **Telegram Bot** | Full Bot Experience | Chat, plant diagnosis, weather forecasts, and farm management without the web app |
| 📶 **PWA** | Offline Support | Installable on mobile home screen; cached assets work without connectivity |

---

## Recent Improvements 🚀

FarmBuddy is constantly evolving. Key recent updates include:
- **Robust Internationalization**: Enforced English as the global default with hydration-safe context management.
- **Enhanced Signup Flow**: Improved multi-step signup with structured error handling, name synchronization, and optional farm detail sanitization.
- **Security Hardening**: Fixed critical vulnerabilities including unprotected JSON parsing, cross-platform password reset logic, and CSRF protection.
- **Voice Performance**: Optimized TTS (Text-to-Speech) latency and improved STT (Speech-to-Text) accuracy for Nigerian accents.
- **UI/UX Polishing**: Fixed hydration errors, improved chat layout responsiveness, and standardized translation dictionaries across 4 languages.

---

## Security & Privacy 🔐

The safety of farmer data is a priority. FarmBuddy implements:
- **CSRF Protection**: All state-changing operations require a valid CSRF token, even for the PWA frontend.
- **Secure Password Hashing**: Utilizes Django's PBKDF2 with SHA256 for all user credentials.
- **Security Question Recovery**: A stateless recovery mechanism using a hashed security answer (grandfather's name), allowing password resets without an email address — ideal for rural users.
- **Data Isolation**: Each farmer's chat history and farm metadata are strictly isolated and only accessible to the authenticated owner.


---

## Architecture

### System Overview

```mermaid
graph TD
    Browser["Browser / PWA\n(Next.js 16 + React 19)"]
    Django["Django 6 API\n(Backend)"]
    Gemini["Google Gemini API\n(Flash Lite / Vision / STT)"]
    Weather["OpenWeatherMap API"]
    YarnGPT["YarnGPT TTS API\n(Nigerian Voices)"]
    DB["SQLite / PostgreSQL"]
    Telegram["Telegram Bot\n(python-telegram-bot)"]

    Browser -- "HTTP / Fetch (NDJSON streaming)" --> Django
    Telegram -- "Polling" --> Django
    Django -- "Text + Vision + STT" --> Gemini
    Django -- "Current + Forecast" --> Weather
    Django -- "Voice Synthesis" --> YarnGPT
    Django -- "Persistence" --> DB
```

### Telegram Bot Architecture

```mermaid
graph TD
    Farmer((Farmer))
    TG[Telegram Client]
    BotLogic[bot_logic.py]
    ORM[Django ORM]
    DB[(Database)]
    AI[Gemini API]

    Farmer -- "Text / Photo / Voice" --> TG
    TG -- "Webhook / Polling" --> BotLogic
    BotLogic -- "Profile + History" --> ORM
    ORM -- "Read / Write" --> DB
    BotLogic -- "Profile Context Injection" --> AI
    AI -- "Personalised Advice" --> BotLogic
    BotLogic -- "Localised Reply" --> TG
```

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Frontend** | Next.js / React / TypeScript | Next.js 16.1.6 / React 19 |
| **Styling** | Tailwind CSS / Shadcn UI / Radix UI | Tailwind 4 |
| **Backend** | Python / Django | Python 3.11.9 / Django 6.0 |
| **AI — Chat & Vision** | Google Gemini | `gemini-flash-lite-latest` |
| **AI — Speech-to-Text** | Google Gemini Audio | via `google-generativeai` SDK |
| **AI — Text-to-Speech** | YarnGPT | Nigerian voices: Idera, Zainab, Chinenye |
| **Weather** | OpenWeatherMap | REST API v2.5 |
| **Telegram Bot** | python-telegram-bot | Async polling |
| **Database** | SQLite (dev) / PostgreSQL (prod) | via `dj-database-url` |
| **Static Files** | WhiteNoise | Compressed manifest storage |
| **Web Server** | Gunicorn | WSGI |

---

## Project Structure

```
Farm-Buddy-v2/
│
├── app/                        # Next.js frontend (App Router)
│   ├── chat/                   # Chat interface
│   ├── login/                  # Login page
│   ├── signup/                 # Two-step signup
│   ├── profile/                # Farm profile management
│   ├── settings/               # User settings & password change
│   ├── forgot-password/        # Password recovery
│   ├── offline/                # PWA offline fallback
│   └── i18n/
│       └── dictionaries/       # en.json, ha.json, ig.json, yo.json
│
├── components/                 # Shared React components (Shadcn UI)
├── hooks/                      # Custom React hooks
├── lib/
│   └── config.ts               # Centralised API_BASE_URL
├── public/                     # Static assets, PWA icons
│
└── backend/
    ├── accounts/               # User auth, FarmerProfile model, forms
    ├── chat/                   # Conversations, Messages, AI views
    │   └── management/
    │       └── commands/       # run_telegram_bot management command
    ├── telegram_bot/           # Async Telegram bot logic
    ├── utils/
    │   ├── gemini_api.py       # Gemini AI integration (chat + vision + STT)
    │   ├── weather_api.py      # OpenWeatherMap integration
    │   └── image_processing.py # Image validation and compression
    ├── farmbuddy_web/          # Django project config (settings, urls, wsgi)
    ├── requirements.txt
    ├── Procfile                # Heroku / Render process definitions
    ├── build.sh                # CI build script
    └── start.sh                # Production start script
```

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11.9 | See `backend/runtime.txt` |
| Node.js | 18+ | Required for Next.js |
| pnpm | Latest | Frontend uses `pnpm-lock.yaml`; `npm` also works |
| ffmpeg | Any | Required for audio processing (pydub) |

**Install ffmpeg:**
```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Windows — download from https://ffmpeg.org/download.html
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Abdul-Salam15/Farm-Buddy-v2.git
cd Farm-Buddy-v2
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver     # Runs on http://localhost:8000
```

### 3. Frontend setup

```bash
# From the project root (not the app/ subdirectory)
pnpm install                   # or: npm install
pnpm dev                       # Runs on http://localhost:3000
```

### 4. Telegram bot (optional)

In a third terminal with the backend virtualenv active:

```bash
cd backend
python manage.py run_telegram_bot
```

---

## Troubleshooting 🛠️

### Common Issues

| Issue | Solution |
|---|---|
| **`ffmpeg` not found** | Required for audio processing. Ensure it's installed and in your system PATH. |
| **"Invalid API Key"** | Check your `backend/.env` file. Ensure `GOOGLE_API_KEY` has permission for Gemini Flash and Vision. |
| **Port 8000 already in use** | Run the backend on a different port: `python manage.py runserver 8001`. Update `NEXT_PUBLIC_API_URL` in `.env.local` accordingly. |
| **PWA not installing** | PWAs require HTTPS or `localhost` to work. Ensure you are accessing the app via `localhost:3000` during development. |
| **Telegram Bot not responding** | Ensure your `TELEGRAM_BOT_TOKEN` is correct and that the `run_telegram_bot` process is running. |


---

## Environment Variables

### Backend — `backend/.env`

Create `backend/.env` with the following variables:

```env
# Django core
SECRET_KEY=your_long_random_secret_key_here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:3000

# Database (optional — defaults to SQLite)
DATABASE_URL=sqlite:///db.sqlite3
# PostgreSQL example:
# DATABASE_URL=postgresql://user:password@localhost/farmbuddy

# AI APIs
GOOGLE_API_KEY=your_google_gemini_api_key
YARNGPT_API_KEY=your_yarngpt_api_key

# Weather
OPENWEATHER_API_KEY=your_openweathermap_key

# Telegram bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_BOT_USERNAME=YourBotUsername
```

> **Production note:** `SECRET_KEY` must be set in production or the server will refuse to start. `DEBUG` must be `False`.

### Frontend — `.env.local`

Create `.env.local` in the **project root** (alongside `package.json`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

In production, set this to your deployed backend URL:

```env
NEXT_PUBLIC_API_URL=https://your-backend.example.com
```

---

## API Reference

All API endpoints are served from the Django backend at `http://localhost:8000`.

### Authentication — `/accounts/`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/accounts/signup/` | Step 1 — create user account |
| `POST` | `/accounts/signup/farm/` | Step 2 — save farm profile |
| `POST` | `/accounts/login/` | Log in and start session |
| `POST` | `/accounts/logout/` | End session |
| `GET / POST` | `/accounts/profile/` | Get or update farmer profile |
| `GET / POST` | `/accounts/settings/` | Get or update user settings, change password |
| `POST` | `/accounts/update-language/` | Switch preferred language |
| `POST` | `/accounts/forgot-password/` | Verify security answer and reset password |

### Chat — `/chat/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/chat/` | Main chat interface (HTML) |
| `POST` | `/chat/send/` | Send message — returns NDJSON stream |
| `POST` | `/chat/upload/` | Upload plant image — returns NDJSON stream |
| `POST` | `/chat/new/` | Create a new conversation |
| `GET` | `/chat/api/list/` | List all conversations for current user |
| `GET` | `/chat/api/history/<id>/` | Get messages for a specific conversation |
| `POST` | `/chat/api/rename/<id>/` | Rename a conversation |
| `POST` | `/chat/api/delete/<id>/` | Delete a conversation |
| `POST` | `/chat/api/weather/` | Fetch weather and store in session context |
| `POST` | `/chat/api/transcribe/` | Transcribe audio file to text (STT) |
| `GET / POST` | `/chat/api/speak/` | Convert text to audio (TTS) |

> Streaming endpoints (`/send/`, `/upload/`) return newline-delimited JSON (`application/x-ndjson`). Each line is a JSON object with either `{"chunk": "..."}` for incremental content or `{"success": true, "full_text": "...", "references": [...]}` as the final message.

---

## Telegram Bot

The FarmBuddy Telegram bot provides a full farming assistant experience for users who prefer or only have access to Telegram.

### Commands

| Command | Description |
|---|---|
| `/start` | Select language and choose to log in, sign up, or link a web account |
| `/dashboard` | View farm summary — location, soil type, farm size |
| `/tip` | Get a daily agricultural tip in your language |
| `/forecast` | Receive a 7-day weather forecast as a chart image |
| `/edit_profile` | Update farm location, size, and soil type |
| `/language` | Switch between English, Hausa, Igbo, and Yoruba |
| `/logout` | Unlink your account from this Telegram chat |

### Capabilities

- **Text chat** — Full AI conversations with profile-aware context
- **Voice notes** — Audio transcribed via Gemini STT, answered in text
- **Plant photos** — Leaf images analysed for disease diagnosis
- **Signup** — Complete account creation entirely within Telegram
- **Password reset** — Recover account via security question, no email needed
- **Account linking** — Connect an existing web account using a one-time link token from the Profile page

---

## Progressive Web App

FarmBuddy is installable as a PWA for an app-like experience on mobile:

- **Installable** — Prompts to add to home screen on Android and iOS
- **Offline fallback** — Custom offline page shown when connectivity is lost
- **Cached assets** — Core app shell cached via service worker for fast loads
- **Responsive** — Optimised for small-screen, low-end Android devices

---

## Deployment

### Backend — Render / Railway / VPS

Set all environment variables from the [Environment Variables](#environment-variables) section in your platform dashboard, then use the provided scripts:

**Build command:**
```bash
cd backend && ./build.sh
```

Which runs:
```bash
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
```

**Start command:**
```bash
cd backend && ./start.sh
```

Which runs:
```bash
python manage.py run_telegram_bot &
gunicorn farmbuddy_web.wsgi:application --bind 0.0.0.0:$PORT
```

Or use the **Procfile** directly (Heroku / Render):
```
web: gunicorn farmbuddy_web.wsgi --log-file -
worker: python manage.py run_telegram_bot
```

### Frontend — Vercel

1. Connect the repository to Vercel
2. Set the root directory to `/` (project root, not `app/`)
3. Add `NEXT_PUBLIC_API_URL=https://your-backend-url.com` as an environment variable
4. Deploy

### Production checklist

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` set to a long random string
- [ ] `ALLOWED_HOSTS` set to your domain
- [ ] `FRONTEND_URL` set to your frontend URL (for CORS)
- [ ] `DATABASE_URL` pointing to PostgreSQL (recommended over SQLite for production)
- [ ] HTTPS enforced — `SECURE_SSL_REDIRECT=True` is enabled automatically when `DEBUG=False`
- [ ] All API keys set (`GOOGLE_API_KEY`, `OPENWEATHER_API_KEY`, `YARNGPT_API_KEY`, `TELEGRAM_BOT_TOKEN`)

---

## Author

- **Abdul-Salam15** — [github.com/Abdul-Salam15](https://github.com/Abdul-Salam15)

---

## License

MIT
