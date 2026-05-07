import os
import io
import requests
import logging
from dotenv import load_dotenv
from utils.weather_api import check_weather_for_ai

load_dotenv(override=True)

from google import genai
from google.genai import types
try:
    from google.genai import errors as genai_errors
except ImportError:
    genai_errors = None

logger = logging.getLogger(__name__)

_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not _api_key:
    raise EnvironmentError(
        "Missing Gemini API key. Set GOOGLE_API_KEY in your .env file."
    )

client = genai.Client(api_key=_api_key)

SYSTEM_INSTRUCTION = """
You are FarmBuddy, an expert agricultural advisor for Nigerian smallholder farmers.
Your goal is to provide accurate, practical, and easy-to-understand farming advice.
- Prioritize organic and cost-effective solutions.
- Use simple English.
- If you don't know the answer, admit it and suggest consulting a local extension agent.
"""

_CHAT_MODEL = "gemini-1.5-flash"
_VISION_MODEL = "gemini-1.5-flash"


def _is_quota_error(e: Exception) -> bool:
    # Check by exception type first (most reliable)
    if genai_errors:
        if isinstance(e, genai_errors.ClientError):
            code = getattr(e, 'code', None) or getattr(e, 'status_code', None)
            if code in (429, 503):
                return True
    # Fallback: string scan (case-insensitive)
    msg = str(e).lower()
    return any(s in msg for s in (
        "429", "resource_exhausted", "quota", "rate_limit", "ratelimit",
        "generaterequests", "too many requests", "retry_delay", "exhausted",
    ))


def _friendly_error(e: Exception) -> str:
    logger.error("Gemini error [%s]: %s", type(e).__name__, e)
    if _is_quota_error(e):
        return "FarmBuddy is currently busy due to high demand. Please wait a moment and try again."
    msg = str(e).lower()
    if "invalid_argument" in msg or ("400" in msg and "quota" not in msg):
        return "I couldn't process that request. Please try rephrasing your message."
    if "401" in msg or "403" in msg or "api_key" in msg:
        return "There's a configuration issue on our end. Please contact support."
    if "503" in msg or "unavailable" in msg:
        return "The AI service is temporarily unavailable. Please try again shortly."
    return "Something went wrong on my end. Please try again."

# Explicit tool declaration for weather function calling
_weather_tool = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="check_weather_for_ai",
        description="Get current weather conditions and 5-day forecast for a Nigerian city",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "city_name": types.Schema(
                    type="STRING",
                    description="Name of the city or town"
                )
            },
            required=["city_name"]
        )
    )
])

YARNGPT_API_KEY = os.getenv("YARNGPT_API_KEY")
YARNGPT_API_URL = "https://yarngpt.ai/api/v1/tts"


def _build_history(messages: list) -> list:
    history = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append(types.Content(
            role=role,
            parts=[types.Part(text=msg["content"])]
        ))
    return history


def ask_gemini(messages_history: list, weather_context=None, profile_context=None, stream=False, language='en'):
    """Send conversation history to Gemini and return a text response or generator."""
    if not messages_history:
        if stream:
            def _empty():
                yield "Hello! How can I help you with farming today?"
            return _empty()
        return "Hello! How can I help you with farming today?"

    lang_instructions = {
        'en': "Answer in English.",
        'ha': "Answer in Hausa language (Harshen Hausa).",
        'ig': "Answer in Igbo language (Asụsụ Igbo).",
        'yo': "Answer in Yoruba language (Èdè Yorùbá)."
    }
    lang_instruction = lang_instructions.get(language, "Answer in English.")

    recent = messages_history[-10:]
    history = _build_history(recent[:-1])

    from datetime import datetime
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    system_context = f"Current Date: {current_date}\nIMPORTANT INSTRUCTION: {lang_instruction}"
    if profile_context:
        system_context += f"\nUser Profile:\n{profile_context}"
    if weather_context:
        system_context += f"\nWeather Info: {weather_context}"

    last_message = f"[System Context: {system_context}]\n\n{recent[-1]['content']}"

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[_weather_tool],
    )

    try:
        chat = client.chats.create(model=_CHAT_MODEL, history=history, config=config)

        if stream:
            def stream_generator():
                try:
                    fn_call = None
                    for chunk in chat.send_message_stream(last_message):
                        if chunk.function_calls:
                            fn_call = chunk.function_calls[0]
                            if fn_call.name == "check_weather_for_ai":
                                city = fn_call.args.get('city_name', 'your location')
                                yield f"[Status: Gathering weather info for {city}...]\n\n"
                            break
                        elif chunk.text:
                            yield chunk.text

                    if fn_call and fn_call.name == "check_weather_for_ai":
                        weather_result = check_weather_for_ai(**dict(fn_call.args))
                        func_part = types.Part(
                            function_response=types.FunctionResponse(
                                name=fn_call.name,
                                response={"result": weather_result}
                            )
                        )
                        for text_chunk in chat.send_message_stream(func_part):
                            if text_chunk.text:
                                yield text_chunk.text
                except Exception as e:
                    print(f"Error during streaming: {e}")
                    yield f"\n{_friendly_error(e)}"
            return stream_generator()
        else:
            response = chat.send_message(last_message)
            if response.function_calls:
                fn = response.function_calls[0]
                if fn.name == "check_weather_for_ai":
                    weather_result = check_weather_for_ai(**dict(fn.args))
                    func_part = types.Part(
                        function_response=types.FunctionResponse(
                            name=fn.name,
                            response={"result": weather_result}
                        )
                    )
                    return chat.send_message(func_part).text
            return response.text
    except Exception as e:
        print(f"ask_gemini error: {e}")
        msg = _friendly_error(e)
        if stream:
            def _err():
                yield msg
            return _err()
        return msg


def analyze_plant_image(image_path, system_context=None, stream=False):
    """Analyze a plant leaf image for disease detection using Gemini Vision."""
    from PIL import Image
    try:
        img = Image.open(image_path)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        image_part = types.Part(
            inline_data=types.Blob(data=buf.getvalue(), mime_type='image/jpeg')
        )

        base_prompt = """Analyze this plant leaf image and provide:
1. **Disease Identification**: What disease or problem do you see? (if any)
2. **Confidence Level**: How confident are you in this diagnosis?
3. **Internal Detection (XAI Properties)**: Provide specific bounding box coordinates [ymin, xmin, ymax, xmax] for the areas where you see symptoms. If multiple spots exist, list the most prominent ones.
4. **Symptoms Observed**: Describe the visible symptoms
5. **Recommended Treatment**: Practical, cost-effective solutions for Nigerian smallholder farmers
6. **Prevention Tips**: How to prevent this in the future

Use simple English and be practical. If you cannot identify a specific disease, explain what you observe and suggest consulting a local agricultural extension agent."""

        prompt = f"{system_context}\n\n[TASK]: {base_prompt}" if system_context else base_prompt

        if stream:
            def stream_generator():
                try:
                    for chunk in client.models.generate_content_stream(
                        model=_VISION_MODEL,
                        contents=[prompt, image_part]
                    ):
                        if chunk.text:
                            yield chunk.text
                except Exception as e:
                    print(f"Error during vision streaming: {e}")
                    yield f" {_friendly_error(e)}"
            return stream_generator()
        else:
            response = client.models.generate_content(
                model=_VISION_MODEL,
                contents=[prompt, image_part]
            )
            return response.text.strip()
    except Exception as e:
        print(f"analyze_plant_image error: {e}")
        msg = _friendly_error(e)
        if stream:
            def _err():
                yield msg
            return _err()
        return msg


def summarize_title(text: str) -> str:
    """Generate a short 5-word summary title for a conversation."""
    try:
        response = client.models.generate_content(
            model=_CHAT_MODEL,
            contents=f"Summarize the following text into a short title of maximum 5 words. Do not use quotes or special characters. Text: {text}"
        )
        return response.text.strip().replace('"', '').replace('*', '')
    except Exception as e:
        print(f"Error generating title: {e}")
        return text[:30] + "..." if len(text) > 30 else text


def transcribe_audio_file(file_path: str, mime_type: str, language: str = "en") -> str:
    """Upload an audio file to Gemini Files API and return the transcription text."""
    import time
    file_ref = client.files.upload(
        path=file_path,
        config=types.UploadFileConfig(mime_type=mime_type, display_name="audio")
    )
    max_wait = 30
    waited = 0
    while file_ref.state.name == "PROCESSING" and waited < max_wait:
        time.sleep(1)
        waited += 1
        file_ref = client.files.get(name=file_ref.name)

    if file_ref.state.name != "ACTIVE":
        raise Exception(f"File {file_ref.name} is not ACTIVE (state: {file_ref.state.name})")

    language_names = {'en': 'English', 'ha': 'Hausa', 'ig': 'Igbo', 'yo': 'Yoruba'}
    lang_name = language_names.get(language, 'English')
    prompt = (
        f"Transcribe this audio exactly as spoken. "
        f"The language is {lang_name}. "
        "Return ONLY the transcription text, nothing else."
    )

    response = client.models.generate_content(
        model=_VISION_MODEL,
        contents=[
            types.Content(parts=[
                types.Part(file_data=types.FileData(
                    file_uri=file_ref.uri,
                    mime_type=file_ref.mime_type
                )),
                types.Part(text=prompt)
            ])
        ]
    )
    try:
        client.files.delete(name=file_ref.name)
    except Exception:
        pass
    return response.text.strip()


def respond_to_voice(file_path: str, mime_type: str, language: str = "en") -> str:
    """Upload a voice note and ask Gemini to both understand and respond (used by Telegram bot)."""
    import time
    file_ref = client.files.upload(
        path=file_path,
        config=types.UploadFileConfig(mime_type=mime_type, display_name="voice_note")
    )
    max_wait = 30
    waited = 0
    while file_ref.state.name == "PROCESSING" and waited < max_wait:
        time.sleep(1)
        waited += 1
        file_ref = client.files.get(name=file_ref.name)

    if file_ref.state.name != "ACTIVE":
        raise Exception(f"Voice file is not ACTIVE (state: {file_ref.state.name})")

    prompt = (
        f"Listen to this audio and respond helpfully in {language} language. "
        "Personalize your response for a Nigerian smallholder farmer."
    )

    response = client.models.generate_content(
        model=_VISION_MODEL,
        contents=[
            types.Content(parts=[
                types.Part(file_data=types.FileData(
                    file_uri=file_ref.uri,
                    mime_type=file_ref.mime_type
                )),
                types.Part(text=prompt)
            ])
        ]
    )
    try:
        client.files.delete(name=file_ref.name)
    except Exception:
        pass
    return response.text.strip()


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
