# FarmBuddy — Backend

Django 6 REST API powering the FarmBuddy agricultural assistant.

For full project documentation, setup instructions, and architecture diagrams see the [root README](../README.md).

---

## Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver     # http://localhost:8000
```

Create `backend/.env`:

```env
SECRET_KEY=your_secret_key
DEBUG=True
FRONTEND_URL=http://localhost:3000
GOOGLE_API_KEY=your_gemini_key
OPENWEATHER_API_KEY=your_openweather_key
YARNGPT_API_KEY=your_yarngpt_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_BOT_USERNAME=YourBotUsername
```

## Apps

| App | Purpose |
|---|---|
| `accounts` | User registration, login, FarmerProfile model, password recovery |
| `chat` | Conversations, messages, AI streaming, image upload, weather, TTS/STT |
| `telegram_bot` | Async Telegram bot — mirrors web features for Telegram users |

## Management Commands

```bash
# Run the Telegram bot
python manage.py run_telegram_bot
```

## Deployment

See the [Deployment section](../README.md#deployment) in the root README.
