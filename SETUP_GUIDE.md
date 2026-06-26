# How to Run Farm-Buddy-v2 on a New Laptop — Step by Step

## Step 1: Install Prerequisites

The laptop needs these installed first:

| Software | Version | Download |
|----------|---------|----------|
| **Python** | 3.12.x | https://www.python.org/downloads/ |
| **Node.js** | 18 or higher | https://nodejs.org/ |
| **pnpm** | Latest | Run `npm install -g pnpm` after installing Node.js |
| **ffmpeg** | Any | Required for audio processing (see below) |

### Installing ffmpeg
- **Windows:** Download from https://ffmpeg.org/download.html, add to system PATH
- **macOS:** `brew install ffmpeg`
- **Ubuntu/Debian:** `sudo apt install ffmpeg`

---

## Step 2: Copy the Project from Flash Drive

Copy the entire `Farm-Buddy-v2` folder from the flash drive to any location on the laptop (e.g., `Desktop` or `Documents`).

---

## Step 3: Create the Backend Environment File

Create a file called `.env` inside the `backend/` folder with these contents:

```env
# Django
SECRET_KEY=any-long-random-string-at-least-50-characters-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:3000

# Database (SQLite works for local dev — no setup needed)
DATABASE_URL=sqlite:///db.sqlite3

# OpenAI (REQUIRED — powers the AI chat, plant diagnosis, and voice)
OPENAI_API_KEY=sk-your-openai-key-here

# Weather (REQUIRED — powers the weather forecast feature)
OPENWEATHER_API_KEY=your-openweathermap-key-here

# Text-to-Speech (OPTIONAL — falls back to Google TTS if missing)
YARNGPT_API_KEY=your-yarngpt-key-here

# Email OTP for password reset (OPTIONAL)
BREVO_API_KEY=your-brevo-key-here
BREVO_SENDER_EMAIL=noreply@yourdomain.com

# Telegram Bot (OPTIONAL — only if you want the Telegram bot running)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_BOT_USERNAME=myfarmbuddy_bot

# Cloudinary image storage (OPTIONAL — uses local disk if missing)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-key
CLOUDINARY_API_SECRET=your-cloudinary-secret
```

### Where to get the API keys

| Key | Where to get it |
|-----|-----------------|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `OPENWEATHER_API_KEY` | https://openweathermap.org/api (free tier: 1000 calls/day) |
| `YARNGPT_API_KEY` | https://yarngpt.ai |
| `BREVO_API_KEY` | https://www.brevo.com |
| `TELEGRAM_BOT_TOKEN` | Message @BotFather on Telegram |
| Cloudinary keys | https://cloudinary.com (free tier: 25GB/month) |

**Minimum to run:** You need at least `OPENAI_API_KEY` and `OPENWEATHER_API_KEY`. Everything else is optional.

---

## Step 4: Create the Frontend Environment File

Create a file called `.env.local` in the **project root** folder (not inside `backend/`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Step 5: Set Up and Start the Backend

Open a terminal/command prompt, navigate to the project, and run:

```bash
cd Farm-Buddy-v2/backend
python -m venv venv
```

Then activate the virtual environment:
- **Windows:** `venv\Scripts\activate`
- **macOS/Linux:** `source venv/bin/activate`

Then install dependencies, set up the database, and start the server:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The backend will be running at **http://localhost:8000**

### Admin dashboard (optional)
Visit http://localhost:8000/admin  
Create a superuser with: `python manage.py createsuperuser`

---

## Step 6: Set Up and Start the Frontend

Open a **second** terminal/command prompt and run:

```bash
cd Farm-Buddy-v2
pnpm install
pnpm dev
```

The frontend will be running at **http://localhost:3000**

---

## Step 7: Open the App

Open a browser and go to **http://localhost:3000**

You should see the FarmBuddy login page. From there you can:
1. Sign up as a new farmer
2. Chat with the AI farming advisor
3. Upload plant photos for disease diagnosis
4. Check weather forecasts
5. Use voice input/output in 4 Nigerian languages (English, Hausa, Igbo, Yoruba)

---

## Step 8: Telegram Bot (Optional)

If the Telegram bot is needed, open a **third** terminal:

```bash
cd Farm-Buddy-v2/backend
source venv/bin/activate        # or venv\Scripts\activate on Windows
python manage.py run_telegram_bot
```

The bot will start polling Telegram (no webhook setup needed).

---

## Quick Reference: What's Running Where

| Service | URL | Terminal |
|---------|-----|----------|
| Backend API | http://localhost:8000 | Terminal 1 |
| Frontend App | http://localhost:3000 | Terminal 2 |
| Admin Dashboard | http://localhost:8000/admin | (same as backend) |
| Telegram Bot | Polls Telegram API | Terminal 3 (optional) |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pnpm: command not found` | Run `npm install -g pnpm` |
| `python: command not found` | Try `python3` instead, or reinstall Python and check "Add to PATH" |
| CORS errors in browser | Make sure `FRONTEND_URL=http://localhost:3000` is in `backend/.env` |
| Voice features not working | Make sure `ffmpeg` is installed and in PATH |
| Weather not loading | Check that `OPENWEATHER_API_KEY` is valid |
| Chat returns errors | Check that `OPENAI_API_KEY` is valid and has credits |
| Port 3000/8000 already in use | Kill the other process or change ports |

---

## Version Summary

| Component | Version |
|-----------|---------|
| Python | 3.12.9 |
| Django | 6.0 |
| Node.js | 18+ |
| Next.js | 16.1.6 |
| React | 19.2.4 |
| TypeScript | 5.7.3 |
