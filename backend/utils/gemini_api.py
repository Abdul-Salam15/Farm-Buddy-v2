import os
import google.generativeai as genai
from dotenv import load_dotenv
import requests
from utils.weather_api import check_weather_for_ai

load_dotenv(override=True)

# Support both GOOGLE_API_KEY (preferred) and GEMINI_API_KEY (legacy) env var names
_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not _api_key:
    raise EnvironmentError(
        "Missing Gemini API key. Set GOOGLE_API_KEY in your .env file."
    )
genai.configure(api_key=_api_key)

# System instruction for the persona
SYSTEM_INSTRUCTION = """
You are FarmBuddy, an expert agricultural advisor for Nigerian smallholder farmers. 
Your goal is to provide accurate, practical, and easy-to-understand farming advice.
- Prioritize organic and cost-effective solutions.
- Use simple English.
- If you don't know the answer, admit it and suggest consulting a local extension agent.
"""

model = genai.GenerativeModel(
    "gemini-flash-lite-latest",
    system_instruction=SYSTEM_INSTRUCTION,
    tools=[check_weather_for_ai]
)

# Load Hugging Face API key from environment variables
# HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Hugging Face Inference API URL for N-ATLaS
# API_URL = "https://api-inference.huggingface.co/models/NCAIR1/N-ATLaS"

# Load YarnGPT API key from environment variables
YARNGPT_API_KEY = os.getenv("YARNGPT_API_KEY")

# YarnGPT API URL
YARNGPT_API_URL = "https://yarngpt.ai/api/v1/tts"

def ask_gemini(messages_history: list, weather_context=None, profile_context=None, stream=False, language='en'):
    """
    Sends the full conversation history to Gemini.
    stream: If True, returns a generator for streaming responses.
    language: Target language for the response ('en', 'ha', 'ig', 'yo').
    profile_context: Optional string containing user profile info.
    """
    # Verify input — always return a generator when stream=True to keep the caller contract
    if not messages_history:
        if stream:
            def _empty_gen():
                yield "Hello! How can I help you with farming today?"
            return _empty_gen()
        return "Hello! How can I help you with farming today?"

    # Language instruction mapping
    lang_instructions = {
        'en': "Answer in English.",
        'ha': "Answer in Hausa language (Harshen Hausa).",
        'ig': "Answer in Igbo language (Asụsụ Igbo).",
        'yo': "Answer in Yoruba language (Èdè Yorùbá)."
    }
    lang_instruction = lang_instructions.get(language, "Answer in English.")

    # Convert Streamlit roles to Gemini roles
    gemini_history = []
    
    # Process messages, limit to last 10 to improve speed
    recent_messages = messages_history[-10:] if len(messages_history) > 10 else messages_history
    
    # Process all messages except the last one
    for msg in recent_messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
    
    # Start chat
    chat = model.start_chat(history=gemini_history)
    
    # Last message
    last_message = recent_messages[-1]["content"]
    
    # Add current date to context to prevent hallucinations
    from datetime import datetime
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    
    system_context = f"Current Date: {current_date}\nIMPORTANT INSTRUCTION: {lang_instruction}"
    
    if profile_context:
        system_context += f"\nUser Profile:\n{profile_context}"
        
    if weather_context:
        system_context += f"\nWeather Info: {weather_context}"
        
    last_message = f"[System Context: {system_context}]\n\n{last_message}"
        
    try:
        response = chat.send_message(last_message, stream=stream)
        
        if stream:
            def stream_generator():
                try:
                    for chunk in response:
                        if chunk.parts and chunk.parts[0].function_call:
                            fn = chunk.parts[0].function_call
                            if fn.name == "check_weather_for_ai":
                                yield f" [Status: Gathering weather info for {fn.args.get('city_name', 'your location')}...] "
                                args = {key: val for key, val in fn.args.items()}
                                weather_result = check_weather_for_ai(**args)
                                
                                # Send result back to Gemini
                                func_response = genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=fn.name, 
                                        response={"result": weather_result}
                                    )
                                )
                                follow_up_response = chat.send_message(func_response, stream=True)
                                for text_chunk in follow_up_response:
                                    if text_chunk.text:
                                        yield text_chunk.text
                        elif chunk.text:
                            yield chunk.text
                except Exception as e:
                    print(f"Error during streaming: {e}")
                    yield " [Error: Interrupted] "
            return stream_generator()
        else:
            if response.parts and response.parts[0].function_call:
                fn = response.parts[0].function_call
                if fn.name == "check_weather_for_ai":
                    args = {key: val for key, val in fn.args.items()}
                    weather_result = check_weather_for_ai(**args)
                    func_response = genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fn.name, 
                            response={"result": weather_result}
                        )
                    )
                    follow_up_response = chat.send_message(func_response, stream=False)
                    return follow_up_response.text
            return response.text
    except Exception as e:
        error_msg = str(e)
        if stream:
            def error_gen(): yield f"An error occurred: {error_msg}"
            return error_gen()
        return f"An error occurred: {error_msg}"


def analyze_plant_image(image_path, system_context=None, stream=False):
    """
    Analyze a plant image for disease detection using Gemini Vision
    image_path: Path to the uploaded plant image
    system_context: Optional string containing user profile and history info
    stream: If True, returns a generator
    """
    from PIL import Image
    
    try:
        # Load the image
        img = Image.open(image_path)
        
        # Create prompt for plant disease analysis
        base_prompt = """Analyze this plant leaf image and provide:
1. **Disease Identification**: What disease or problem do you see? (if any)
2. **Confidence Level**: How confident are you in this diagnosis?
3. **Internal Detection (XAI Properties)**: Provide specific bounding box coordinates [ymin, xmin, ymax, xmax] for the areas where you see symptoms. If multiple spots exist, list the most prominent ones.
4. **Symptoms Observed**: Describe the visible symptoms
5. **Recommended Treatment**: Practical, cost-effective solutions for Nigerian smallholder farmers
6. **Prevention Tips**: How to prevent this in the future

Use simple English and be practical. If you cannot identify a specific disease, explain what you observe and suggest consulting a local agricultural extension agent."""

        if system_context:
            prompt = f"{system_context}\n\n[TASK]: {base_prompt}"
        else:
            prompt = base_prompt

        response = model.generate_content([prompt, img], stream=stream)
        
        if stream:
            def stream_generator():
                try:
                    for chunk in response:
                        if chunk.text:
                            yield chunk.text
                except Exception as e:
                    print(f"Error during vision streaming: {e}")
                    yield " [Error: Interrupted] "
            return stream_generator()
        else:
            return response.text.strip()
        
    except Exception as e:
        if stream:
            def error_gen(): yield f"Error analyzing image: {str(e)}"
            return error_gen()
        return f"Error analyzing image: {str(e)}"


def summarize_title(text):
    """
    Generate a short 5-word summary title for a conversation based on the first prompt
    """
    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        # Use simple model for summarization
        prompt = f"Summarize the following text into a short title of maximum 5 words. Do not use quotes or special characters. Text: {text}"
        response = model.generate_content(prompt)
        return response.text.strip().replace('"', '').replace('*', '')
    except Exception as e:
        print(f"Error generating title: {str(e)}")
        # Fallback to truncation if AI fails
        return text[:30] + "..." if len(text) > 30 else text

# Function to generate speech using YarnGPT
def text_to_speech(text, voice="Idera"):
    API_URL = "https://yarngpt.ai/api/v1/tts"
    headers = {
        "Authorization": f"Bearer {YARNGPT_API_KEY}"
    }
    payload = {
        "text": text,
        "voice": voice
    }

    response = requests.post(API_URL, headers=headers, json=payload, stream=True)

    if response.status_code == 200:
        with open("output.mp3", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Audio file saved as output.mp3")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())

# Function to transcribe speech using YarnGPT
def speech_to_text(audio_file, language="en"):
    headers = {
        "Authorization": f"Bearer {YARNGPT_API_KEY}",
    }
    with open(audio_file, "rb") as f:
        files = {"file": f}
        response = requests.post(f"{YARNGPT_API_URL}/stt", headers=headers, files=files, params={"language": language})
    if response.status_code == 200:
        print("Transcription:", response.json()["text"])
    else:
        print("Error:", response.json())

