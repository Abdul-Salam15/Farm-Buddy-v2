# FarmBuddy

**AI-powered agricultural advisor for Nigerian smallholder farmers**

FarmBuddy is a full-stack agricultural assistant that delivers personalised, real-time advice to smallholder farmers in Nigeria and West Africa. It combines a Next.js Progressive Web App with a Django REST backend, OpenAI (GPT-4o / GPT-4o-mini / Whisper), live weather data, voice interaction in four Nigerian languages, and a full-featured Telegram bot — all designed for low-connectivity, low-literacy environments.

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
- [Security & Privacy](#security--privacy)
- [Deployment](#deployment)
- [Author](#author)

---

## Features

| Category | Feature | Description |
|---|---|---|
| 🤖 **AI Advice** | Personalised Chat | GPT-4o-mini advice tailored to the farmer's soil type, location, crop history, and pest profile with streaming responses |
| 🧠 **Explainability** | Sources & Context | Each AI response cites which profile attributes or past conversations informed the answer |
| 🌍 **Localisation** | 4 Languages | Full UI and AI support for English, Hausa, Igbo, and Yoruba |
| 📸 **Vision** | Plant Disease Diagnosis | Upload a leaf photo — GPT-4o Vision identifies diseases, confidence level, and recommends treatments |
| 🔊 **Voice Input** | Speech-to-Text | Browser Web Speech API + OpenAI Whisper fallback for reliable transcription in any language |
| 🔉 **Voice Output** | Text-to-Speech | YarnGPT multilingual voices (Idera, Zainab, Chinenye) with streaming audio playback |
| 🌦️ **Weather** | Contextual Forecasts | Live weather and 5-day forecasts injected into AI context via OpenWeatherMap |
| 🔍 **Search** | Conversation Search | Full-text search across all past conversations with in-message snippets |
| 👤 **Accounts** | Cross-Platform Auth | Web signup, Telegram signup, and secure account linking between platforms |
| 🔐 **Recovery** | Dual Password Reset | Security question recovery (no email required) + email OTP via Brevo |
| 📁 **Chat History** | Conversation Management | Create, rename, delete, and switch between persistent chat threads |
| 🌙 **Dark Mode** | Theme Toggle | System-aware dark/light mode with green accent theming |
| 📱 **Telegram Bot** | Full Bot Experience | 13 commands covering chat, plant diagnosis, weather, voice, and farm management |
| 📶 **PWA** | Offline Support | Installable on mobile home screen; service-worker cached assets work without connectivity |

---

## Architecture

### System Overview

```mermaid
graph TD
    Browser["Browser / PWA\n(Next.js 16 + React 19)"]
    Django["Django 6 API\n(Backend)"]
    OpenAI["OpenAI API\n(GPT-4o-mini / GPT-4o / Whisper)"]
    Weather["OpenWeatherMap API"]
    YarnGPT["YarnGPT TTS API\n(Nigerian Voices)"]
    Brevo["Brevo Email API\n(OTP Reset)"]
    DB["SQLite / PostgreSQL"]
    Telegram["Telegram Bot\n(python-telegram-bot)"]

    Browser -- "HTTP / Fetch (NDJSON streaming)" --> Django
    Telegram -- "Async Polling" --> Django
    Django -- "Chat + Vision + STT" --> OpenAI
    Django -- "Current + 5-day Forecast" --> Weather
    Django -- "Voice Synthesis" --> YarnGPT
    Django -- "OTP Emails" --> Brevo
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
    AI[OpenAI API]

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

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | Next.js 16.1.6 / React 19.2.4 / TypeScript 5.7.3 | App Router, streaming fetch |
| **Styling** | Tailwind CSS 4.2 / Radix UI / Shadcn UI | 25+ accessible components |
| **State / Forms** | React Hook Form 7.54 + Zod | Schema validation |
| **Charts** | Recharts 2.15 | Weather forecast visualisation |
| **Backend** | Python 3.12 / Django 6.0 | REST + streaming NDJSON |
| **Web Server** | Gunicorn | WSGI, single worker (free tier compatible) |
| **AI — Chat** | OpenAI `gpt-4o-mini` | Streaming, tool-use (weather function calling) |
| **AI — Vision** | OpenAI `gpt-4o` | Plant disease diagnosis with bounding-box XAI |
| **AI — STT** | OpenAI `whisper-1` | Audio transcription (WebM, Ogg, MP4, WAV) |
| **AI — TTS** | YarnGPT API | Voices: Idera (EN/YO), Zainab (HA), Chinenye (IG) |
| **Weather** | OpenWeatherMap REST v2.5 | Current + 5-day forecast, city or lat/lon |
| **Email** | Brevo (Sendinblue) API | OTP password reset emails |
| **Telegram** | python-telegram-bot | Async polling, 13 commands |
| **Database** | SQLite (dev) / PostgreSQL via `dj-database-url` (prod) | Django ORM |
| **Static Files** | WhiteNoise | Compressed manifest storage |
| **Admin UI** | Django Jazzmin | Custom branded admin dashboard |
| **Deployment** | Vercel (frontend) / Render (backend) | Free-tier compatible |

---

## Project Structure

```
Farm-Buddy-v2/
│
├── app/                        # Next.js frontend (App Router)
│   ├── page.tsx                # Landing / home page
│   ├── chat/                   # Main chat interface (streaming, voice, image upload)
│   ├── login/                  # Authentication
│   ├── signup/                 # Two-step registration (account → farm profile)
│   ├── profile/                # Farm profile management + Telegram link token
│   ├── settings/               # Password change, security answer, preferences
│   ├── forgot-password/        # Security question + email OTP reset
│   ├── offline/                # PWA offline fallback page
│   └── i18n/
│       └── dictionaries/       # en.json, ha.json, ig.json, yo.json
│
├── components/                 # Shared React components (Shadcn UI)
├── hooks/                      # Custom React hooks
├── lib/
│   └── config.ts               # Centralised API_BASE_URL
├── public/                     # Static assets, PWA icons, manifest.json, sw.js
│
└── backend/
    ├── accounts/               # User auth, FarmerProfile model, password recovery
    ├── chat/                   # Conversations, Messages, AI views, context builder
    │   ├── context_builder.py  # System prompt builder + XAI ref parser
    │   └── management/
    │       └── commands/       # run_telegram_bot management command
    ├── telegram_bot/           # Async Telegram bot (bot_logic.py)
    ├── utils/
    │   ├── openai_api.py       # OpenAI integration (chat + vision + STT + TTS)
    │   ├── weather_api.py      # OpenWeatherMap integration + AI tool handler
    │   └── image_processing.py # Image validation and compression (≤1024px, JPEG 85)
    ├── farmbuddy_web/          # Django project config (settings, urls, wsgi)
    ├── requirements.txt
    ├── Procfile                # Render / Heroku process definitions
    ├── build.sh                # CI build script
    └── start.sh                # Production start script
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12 | See `backend/runtime.txt` |
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

## Environment Variables

### Backend — `backend/.env`

```env
# Django core
SECRET_KEY=your_long_random_secret_key_here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:3000

# Database (defaults to SQLite if omitted)
DATABASE_URL=sqlite:///db.sqlite3
# PostgreSQL example:
# DATABASE_URL=postgresql://user:password@localhost/farmbuddy

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Text-to-Speech
YARNGPT_API_KEY=your_yarngpt_api_key

# Weather
OPENWEATHER_API_KEY=your_openweathermap_key

# Email OTP (Brevo / Sendinblue)
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=noreply@yourdomain.com

# Telegram bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_BOT_USERNAME=YourBotUsername
```

> **Production note:** `SECRET_KEY` must be set and `DEBUG` must be `False` in production.

### Frontend — `.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

In production, set this to your deployed backend URL.

---

## API Reference

All endpoints are served from the Django backend (`http://localhost:8000`).

### Authentication — `/accounts/`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/accounts/signup/` | Step 1 — create user account |
| `POST` | `/accounts/signup/farm/` | Step 2 — save farm profile |
| `POST` | `/accounts/login/` | Log in and start session |
| `POST` | `/accounts/logout/` | End session |
| `GET / POST` | `/accounts/profile/` | Get or update farmer profile |
| `GET / POST` | `/accounts/settings/` | Get or update settings, change password, security answer |
| `POST` | `/accounts/update-language/` | Switch preferred language |
| `POST` | `/accounts/forgot-password/` | Reset password via security question or email OTP |

### Chat — `/chat/`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat/send/` | Send message — returns NDJSON stream with chunks + final refs |
| `POST` | `/chat/upload/` | Upload plant image — returns NDJSON streamed diagnosis |
| `POST` | `/chat/new/` | Create a new conversation |
| `GET` | `/chat/api/list/` | List all conversations for current user |
| `GET` | `/chat/api/history/<id>/` | Get full message history for a conversation |
| `GET` | `/chat/api/search/` | Full-text search across all conversations |
| `POST` | `/chat/api/rename/<id>/` | Rename a conversation |
| `POST` | `/chat/api/delete/<id>/` | Delete a conversation |
| `POST` | `/chat/api/weather/` | Fetch weather and cache in session context |
| `POST` | `/chat/api/transcribe/` | Transcribe uploaded audio via OpenAI Whisper |
| `GET / POST` | `/chat/api/speak/` | Convert text to speech via YarnGPT |

> **Streaming format:** `/send/` and `/upload/` return `application/x-ndjson`. Each line is either `{"chunk": "..."}` (incremental token) or `{"success": true, "full_text": "...", "references": [...], "conversation_id": 123}` (final message with XAI sources).

---

## Telegram Bot

The FarmBuddy Telegram bot provides a full farming assistant experience without needing the web app.

### Commands

| Command | Description |
|---|---|
| `/start` | Select language; choose to log in, sign up, or link a web account |
| `/login` | Multi-step login flow |
| `/signup` | Full registration flow (account + farm profile) entirely in Telegram |
| `/connect` | Link an existing web account using a token from the Profile page |
| `/dashboard` | View farm summary — location, soil type, farm size, crops |
| `/tip` | Get today's agricultural tip in your language |
| `/random_tip` | Get a random farming tip |
| `/forecast` | Receive a weather forecast chart for your farm location |
| `/edit_profile` | Update farm location, size, soil type, and crops |
| `/language` | Switch between English, Hausa, Igbo, and Yoruba |
| `/forgot` | Reset password via security question |
| `/logout` | Unlink your account from this Telegram chat |

### Media Support

- **Text messages** — Full AI conversations with profile-aware context, streamed response
- **Voice notes** — Transcribed via OpenAI Whisper; AI responds in text
- **Plant photos** — GPT-4o Vision analyses leaf images for disease diagnosis

---

## Progressive Web App

FarmBuddy is installable as a PWA for an app-like experience on mobile:

- **Installable** — Prompts to add to home screen on Android and iOS
- **Offline fallback** — Custom offline page when connectivity is lost
- **Cached assets** — Core app shell served by service worker for fast subsequent loads
- **Responsive** — Mobile-first design optimised for low-end Android devices

---

## Security & Privacy

| Mechanism | Details |
|---|---|
| **CSRF Protection** | All state-changing endpoints require a valid CSRF token, including the PWA frontend |
| **Password Hashing** | Django PBKDF2 + SHA256 |
| **Security Answer** | Hashed recovery answer — allows password reset with no email address (ideal for rural users) |
| **Email OTP** | 6-digit one-time code via Brevo with 60-second rate limit |
| **Session Cookies** | `HttpOnly`, `SameSite=Lax`; `Secure` enforced in production |
| **Data Isolation** | Each farmer's chat history and profile are strictly scoped to their authenticated account |
| **CORS** | Origin whitelist enforced via `django-cors-headers` |

---

## Troubleshooting

| Issue | Solution |
|---|---|
| **`ffmpeg` not found** | Required for audio processing. Install and ensure it's on your PATH. |
| **"Invalid API Key"** | Check `backend/.env`. `OPENAI_API_KEY` must have access to GPT-4o and Whisper. |
| **OTP emails not arriving** | Set `BREVO_API_KEY` and `BREVO_SENDER_EMAIL`. Verify the sender in your Brevo dashboard. |
| **Port 8000 in use** | `python manage.py runserver 8001` then update `NEXT_PUBLIC_API_URL` in `.env.local`. |
| **PWA not installing** | PWAs require HTTPS or `localhost`. Access via `localhost:3000` during development. |
| **Telegram bot not responding** | Check `TELEGRAM_BOT_TOKEN` and confirm `run_telegram_bot` process is running. |
| **Sources not showing** | Ensure user is logged in and has a complete farm profile — the AI cites profile fields and conversation history. |

---

## Deployment

### Backend — Render / Railway / VPS

Set all environment variables from the [Environment Variables](#environment-variables) section, then:

**Build command:**
```bash
cd backend && ./build.sh
```

Runs: `pip install -r requirements.txt` → `collectstatic` → `migrate` → creates default admin user.

**Start command:**
```bash
cd backend && ./start.sh
```

Runs: Telegram bot in background → `gunicorn farmbuddy_web.wsgi`.

Or via **Procfile** (Render / Heroku):
```
web: gunicorn farmbuddy_web.wsgi --log-file -
worker: python manage.py run_telegram_bot
```

### Frontend — Vercel

1. Connect the repository to Vercel
2. Set root directory to `/` (project root, not `app/`)
3. Add `NEXT_PUBLIC_API_URL=https://your-backend-url.com`
4. Deploy

### Production checklist

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` set to a long random string
- [ ] `ALLOWED_HOSTS` set to your domain
- [ ] `FRONTEND_URL` set to your Vercel frontend URL (for CORS)
- [ ] `DATABASE_URL` pointing to PostgreSQL (recommended for production)
- [ ] HTTPS enforced — `SECURE_SSL_REDIRECT=True` activates automatically when `DEBUG=False`
- [ ] All API keys set: `OPENAI_API_KEY`, `OPENWEATHER_API_KEY`, `YARNGPT_API_KEY`, `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `TELEGRAM_BOT_TOKEN`

---

## Author

- **Abdul-Salam15** — [github.com/Abdul-Salam15](https://github.com/Abdul-Salam15)

---

## License

MIT
