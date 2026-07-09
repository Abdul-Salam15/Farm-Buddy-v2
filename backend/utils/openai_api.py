import os
import io
import json
import base64
import requests
import logging
from dotenv import load_dotenv
from utils.weather_api import check_weather_for_ai

load_dotenv(override=True)

from openai import OpenAI, APIStatusError

logger = logging.getLogger(__name__)

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise EnvironmentError("Missing OpenAI API key. Set OPENAI_API_KEY in your .env file.")

client = OpenAI(api_key=_api_key)

SYSTEM_INSTRUCTION = """
You are FarmBuddy, a friendly and knowledgeable agricultural advisor for Nigerian smallholder farmers.
Your goal is to provide accurate, practical, and easy-to-understand farming advice.

When a user greets you or makes small talk (e.g. "good morning", "how are you", "hello"), respond warmly and naturally, then offer to help with their farming needs.

For farming questions:
- Prioritize organic and cost-effective solutions.
- Use simple, jargon-free language.
- If you don't know the answer, admit it and suggest consulting a local agricultural extension agent.

Always be friendly, encouraging, and culturally sensitive to Nigerian farmers.
"""

_CHAT_MODEL = "gpt-4o-mini"
_VISION_MODEL = "gpt-4o"

_weather_tool = [
    {
        "type": "function",
        "function": {
            "name": "check_weather_for_ai",
            "description": "Get current weather conditions and 5-day forecast for a Nigerian city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "Name of the city or town"
                    }
                },
                "required": ["city_name"]
            }
        }
    }
]

YARNGPT_API_KEY = os.getenv("YARNGPT_API_KEY")
YARNGPT_API_URL = "https://yarngpt.ai/api/v1/tts"


def _friendly_error(e: Exception) -> str:
    logger.error("OpenAI error [%s]: %s", type(e).__name__, e)
    if isinstance(e, APIStatusError):
        if e.status_code == 429:
            return "FarmBuddy is currently busy due to high demand. Please wait a moment and try again."
        if e.status_code in (401, 403):
            return "There's a configuration issue on our end. Please contact support."
        if e.status_code == 400:
            return "I couldn't process that request. Please try rephrasing your message."
        if e.status_code >= 500:
            return "The AI service is temporarily unavailable. Please try again shortly."
    # Fallback string scan for anything not an APIStatusError
    msg = str(e).lower()
    if any(s in msg for s in ("429", "rate_limit", "quota", "too many requests")):
        return "FarmBuddy is currently busy due to high demand. Please wait a moment and try again."
    return "Something went wrong on my end. Please try again."


LANG_INSTRUCTIONS = {
    'en': "Write your reply in English.",
    'ha': "Write your reply in the Hausa language (Harshen Hausa).",
    'ig': "Write your reply in the Igbo language (Asụsụ Igbo).",
    'yo': "Write your reply in the Yoruba language (Èdè Yorùbá).",
}

# Explains that the language requirement covers prose only, not the
# machine-parsed [FARMBUDDY_REFS] tokens — without this carve-out, models
# can read "every sentence must be in the target language" as conflicting
# with "you MUST use these exact English tag names" and refuse to answer.
REF_BLOCK_LANGUAGE_NOTE = (
    "This covers all prose: your main answer and the explanation text after "
    "each em-dash in the [FARMBUDDY_REFS] block. The block's structural "
    "keywords (FARMBUDDY_REFS, PROFILE, HISTORY, WEATHER, KNOWLEDGE, IMAGE, "
    "and field keys like current_crops) are fixed protocol tokens — always "
    "keep those in English exactly as shown."
)


def _build_messages(messages_history: list, lang_instruction: str, system_extra: str = "", profile_context: str = "") -> list:
    # The language directive is stated first (primacy) and echoed briefly at
    # the end (recency) so it isn't diluted by the profile/formatting
    # instructions in between.
    system = f"{lang_instruction} {REF_BLOCK_LANGUAGE_NOTE}\n\n{SYSTEM_INSTRUCTION.strip()}"
    if profile_context:
        system += f"\n\n{profile_context}"
    if system_extra:
        system += f"\n\n{system_extra}"
    system += f"\n\n({lang_instruction})"
    result = [{"role": "system", "content": system}]
    for msg in messages_history:
        role = "user" if msg["role"] == "user" else "assistant"
        result.append({"role": role, "content": msg["content"]})
    return result


def ask_openai(messages_history: list, weather_context=None, profile_context=None, stream=False, language='en'):
    """Send conversation history to OpenAI and return a text response or generator."""
    if not messages_history:
        if stream:
            def _empty():
                yield "Hello! How can I help you with farming today?"
            return _empty()
        return "Hello! How can I help you with farming today?"

    lang_instruction = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS['en'])

    from datetime import datetime
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    system_extra = f"Current Date: {current_date}"
    if weather_context:
        system_extra += f"\nWeather Info: {weather_context}"

    recent = messages_history[-10:]
    messages = _build_messages(recent, lang_instruction, system_extra, profile_context=profile_context or "")

    try:
        if stream:
            def stream_generator():
                try:
                    response = client.chat.completions.create(
                        model=_CHAT_MODEL,
                        messages=messages,
                        tools=_weather_tool,
                        stream=True,
                    )

                    # Accumulate tool calls while streaming content
                    tool_calls_acc = {}
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                i = tc.index
                                if i not in tool_calls_acc:
                                    tool_calls_acc[i] = {"id": "", "name": "", "arguments": ""}
                                if tc.id:
                                    tool_calls_acc[i]["id"] += tc.id
                                if tc.function:
                                    if tc.function.name:
                                        tool_calls_acc[i]["name"] += tc.function.name
                                    if tc.function.arguments:
                                        tool_calls_acc[i]["arguments"] += tc.function.arguments
                        elif delta.content:
                            yield delta.content

                    # Resolve any tool calls and stream follow-up
                    for tc in tool_calls_acc.values():
                        if tc["name"] == "check_weather_for_ai":
                            args = json.loads(tc["arguments"])
                            city = args.get("city_name", "your location")
                            yield f"[Status: Gathering weather info for {city}...]\n\n"
                            weather_result = check_weather_for_ai(**args)
                            follow_up = messages + [
                                {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [{"id": tc["id"], "type": "function",
                                                    "function": {"name": tc["name"], "arguments": tc["arguments"]}}]
                                },
                                {
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": json.dumps({"result": weather_result})
                                }
                            ]
                            for chunk in client.chat.completions.create(
                                model=_CHAT_MODEL, messages=follow_up, stream=True
                            ):
                                if chunk.choices and chunk.choices[0].delta.content:
                                    yield chunk.choices[0].delta.content

                except Exception as e:
                    logger.error("Streaming error: %s", e)
                    yield f"\n{_friendly_error(e)}"

            return stream_generator()

        else:
            response = client.chat.completions.create(
                model=_CHAT_MODEL,
                messages=messages,
                tools=_weather_tool,
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                tc = msg.tool_calls[0]
                if tc.function.name == "check_weather_for_ai":
                    args = json.loads(tc.function.arguments)
                    weather_result = check_weather_for_ai(**args)
                    follow_up = messages + [
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{"id": tc.id, "type": "function",
                                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}}]
                        },
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps({"result": weather_result})
                        }
                    ]
                    follow_up_resp = client.chat.completions.create(
                        model=_CHAT_MODEL, messages=follow_up
                    )
                    return follow_up_resp.choices[0].message.content

            return msg.content

    except Exception as e:
        logger.error("ask_openai error: %s", e)
        err = _friendly_error(e)
        if stream:
            def _err():
                yield err
            return _err()
        return err


def analyze_plant_image(image_path, system_context=None, stream=False, language='en'):
    """Analyze a plant leaf image for disease detection using GPT-4o vision."""
    from PIL import Image
    try:
        img = Image.open(image_path)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        image_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        lang_instruction = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS['en'])

        base_prompt = f"""{lang_instruction} {REF_BLOCK_LANGUAGE_NOTE}

Analyze this plant leaf image and provide:
1. **Disease Identification**: What disease or problem do you see? (if any)
2. **Confidence Level**: How confident are you in this diagnosis?
3. **Internal Detection (XAI Properties)**: Provide specific bounding box coordinates [ymin, xmin, ymax, xmax] for the areas where you see symptoms. If multiple spots exist, list the most prominent ones.
4. **Symptoms Observed**: Describe the visible symptoms
5. **Recommended Treatment**: Practical, cost-effective solutions for Nigerian smallholder farmers
6. **Prevention Tips**: How to prevent this in the future

Be practical and simple. If you cannot identify a specific disease, explain what you observe and suggest consulting a local agricultural extension agent.

You MUST end your response with a [FARMBUDDY_REFS] ... [/FARMBUDDY_REFS] block
citing every source you used, using the exact format "TYPE:KEY — explanation"
(em-dash). Valid types:
- IMAGE:uploaded_photo — always include this one.
- PROFILE:<field_key> — for any profile fields (soil_type, location,
  current_crops, etc.) that informed your recommendations.
- WEATHER:OpenWeatherMap — if weather info was provided and used.
- KNOWLEDGE:general — fallback for general agricultural knowledge.

Example:

[FARMBUDDY_REFS]
- IMAGE:uploaded_photo — Visible yellow halos on the leaf indicate early blight.
- PROFILE:current_crops — Tailored the treatment to your tomato crop.
- KNOWLEDGE:general — Standard organic fungicide recommendations.
[/FARMBUDDY_REFS]

({lang_instruction})"""

        prompt = f"{system_context}\n\n[TASK]: {base_prompt}" if system_context else base_prompt

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }
        ]

        if stream:
            def stream_generator():
                try:
                    response = client.chat.completions.create(
                        model=_VISION_MODEL,
                        messages=messages,
                        stream=True,
                    )
                    for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                except Exception as e:
                    logger.error("Vision streaming error: %s", e)
                    yield f" {_friendly_error(e)}"
            return stream_generator()
        else:
            response = client.chat.completions.create(
                model=_VISION_MODEL,
                messages=messages,
            )
            return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error("analyze_plant_image error: %s", e)
        err = _friendly_error(e)
        if stream:
            def _err():
                yield err
            return _err()
        return err


def summarize_title(text: str) -> str:
    """Generate a short 5-word summary title for a conversation."""
    try:
        response = client.chat.completions.create(
            model=_CHAT_MODEL,
            messages=[
                {"role": "user", "content": (
                    "Summarize the following text into a short title of maximum 5 words. "
                    "Do not use quotes or special characters. "
                    f"Text: {text}"
                )}
            ],
        )
        return response.choices[0].message.content.strip().replace('"', '').replace('*', '')
    except Exception as e:
        logger.error("summarize_title error: %s", e)
        return text[:30] + "..." if len(text) > 30 else text


def transcribe_audio_file(file_path: str, mime_type: str, language: str = "en") -> str:
    """Transcribe an audio file using OpenAI Whisper."""
    # Whisper uses ISO 639-1 codes; pass None for non-English to let it auto-detect
    lang_code = language if language == "en" else None
    with open(file_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language=lang_code,
        )
    return response.text.strip()


def respond_to_voice(file_path: str, mime_type: str, language: str = "en") -> str:
    """Transcribe a voice note then generate a farming response (used by Telegram bot)."""
    transcription = transcribe_audio_file(file_path, mime_type, language)

    lang_instruction = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS['en'])

    response = client.chat.completions.create(
        model=_CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_INSTRUCTION.strip() + f"\n\n{lang_instruction}\nPersonalize your response for a Nigerian smallholder farmer."
            },
            {"role": "user", "content": transcription}
        ],
    )
    return response.choices[0].message.content.strip()


def text_to_speech(text, voice="Idera"):
    headers = {"Authorization": f"Bearer {YARNGPT_API_KEY}"}
    response = requests.post(
        YARNGPT_API_URL,
        headers=headers,
        json={"text": text, "voice": voice},
        stream=True
    )
    if response.status_code == 200:
        with open("output.mp3", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        print(f"TTS Error {response.status_code}:", response.json())
