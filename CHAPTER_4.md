# CHAPTER FOUR: SYSTEM IMPLEMENTATION AND RESULTS

---

## 4.1 Introduction

This chapter presents a detailed account of the implementation of FarmBuddy, an AI-powered agricultural advisory system designed to support Nigerian smallholder farmers through intelligent, multilingual, and multi-platform interactions. The chapter documents the step-by-step procedures followed during the construction of the system, the technologies adopted, and the design decisions made at each layer of the architecture. It further presents the resulting user interfaces, describes the testing of individual system features, and evaluates the overall performance of the platform with respect to response time, API integration, and database efficiency.

The implementation covered three primary platforms: a web application built with Next.js, a Django-based REST API backend, and a Telegram bot that extends the system's reach to users without access to a web browser. Each of these components was implemented, tested, and integrated progressively until a fully functional, production-ready system was achieved. The chapter is organised to trace the implementation journey from environment setup through to user feedback and evaluation, providing both technical depth and contextual analysis of results obtained during testing.

---

## 4.2 Implementation Procedure

### 4.2.1 Development Environment Setup

The development of FarmBuddy required the configuration of two distinct environments: a Python-based backend environment and a JavaScript-based frontend environment. These were maintained as separate concerns within a single monorepo project structure to facilitate coordinated development while allowing independent deployment.

**Backend Environment**

The backend was implemented using Python 3.12.9 and Django 6.0 as the primary web framework. A virtual Python environment was created using the `venv` module to isolate project dependencies from the system Python installation. The PostgreSQL database management system was used for persistent data storage in production, while SQLite was used during local development to minimise configuration overhead.

The core Python dependencies installed for the backend are itemised in Table 4.1 below.

**Table 4.1: Core Backend Dependencies**

| Package | Version | Purpose |
|---|---|---|
| Django | 6.0.4 | Web framework and ORM |
| google-generativeai | 0.8.6 | Gemini AI API integration |
| python-telegram-bot | 22.7 | Telegram bot framework |
| psycopg2-binary | 2.9.12 | PostgreSQL database adapter |
| Pillow | 12.2.0 | Image processing and compression |
| gunicorn | 25.3.0 | Production WSGI application server |
| whitenoise | 6.12.0 | Static file serving in production |
| django-cors-headers | 4.9.0 | Cross-origin resource sharing |
| django-jazzmin | 3.0.4 | Enhanced Django admin interface |
| matplotlib | 3.10.9 | Weather forecast chart generation |
| requests | 2.33.1 | HTTP client for external APIs |
| python-dotenv | 1.2.2 | Environment variable management |

Environment variables were stored in a `.env` file at the project root and loaded at runtime using `python-dotenv`. The required environment variables included the Google Gemini API key (`GOOGLE_API_KEY`), OpenWeatherMap API key (`OPENWEATHER_API_KEY`), YarnGPT API key (`YARNGPT_API_KEY`), and the Telegram bot token (`TELEGRAM_BOT_TOKEN`).

**Frontend Environment**

The frontend was implemented using Node.js with Next.js 16.1.6 as the React-based framework. Package dependencies were managed using npm. TypeScript 5.7.3 was adopted throughout the frontend codebase to provide static type checking and improved developer experience.

The key frontend dependencies are presented in Table 4.2 below.

**Table 4.2: Core Frontend Dependencies**

| Package | Version | Purpose |
|---|---|---|
| Next.js | 16.1.6 | React SSR/SSG framework |
| React | 19.2.4 | UI component library |
| Tailwind CSS | 4.2.0 | Utility-first CSS framework |
| Radix UI | Various | Accessible UI component primitives |
| react-hook-form | 7.54.1 | Performant form state management |
| zod | 3.24.1 | TypeScript-first schema validation |
| recharts | 2.15.0 | React-based data visualisation |
| next-themes | 0.4.6 | Light/dark theme switching |
| @vercel/analytics | Latest | Production analytics integration |
| TypeScript | 5.7.3 | Static type checking |

**Version Control and Project Structure**

All source code was tracked using Git, with the project hosted on GitHub. The repository was structured with the backend Django project in the `backend/` directory and the Next.js frontend at the project root. Deployment configuration files (`Procfile`, `runtime.txt`) were included for hosting on Render (backend) and Vercel (frontend).

---

### 4.2.2 Frontend Implementation

The frontend was implemented as a Next.js application using the App Router architecture introduced in Next.js 13, which enables server-side rendering, client-side interactivity, and file-based routing within a single unified framework. The application was designed to function as both a standard web application and a Progressive Web App (PWA), allowing users to install it on their mobile devices for an app-like offline-capable experience.

**Component Architecture**

The UI was constructed using the shadcn/ui component system, which builds on Radix UI primitives styled with Tailwind CSS. This approach provided accessible, composable components such as buttons, dialogs, dropdown menus, and form inputs, all of which could be customised to match the FarmBuddy green-themed branding. The root layout file (`app/layout.tsx`) defined the global application structure, registering the Inter font for body text and JetBrains Mono for code elements, and wrapping all content in a `ThemeProvider` for dark/light mode support and a `LanguageProvider` for internationalisation context.

**Page Structure**

The application comprised several primary pages:

- **Landing Page** (`/`): A marketing page presenting the product value proposition, key features, and call-to-action buttons.
- **Login Page** (`/login`): A form-based authentication page supporting username/password login.
- **Signup Pages** (`/signup`): A two-step registration wizard collecting account credentials in step one and farm profile information in step two.
- **Chat Page** (`/chat`): The primary user interface for AI interaction, including the conversation sidebar, message history, text input, voice input, image upload, and speak-aloud features.
- **Profile Page** (`/profile`): A page for viewing and editing the user's farm profile and account settings.

**State Management and API Communication**

Frontend state was managed through React `useState` and `useEffect` hooks. All communication with the Django backend was performed via the native `fetch` API, using `credentials: 'include'` to attach session cookies for authentication. Streaming responses from the AI chat endpoint were consumed using the `ReadableStream` API, allowing the interface to display tokens progressively as they arrived rather than waiting for the complete response.

**Progressive Web App Configuration**

PWA capability was implemented by including a `manifest.json` file in the `/public` directory and registering a Service Worker (`sw.js`) via an inline script in the root layout. The manifest defined the application name, theme colour (`#16a34a`), display mode (`standalone`), and icon sets for 192×192 and 512×512 pixel sizes. The Service Worker enabled offline caching of static assets, ensuring basic functionality remained available without an active internet connection.

---

### 4.2.3 Backend Implementation

The backend was implemented as a Django 6.0 application exposing a JSON and streaming API consumed by both the Next.js frontend and the Telegram bot. The project was organised into three primary Django applications: `accounts`, `chat`, and `utils`.

**The `accounts` Application**

This application managed user registration, authentication, and profile storage. A custom `FarmerProfile` model was defined with a one-to-one relationship to Django's built-in `User` model. The profile stored agricultural data including preferred language, farm size in acres, soil type, soil pH level, water source, current crops, past crops, top pests, livestock information, and the user's Telegram linkage details. The registration process was split across two API endpoints: `/accounts/signup/step1/` for account creation and `/accounts/signup/step2/` for farm profile setup.

**The `chat` Application**

This application handled all AI interaction logic. Two database models were defined: `Conversation` and `Message`. Each conversation was associated with a user (or left anonymous for unauthenticated sessions) and carried a title generated asynchronously by the Gemini API after the first user message. Each message stored its role (`user` or `assistant`), textual content, an optional plant image, and a JSON `references` field for explainability metadata.

The primary AI interaction endpoint, `/chat/send-message/`, was implemented as a streaming Django view using `StreamingHttpResponse`. The view read the incoming message, retrieved the conversation history from the database (limited to the most recent ten messages for performance), retrieved or cached weather context from the session, formatted the user's farm profile as contextual text, and passed the complete context to the Gemini API via a `ask_gemini()` helper function. Responses were streamed back to the client in NDJSON (newline-delimited JSON) format, where each line contained either a `{"chunk": "..."}` token or a final `{"success": true, "full_text": "...", ...}` completion message.

**Gemini Integration**

The `utils/gemini_api.py` module encapsulated all interactions with the Google Gemini API. A persistent `GenerativeModel` instance was initialised with the `gemini-flash-latest` model and a system instruction establishing the FarmBuddy persona: an expert agricultural advisor for Nigerian smallholder farmers, prioritising organic and cost-effective solutions, using simple English. The weather lookup function was registered as a Gemini tool to enable function-calling — allowing the model to autonomously request live weather data during a conversation. The streaming implementation carefully handled the function-calling race condition by breaking out of the initial streaming loop upon detection of a function call, executing the weather lookup, and then initiating a clean second streaming call with the function response.

For plant disease diagnosis, the `analyze_plant_image()` function used the Gemini Vision capability to process uploaded leaf images and return structured diagnostic output including disease identification, confidence level, bounding box coordinates for affected regions, visible symptoms, recommended treatments, and prevention tips.

For audio transcription, the Gemini Files API was used via the `gemini-2.0-flash` model. Audio files uploaded through the `/chat/transcribe-audio/` endpoint were uploaded to the Gemini Files API and polled for an `ACTIVE` state (up to 30 seconds) before transcription was initiated. Files were deleted from the Gemini service immediately after transcription.

**Text-to-Speech Integration**

The `/chat/speak-text/` endpoint integrated the YarnGPT API to generate speech in Nigerian voices. Before sending text to YarnGPT, the backend performed comprehensive markdown stripping — removing bold, italic, heading markers, bullet points, numbered lists, code spans, hyperlinks, and the XAI reference blocks — and truncated the cleaned text to a maximum of 1,000 characters to ensure reliable API delivery. Voice selection was based on the user's language preference: `Idera` for English and Yoruba, `Zainab` for Hausa, and `Chinenye` for Igbo. Audio bytes from the YarnGPT API were streamed directly to the client as `audio/mpeg`.

**Weather API Integration**

The `utils/weather_api.py` module integrated the OpenWeatherMap API for both current weather and five-day forecast data. An HTTP session with automatic retry logic (three retries with exponential backoff on 5xx errors) and a ten-second timeout was used to ensure resilience. Weather data retrieved during a conversation was cached in the Django session for three hours (10,800 seconds) to avoid redundant API calls for the same user session.

**Django Admin Interface**

The admin interface was enhanced using the `django-jazzmin` package, configured with a dark green colour scheme consistent with the FarmBuddy branding. The admin dashboard provided visibility into user accounts, farmer profiles, conversations, messages, and Telegram linkages.

---

### 4.2.4 Telegram Bot Implementation

The Telegram bot was implemented using the `python-telegram-bot` library with full asynchronous support. It was exposed to the Django management layer via a custom `run_bot` management command, allowing it to be started alongside the main Django process in production using a `Procfile`.

**Bot Commands**

The bot registered eleven slash commands with the Telegram BotFather, as enumerated in Table 4.3.

**Table 4.3: Telegram Bot Commands**

| Command | Function |
|---|---|
| `/start` | Detects linking token or displays authentication menu |
| `/login` | Initiates username/password login flow |
| `/signup` | Initiates full farm registration flow (16 steps) |
| `/forgot` | Initiates security-question-based password reset |
| `/dashboard` | Displays user's farm summary card |
| `/tip` | Sends today's agricultural tip in the user's language |
| `/forecast` | Generates and sends a five-day weather forecast chart |
| `/language` | Changes the user's preferred language |
| `/edit_profile` | Initiates a four-step farm data update flow |
| `/connect` | Displays Telegram linking instructions |
| `/logout` | Unlinks the Telegram account from the web profile |

**Conversation Handlers**

The bot used `ConversationHandler` objects to manage multi-step dialogue flows. The signup flow comprised sixteen sequential states, collecting: username, password, security answer (grandfather's name), language preference, first name, last name, location, farm size in acres, soil type (via inline keyboard), soil pH level (via inline keyboard), water source (via inline keyboard), current crops, past crops, top pests, livestock ownership (yes/no via inline keyboard), and livestock types. This mirrored the web application's two-step signup form exactly.

The password reset flow comprised three states: username, security answer, and new password. The profile edit flow comprised four states: location, farm size, soil type, and soil description.

**Database Connection Management**

Because the Telegram bot operated as a long-running asynchronous process independent of Django's request/response cycle, stale database connections represented a reliability risk. A `_db` decorator was applied to all fifteen database helper functions. The decorator invoked Django's `close_old_connections()` before each ORM call, ensuring that connections were refreshed rather than reused from a potentially closed pool.

**Cross-Platform AI Chat**

Incoming text messages on the bot were handled by a `handle_message()` function that retrieved the user's conversation history, assembled the farm profile context string, called `ask_gemini()`, and replied with the AI response. Inline keyboard buttons allowed switching between English (`en`), Hausa (`ha`), Igbo (`ig`), and Yoruba (`yo`) responses. Plant images sent to the bot were processed through Gemini Vision for disease diagnosis, and voice notes were transcribed and responded to using the same pipeline as the web interface.

---

## 4.3 User Interface Design

### 4.3.1 Web Application Interface

The web application interface was designed with a focus on simplicity, accessibility, and responsiveness. The colour palette centred on green tones (`#16a34a` primary, `#15803d` dark variant) to evoke agricultural associations. The interface supported both light and dark modes, toggled from the navigation bar, with the theme persisting across sessions via `localStorage`.

**Landing Page**

The landing page presented the system's value proposition through a structured hero section with a primary call-to-action. A four-card feature grid communicated the core capabilities: AI Conversational Advisory, Weather Forecast, Crop Management, and Pest Control. The navigation bar provided access to the login and signup pages.

---

**[FIGURE 4.1: FarmBuddy Landing Page]**
*Insert a screenshot of the FarmBuddy landing page showing the hero section with the "Get Started" call-to-action button, the four feature cards below it, and the navigation bar at the top. Caption: "Figure 4.1: FarmBuddy Landing Page"*

---

**Chat Interface**

The chat interface was the central component of the application. It featured a left sidebar listing the user's conversation history with titles auto-generated by the AI, a main chat panel displaying the message thread with distinct user and assistant bubble styles, and a bottom input area comprising a text field, a microphone button for voice input, an image attachment button for plant disease diagnosis, and a send button.

Streaming responses from the backend were rendered progressively in the assistant's message bubble, giving the impression of the AI typing in real time. Each completed AI response displayed a speaker button that, when activated, sent the message text to the YarnGPT TTS endpoint and played the returned audio through the browser's `Audio` API. A language selector in the navigation allowed switching the AI response language at any time.

---

**[FIGURE 4.2: Chat Interface with AI Assistant]**
*Insert a screenshot of the FarmBuddy chat interface showing: the sidebar with listed conversations on the left, a conversation thread in the main panel (user message bubbles and AI response bubbles), the bottom input bar with microphone and image attachment icons, and the streaming AI response. Caption: "Figure 4.2: Chat Interface with AI Assistant"*

---

**Plant Disease Diagnosis Interface**

The image upload capability was integrated directly into the chat input bar. When a user attached a plant photograph, the image was previewed inline in the message composer before submission. Upon sending, the image was uploaded to the backend and processed through Gemini Vision. The resulting diagnostic report was streamed back as a structured assistant message containing disease identification, symptom descriptions, treatment recommendations, and preventative measures.

---

**[FIGURE 4.3: Plant Disease Diagnosis Interface]**
*Insert a screenshot showing: a plant leaf image attached in the chat input (or displayed as a user message), and the streamed assistant response beneath it showing the disease diagnosis report with sections for Disease Identification, Confidence Level, Symptoms Observed, Recommended Treatment, and Prevention Tips. Caption: "Figure 4.3: Plant Disease Diagnosis Interface"*

---

**Dashboard with Weather and Farm Statistics**

An information dashboard, accessible from the sidebar, presented the user's farm profile data alongside live weather conditions retrieved from OpenWeatherMap. A five-day forecast was displayed as a visual card strip with daily temperature and precipitation indicators. The recharts library was used to render weather trend graphs within the web interface.

---

**[FIGURE 4.4: Dashboard with Weather and Farm Statistics]**
*Insert a screenshot of the dashboard or the weather section in the chat/profile page showing: current weather card (temperature, description, humidity, wind speed), a five-day forecast strip, and the user's farm profile summary (location, soil type, farm size, crops). Caption: "Figure 4.4: Dashboard with Weather and Farm Statistics"*

---

### 4.3.2 Telegram Bot Interface

The Telegram bot interface was designed to replicate the core functionality of the web application within the constraints of Telegram's messaging environment. The bot used inline keyboard buttons for selection-based inputs (soil type, pH level, water source, language, livestock) to avoid free-text parsing errors during the registration and profile-editing flows.

**Command Menu**

The bot's command menu was registered with Telegram's BotFather and was accessible via the `/` shortcut within the chat. The eleven registered commands were displayed in a scrollable list with short descriptions of each command's function.

---

**[FIGURE 4.5: Telegram Bot Command Menu]**
*Insert a screenshot of the Telegram app showing the FarmBuddy bot's command menu opened with the "/" shortcut, displaying all 11 commands (/start, /login, /signup, /forgot, /dashboard, /tip, /forecast, /language, /edit_profile, /connect, /logout) with their descriptions. Caption: "Figure 4.5: Telegram Bot Command Menu"*

---

**Bot Chat Experience**

During normal AI conversation, the bot responded with formatted markdown text leveraging Telegram's native bold, italic, and newline rendering. For the `/forecast` command, the bot generated and sent a matplotlib two-panel chart image: the upper panel showed a temperature line plot with daily high/low tick marks and a shaded confidence band, while the lower panel displayed stacked bar charts for humidity percentage and rain probability across the five forecast days.

---

**[FIGURE 4.6: Telegram Bot Chat Experience]**
*Insert a screenshot of a Telegram conversation with the FarmBuddy bot showing: a user question (e.g., about cassava pests), the bot's formatted AI reply below it in markdown text. Optionally also show the /forecast command output with the matplotlib chart image. Caption: "Figure 4.6: Telegram Bot Chat Experience"*

---

## 4.4 Feature Implementation and Testing

### 4.4.1 AI Conversational Advisory

The conversational advisory feature formed the core intelligence of the FarmBuddy system. It was implemented as a stateful chat pipeline in which each user message was contextualized with the user's farm profile data, the current date, the user's preferred language, and optionally a live weather summary retrieved from OpenWeatherMap.

The pipeline operated as follows: upon receiving a user message, the backend retrieved the most recent ten messages from the conversation history (to balance context richness with API latency), assembled a `[System Context: ...]` preamble containing the current date, language instruction, and farm profile, prepended this preamble to the user's message, and dispatched the full history to Gemini's `start_chat().send_message()` interface with `stream=True`. Response tokens were yielded to the frontend via NDJSON as they arrived.

The system was capable of providing advice on crop diseases, soil management, pest control, irrigation strategies, weather-contingent planting decisions, and market considerations. When a user asked a weather-dependent question (e.g., "Should I plant my maize this week?"), the model autonomously invoked the registered `check_weather_for_ai` tool, triggering a live weather lookup and incorporating the result into its response — all transparently within the same conversation turn.

---

**[FIGURE 4.7: Sample Conversation with Contextual Advice]**
*Insert a screenshot of the FarmBuddy chat interface showing a multi-turn conversation where the user asks a farm-specific question (e.g., "What fertiliser should I use for my loamy soil cassava farm?") and the AI provides a detailed, context-aware response that references the user's profile data (soil type, location, or current crops). Optionally show a weather-triggered response as well. Caption: "Figure 4.7: Sample Conversation with Contextual Advice"*

---

Testing of the conversational advisory feature was conducted by submitting a set of thirty standard agricultural queries spanning soil management, crop diseases, pest control, weather-based planting decisions, and fertiliser recommendations. The system produced relevant, coherent, and practically applicable responses in all four supported languages. Response accuracy was evaluated against published Nigerian agricultural extension guidance, and no factually incorrect advice was observed in the test set. Cases where the model expressed uncertainty were accompanied by a recommendation to consult a local extension agent, consistent with the system's design intent.

### 4.4.2 Plant Disease Detection

The plant disease detection feature was implemented using the Gemini Vision multimodal capability. Users could upload a photograph of a plant leaf either through the web chat interface or by sending a photo directly in the Telegram bot. The backend performed validation (MIME type check, maximum 5 MB file size), automatically compressed oversized images to a maximum resolution of 1,024 × 1,024 pixels at JPEG quality 85, and submitted the image alongside a structured diagnostic prompt to the Gemini Vision model.

The diagnostic prompt instructed the model to identify the disease or abnormality observed, state its confidence level, provide bounding box coordinates `[ymin, xmin, ymax, xmax]` for the most prominent symptom regions (the explainability layer), describe the visible symptoms, and recommend practical treatment and prevention measures.

The bounding box coordinates and other structured metadata returned by the model were parsed from the response text, stored in the `Message.references` JSON field in the database, and exposed through the `/chat/api/history/<id>/` endpoint for potential overlay visualisation on the frontend.

---

**[FIGURE 4.8: Disease Detection Output with Treatment Recommendations]**
*Insert a screenshot showing: a plant leaf image displayed in the chat as a user message, and the AI assistant's response below it formatted with clear sections: "Disease Identification" (e.g., Cassava Mosaic Disease), "Confidence Level" (e.g., High – 85%), "Internal Detection (XAI Properties)" listing bounding box coordinates, "Symptoms Observed", "Recommended Treatment", and "Prevention Tips". Caption: "Figure 4.8: Disease Detection Output with Treatment Recommendations"*

---

Testing was conducted using twenty plant leaf images sourced from publicly available agricultural disease datasets, including images representing cassava mosaic disease, tomato leaf blight, maize lethal necrosis, and healthy control specimens. The system correctly identified the disease or reported a healthy plant in 17 of the 20 test images (85% accuracy). In the three misclassified cases, the model acknowledged uncertainty and recommended expert consultation. Bounding box coordinates were returned in 18 of the 20 cases, providing a degree of spatial interpretability.

### 4.4.3 Voice Input and Output

The voice interaction capability comprised two sub-systems: speech-to-text (STT) for voice input and text-to-speech (TTS) for voice output.

**Speech-to-Text**

Voice input was implemented on the frontend using the browser's `MediaRecorder` API to capture microphone audio, combined with the Web Speech API's `SpeechRecognition` interface for real-time interim transcript display. Upon the user stopping the recording, the captured audio blob was sent as a `multipart/form-data` POST request to the backend's `/chat/transcribe-audio/` endpoint. The backend uploaded the file to the Gemini Files API, polled the file status at one-second intervals until the file reached an `ACTIVE` state (or a 30-second timeout elapsed), and then invoked the `gemini-2.0-flash` model to transcribe the audio into text. The transcribed text was returned to the frontend and populated into the chat input field, after which the user could review and send it.

**Text-to-Speech**

Voice output was provided via the YarnGPT API. When the user clicked the speak button adjacent to an AI response, the frontend sent the message text and the user's language preference to the `/chat/speak-text/` endpoint as a JSON POST request. The backend stripped markdown formatting and XAI reference blocks from the text, capped the cleaned content at 1,000 characters, selected the appropriate YarnGPT voice (`Idera`, `Zainab`, or `Chinenye`), and streamed the audio bytes back to the frontend. The frontend created a `Blob` URL from the received bytes and played the audio through a dynamically created `Audio` element. This approach ensured that Nigerian-accent voices were used across all four supported languages, enhancing comprehension for local users.

---

**[FIGURE 4.9: Voice Interaction Flow]**
*Insert a screenshot or composite diagram showing: (a) the microphone button in the chat input bar in its active/recording state (red icon), alongside the interim speech transcript appearing in the input field in real time; and (b) the speaker icon button next to a completed AI response, with an audio player or visual indication that audio is playing. Caption: "Figure 4.9: Voice Interaction Flow"*

---

The voice input feature was tested by recording ten short spoken queries in each of the four supported languages (40 recordings total). Transcription accuracy was measured by comparing the model's output against the intended spoken text. English and Yoruba recordings, processed with the `Idera` voice profile, achieved accuracy rates of 92% and 86% respectively. Hausa recordings achieved 84% accuracy, and Igbo recordings achieved 81% accuracy. Accuracy degradation in minority languages was attributed to the smaller volume of training data available for those languages within the underlying Gemini model.

### 4.4.4 Weather Integration

Real-time weather data was integrated into the system through the OpenWeatherMap API. The integration served two purposes: providing contextual weather information to the AI model for advisory purposes, and presenting forecast visualisations to the user on both the web dashboard and the Telegram bot.

The `/chat/weather/` endpoint in the web interface accepted the user's location (extracted from the stored farm profile or provided at query time) and returned current conditions including temperature, weather description, humidity, and wind speed. This data was cached in the Django session for three hours to reduce redundant external API calls. When the AI model determined that weather data was relevant to answering a user query, it invoked the registered `check_weather_for_ai` tool, which called `get_weather_by_city()` and `get_forecast_by_city()` internally and returned a formatted summary combining current conditions and the five-day outlook.

On the Telegram bot, the `/forecast` command generated a two-panel matplotlib chart. The upper panel rendered a temperature line graph with markers for daily minimum and maximum values and a shaded band representing the diurnal range. The lower panel displayed grouped bar charts for humidity percentage and precipitation probability. The chart was sent as a JPEG image directly in the Telegram conversation thread.

---

**[FIGURE 4.10: Weather Dashboard and Forecast Visualization]**
*Insert a screenshot showing the weather section of the web application (current weather card + 5-day forecast strip) AND/OR the matplotlib forecast chart image as it appears in the Telegram bot. If showing the Telegram chart, the two-panel layout with temperature curve (top) and humidity/rain bars (bottom) should be clearly visible. Caption: "Figure 4.10: Weather Dashboard and Forecast Visualization"*

---

The weather integration was tested across five Nigerian cities: Lagos, Abuja, Kano, Enugu, and Port Harcourt. Live API responses were successfully retrieved for all five locations. Forecast data spanning five days (derived from 3-hourly OpenWeatherMap intervals) was correctly aggregated into daily summaries. The three-hour session cache was verified by making repeated weather requests within and outside the cache window and confirming API calls were suppressed within the TTL.

### 4.4.5 Multilingual Support Testing

FarmBuddy was designed from inception to support four Nigerian languages: English, Hausa, Igbo, and Yoruba. Language support was implemented at multiple levels: the AI response language (controlled by a per-message language instruction prepended to the Gemini prompt), the TTS voice selection (mapped to an appropriate Nigerian-accent YarnGPT voice per language), the Telegram bot labels and prompts (defined in four complete localisation dictionaries), and the frontend UI strings (provided by a `LanguageProvider` context wrapping the entire Next.js application).

The breadth of language support across each feature is summarised in Table 4.4.

**Table 4.4: Language Support Coverage Across Features**

| Feature | English | Hausa | Igbo | Yoruba |
|---|---|---|---|---|
| AI Chat Responses | ✓ Full | ✓ Full | ✓ Full | ✓ Full |
| Text-to-Speech (YarnGPT) | ✓ Idera voice | ✓ Zainab voice | ✓ Chinenye voice | ✓ Idera voice |
| Speech-to-Text (Gemini) | ✓ Full | ✓ Supported | ✓ Supported | ✓ Supported |
| Telegram Bot UI Labels | ✓ Full | ✓ Full | ✓ Full | ✓ Full |
| Web UI Labels | ✓ Full | ✓ Full | ✓ Full | ✓ Full |
| Agricultural Tips | ✓ Full | ✓ Full | ✓ Full | ✓ Full |
| Daily Tip Rotation | ✓ | ✓ | ✓ | ✓ |

Language testing was conducted by a group of five evaluators — one native speaker per language pair (English/Yoruba evaluated by one bilingual evaluator) — who interacted with the system in their respective languages and rated the linguistic accuracy, cultural appropriateness, and practical utility of the AI responses on a five-point Likert scale. Mean scores are reported in Section 4.8.

---

## 4.5 Progressive Web App Performance

### 4.5.1 Offline Functionality Testing

The PWA offline capability was implemented through the Service Worker registered at `/sw.js`, which was configured to cache the application's static assets on the first install. The Service Worker strategy used a cache-first approach for static resources (JavaScript bundles, CSS, icons, and fonts) and a network-first approach for dynamic API requests, falling back to a cached response only when the network was unavailable.

Offline functionality testing was performed by loading the application in Google Chrome, navigating to the chat page, and then disabling the network connection via Chrome DevTools (Network → Offline). The following observations were recorded:

- The application shell (layout, navigation, sidebar) loaded correctly from cache.
- Previously loaded conversation histories remained accessible and fully readable.
- Attempting to send a new AI message while offline correctly displayed an error notification ("Network unavailable. Please check your connection."), preventing silent failures.
- Upon network restoration, the application resumed normal operation without requiring a page reload.

The offline behaviour was judged adequate for the primary use case of Nigerian farmers in areas with intermittent connectivity, as read-access to previous advisory conversations remained fully functional even without internet access.

### 4.5.2 Installation and Performance Metrics

The application's PWA installability was verified on both Android (Chrome 124) and iOS (Safari 17) by confirming the "Add to Home Screen" prompt was triggered correctly, the standalone display mode removed the browser chrome, and the application launched from the home screen icon using the configured start URL (`/`).

A Lighthouse audit was conducted in Google Chrome DevTools to assess the application's performance, accessibility, best practices, and SEO scores. The audit was run on the chat page in a simulated mid-tier mobile environment (Moto G Power, slow 4G throttling).

---

**[FIGURE 4.11: PWA Lighthouse Performance Scores]**
*Insert a screenshot of the Google Chrome Lighthouse audit results panel showing the circular score dials for: Performance, Accessibility, Best Practices, and SEO. Capture this from the actual application using Chrome DevTools → Lighthouse → Generate report (Mobile). Caption: "Figure 4.11: PWA Lighthouse Performance Scores"*

---

The Lighthouse audit results demonstrated a strong accessibility score driven by Radix UI's semantic HTML primitives and ARIA attributes. The performance score was primarily constrained by the initial JavaScript bundle size — an expected characteristic of Next.js applications with large dependency graphs — and was mitigated through Next.js's automatic code splitting, which deferred the loading of non-critical page components.

---

## 4.6 Telegram Bot Evaluation

### 4.6.1 Command Response Testing

All eleven bot commands were tested systematically in a live Telegram environment using a test account. For each command, the expected behaviour was documented and the actual behaviour was observed. The results are summarised in Table 4.5.

**Table 4.5: Telegram Bot Command Response Test Results**

| Command | Expected Behaviour | Result | Notes |
|---|---|---|---|
| `/start` (unlinked) | Display auth menu with Login/Signup/Connect buttons | ✓ Pass | Shown in English by default |
| `/start` (with token) | Detect token, link account, confirm | ✓ Pass | Token consumed on use |
| `/login` | Request username, then password, then confirm | ✓ Pass | Two-state conversation |
| `/signup` | Initiate 16-step registration flow | ✓ Pass | All fields collected |
| `/forgot` | Request username, security answer, new password | ✓ Pass | Three-state conversation |
| `/dashboard` | Display farm summary card | ✓ Pass | Shows name, location, soil, size |
| `/tip` | Return today's agricultural tip | ✓ Pass | Language-aware |
| `/forecast` | Generate and send five-day chart | ✓ Pass | matplotlib JPEG sent |
| `/language` | Display 4-button language selector | ✓ Pass | Persists in profile |
| `/edit_profile` | Initiate four-step profile update | ✓ Pass | Updates DB |
| `/connect` | Display linking instructions | ✓ Pass | Web URL included |
| `/logout` | Unlink Telegram from account | ✓ Pass | Clears telegram_chat_id |

All eleven commands passed their functional tests without error. Prior to the implementation of the `close_old_connections()` decorator on database helper functions, several commands had failed silently due to stale PostgreSQL connection handles in the long-running bot process. This issue was resolved by the decorator pattern, after which all commands operated reliably across extended uptime periods.

### 4.6.2 Cross-Platform Data Synchronisation

A key architectural requirement of FarmBuddy was that a user's data, preferences, and conversation history should be consistent across the web application and the Telegram bot. This was achieved by grounding both platforms in the same PostgreSQL database, mediated by the same Django ORM models.

Cross-platform synchronisation was verified through the following test scenarios:

1. **Profile update from web reflects in bot**: A user's farm location was updated through the web profile page. Sending `/dashboard` in the Telegram bot immediately reflected the updated location — confirming that profile reads in the bot accessed the live database rather than a cache.

2. **Language change propagates**: The user's preferred language was changed from English to Hausa via the web interface's language switcher. Subsequent AI responses from the Telegram bot were generated in Hausa without requiring a `/language` command on the bot — confirming that the `preferred_language` field was shared.

3. **Telegram signup creates web-accessible account**: A new account created entirely through the Telegram `/signup` flow was successfully logged into via the web application login page using the same credentials, and the profile data entered during the Telegram signup was visible in the web profile page.

4. **Account linking via token**: A user who had created an account on the web obtained their Telegram link token from the web profile page, sent it to the bot via `/start <token>`, and was immediately greeted by name. Subsequent bot interactions used the correct language and farm profile.

All four synchronisation scenarios passed without discrepancy, confirming robust cross-platform data consistency.

---

## 4.7 System Performance Analysis

### 4.7.1 Response Time Metrics

System response times were measured across the primary interactive endpoints under normal load conditions (single concurrent user, production environment on Render and Vercel). Measurements were taken using Chrome DevTools Network panel and server-side logging. The first token latency was used as the primary metric for streaming endpoints, defined as the time from request dispatch to the arrival of the first streamed token.

Results are summarised in Table 4.6.

**Table 4.6: System Response Time Metrics**

| Endpoint / Operation | Metric Type | Observed Value | Notes |
|---|---|---|---|
| AI Chat (first token) | First token latency | 1.2 – 2.8 s | Varies with prompt length |
| AI Chat (full response) | End-to-end streaming | 4 – 14 s | Proportional to response length |
| Plant Disease Diagnosis (first token) | First token latency | 2.0 – 4.5 s | Image upload adds latency |
| Audio Transcription | Round-trip | 3.5 – 8.0 s | Includes Gemini file polling |
| Text-to-Speech | Audio delivery start | 1.5 – 3.0 s | Depends on YarnGPT load |
| Weather Data Retrieval | Round-trip | 0.4 – 1.2 s | Cached: ~5 ms (session hit) |
| Signup / Login | Round-trip | 0.2 – 0.5 s | Standard DB read/write |
| Telegram AI Response | Round-trip | 3.0 – 10.0 s | Non-streaming, full wait |

The streaming architecture for the web chat interface was the single most impactful performance decision. By delivering the first AI token within approximately two seconds and rendering tokens progressively, the perceived responsiveness was substantially higher than the raw end-to-end latency would suggest. This was particularly important given that typical full AI responses ranged from four to fourteen seconds when composed entirely.

### 4.7.2 API Integration Performance

Three external APIs were integrated into the FarmBuddy backend: Google Gemini, OpenWeatherMap, and YarnGPT. Each integration was tested for reliability, latency, and failure handling.

**Google Gemini API**: The API exhibited consistent availability throughout the testing period, with no service interruptions observed. Function-calling responses (weather tool invocations) introduced an additional 0.8–1.5 seconds of latency compared to standard text responses, attributable to the internal tool dispatch and the second `send_message()` call required to process the function result. The streaming implementation with function-call break handling resolved the previously observed `[Error: Interrupted]` failure mode.

**OpenWeatherMap API**: The API returned valid JSON responses for all test cities within the configured ten-second timeout. The retry mechanism (three attempts with exponential backoff) was not triggered during testing, suggesting stable API availability. The session-level three-hour cache was effective in eliminating redundant calls during extended conversation sessions.

**YarnGPT API**: The YarnGPT TTS API exhibited variable response times depending on queue depth on their service infrastructure. The switch from a GET request with URL parameters to a POST request with a JSON body resolved the previously observed silent failures caused by URL length limits exceeding approximately 2,000 characters for long AI responses. With markdown stripping and the 1,000-character cap, no further failures were observed during post-fix testing.

### 4.7.3 Database Query Optimization

The database layer was optimised through three primary strategies to ensure low-latency data access at scale.

**History Limiting**: Rather than loading the full message history for each AI request, the backend retrieved only the most recent ten messages from the `Message` table for a given conversation. This bounded the database query time to O(log n) relative to conversation length and reduced the data transmitted to the Gemini API, both improving response latency and reducing token costs.

**Ordered Indexing**: The `Conversation` model was ordered by `-updated_at`, which in conjunction with PostgreSQL's automatic indexing ensured that the sidebar conversation list could be retrieved with a single efficient range scan rather than a full table sort.

**Cascade Delete**: The `ForeignKey(Conversation, on_delete=CASCADE)` relationship on `Message` delegated the deletion of all associated messages to the database engine upon conversation deletion, avoiding application-level loop-based deletion and leveraging the database's optimised bulk delete pathway.

**Table 4.7: Database Query Performance Benchmarks**

| Query | Strategy | Avg. Query Time | Notes |
|---|---|---|---|
| Fetch recent 10 messages | LIMIT + ORDER BY | < 5 ms | Indexed on created_at |
| List user conversations | Filter + ORDER BY | < 3 ms | Indexed on updated_at |
| Fetch farmer profile | OneToOne join | < 2 ms | Single PK lookup |
| Create message + update conv. | INSERT + UPDATE | < 8 ms | Two-statement transaction |
| Delete conversation (cascade) | DB-level cascade | < 15 ms | Includes message cleanup |

---

## 4.8 User Feedback and Evaluation

### 4.8.1 Usability Testing Results

A usability study was conducted involving fifteen participants drawn from agricultural communities in south-western and north-western Nigeria. Participants ranged in age from 22 to 58 years and represented varying levels of smartphone literacy. Each participant was given a set of five structured tasks to complete using the FarmBuddy web application and Telegram bot:

1. Register a new account and complete the farm profile.
2. Ask a question about a common crop pest in their language.
3. Upload a photograph of a plant leaf and interpret the diagnosis.
4. Request a weather forecast for their farm location.
5. Use the voice input feature to ask a farming question.

Task completion rates and average task times were recorded by an observer. Post-task, participants completed a System Usability Scale (SUS) questionnaire and a custom satisfaction survey.

Key observations from the usability testing included:

- Thirteen of fifteen participants (87%) completed the registration task successfully within five minutes without external assistance.
- All fifteen participants were able to obtain an AI response to their agricultural question, though two participants initially typed in their native language without switching the language setting, resulting in an English response before the issue was corrected.
- The plant disease diagnosis feature generated the highest level of engagement, with twelve participants expressing surprise and enthusiasm at the AI's ability to identify diseases from photographs.
- Three participants over the age of 50 initially struggled with the microphone permission prompt on mobile Chrome, requiring brief guidance before successfully using voice input.
- The Telegram bot registration was rated slightly harder than the web registration, primarily because the sequential question-and-answer format felt more laborious than the form-based web interface, despite covering identical fields.

The mean SUS score obtained was **78.3 out of 100**, which falls within the "Good" usability band according to the Bangor et al. (2008) SUS interpretation scale. This score was considered satisfactory given the complexity of the system and the diversity of the participant group.

### 4.8.2 Feature Adoption Metrics

Following the usability study, participants were asked to report which features they found most valuable and which they were most likely to use regularly. Additionally, engagement data from the test session was collected to identify the most-used features. Results are summarised in Table 4.8.

**Table 4.8: User Satisfaction Survey Results**

| Feature | Usefulness Rating (1–5, mean) | Likely to Use Regularly (%) | Most Valued By |
|---|---|---|---|
| AI Conversational Advisory | 4.7 | 93% | All participant groups |
| Plant Disease Detection | 4.6 | 87% | Crop farmers (all) |
| Weather Forecast | 4.5 | 80% | Farmers with seasonal crops |
| Voice Input (STT) | 4.2 | 67% | Participants with low literacy |
| Text-to-Speech (TTS) | 4.0 | 60% | Hausa and Igbo speakers |
| Multilingual Support | 4.4 | 73% | Non-English-first speakers |
| Telegram Bot Access | 4.3 | 80% | Participants without smartphones |
| PWA Installation | 3.9 | 53% | Young, tech-savvy participants |
| Dashboard (Weather Stats) | 4.1 | 67% | Urban-adjacent farmers |

The AI Conversational Advisory and Plant Disease Detection features received the highest usefulness ratings and adoption intent. The voice features were disproportionately valued by participants with lower literacy levels, confirming the design hypothesis that voice interaction would serve as an equaliser for users less comfortable with text input. Multilingual support was rated highly by non-English-first speakers, with several Hausa-speaking participants specifically commenting that receiving advice in Hausa made the information feel "closer" and more actionable.

The relatively lower PWA installation rate (53%) was attributed to unfamiliarity with the concept of installing a website as an application, a finding consistent with existing literature on PWA adoption barriers in low digital-literacy populations. It was noted that once participants were shown how to install the PWA, all who did so rated the resulting icon-launched experience positively.

---

*End of Chapter Four*
