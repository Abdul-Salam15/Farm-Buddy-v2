from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.gemini_api import ask_gemini, analyze_plant_image
from .context_builder import build_system_prompt, parse_xai_refs
from utils.weather_api import get_weather, get_forecast, get_weather_by_city, get_forecast_by_city, format_weather_for_ai, format_forecast_for_ai

from .models import Conversation, Message


def index(request, conversation_id=None):
    """Main chat interface"""
    if conversation_id:
        try:
            # Only allow access to conversations owned by the current user
            if request.user.is_authenticated:
                current_conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            else:
                current_conversation = Conversation.objects.get(id=conversation_id, user__isnull=True)
            request.session['conversation_id'] = current_conversation.id
        except Conversation.DoesNotExist:
            return redirect('index')
    else:
        if request.user.is_authenticated:
            # Get or create a conversation owned by this user
            user_conv = Conversation.objects.filter(user=request.user).order_by('-updated_at').first()
            if user_conv:
                current_conversation = user_conv
                request.session['conversation_id'] = current_conversation.id
            else:
                current_conversation = Conversation.objects.create(user=request.user)
                request.session['conversation_id'] = current_conversation.id
        else:
            # Unauthenticated users get their own session-scoped conversations
            session_conv_id = request.session.get('conversation_id')
            if session_conv_id:
                try:
                    current_conversation = Conversation.objects.get(id=session_conv_id, user__isnull=True)
                except Conversation.DoesNotExist:
                    current_conversation = Conversation.objects.create()
                    request.session['conversation_id'] = current_conversation.id
            else:
                current_conversation = Conversation.objects.create()
                request.session['conversation_id'] = current_conversation.id

    # Get messages for current conversation
    chat_messages = current_conversation.messages.all()

    # Get conversations for sidebar — strictly filtered to the current user
    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(user=request.user).order_by('-updated_at')[:20]
    else:
        # Unauthenticated users only see the conversation in their current session
        conversations = Conversation.objects.filter(id=current_conversation.id)

    # Determine language for UI rendering
    lang = 'en'
    if request.user.is_authenticated:
        try:
            from accounts.models import FarmerProfile
            lang = FarmerProfile.objects.get(user=request.user).preferred_language
        except Exception:
            lang = 'en'

    context = {
        'current_conversation': current_conversation,
        'chat_messages': chat_messages,
        'conversations': conversations,
        'lang': lang,
        'user_lang': lang,
    }
    return render(request, 'chat/index.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """Handle sending a message and getting AI response"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        language = data.get('language', 'en')
        if language not in ['en', 'ha', 'ig', 'yo']:
            language = 'en'
        conversation_id = data.get('conversation_id') # Explicit ID support
        
        if not user_message:
            return JsonResponse({'success': False, 'error': 'Empty message'})
        
        # Get current conversation — enforce ownership
        if not conversation_id:
            conversation_id = request.session.get('conversation_id')

        try:
            if request.user.is_authenticated:
                if conversation_id:
                    conversation = Conversation.objects.get(id=conversation_id, user=request.user)
                else:
                    conversation = Conversation.objects.filter(user=request.user).order_by('-updated_at').first()
                    if not conversation:
                        conversation = Conversation.objects.create(user=request.user)
            else:
                if conversation_id:
                    conversation = Conversation.objects.get(id=conversation_id, user__isnull=True)
                else:
                    conversation = Conversation.objects.create()
            
            request.session['conversation_id'] = conversation.id
        except Conversation.DoesNotExist:
            if request.user.is_authenticated:
                conversation = Conversation.objects.create(user=request.user)
            else:
                conversation = Conversation.objects.create()
            request.session['conversation_id'] = conversation.id
        
        # Save user message
        Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_message
        )
        
        # Fetch only the last 10 messages at the DB layer to avoid loading full history
        recent_qs = conversation.messages.order_by('-created_at')[:10]
        messages_history = list(reversed(list(recent_qs.values('role', 'content'))))
        
        # Generator for streaming response
        def response_generator():
            full_response = ""
            try:
                try:
                    system_prompt = build_system_prompt(request.user) if request.user.is_authenticated else ""
                except Exception:
                    system_prompt = ''

                # Expire weather context after 3 hours (10800 seconds)
                import time as _time
                weather_context = request.session.get('weather_context') or ''
                weather_ts = request.session.get('weather_context_ts', 0)
                if weather_context and (_time.time() - weather_ts) > 10800:
                    weather_context = ''
                    request.session.pop('weather_context', None)
                    request.session.pop('weather_context_ts', None)
                combined_context = system_prompt + "\n\n" + weather_context if system_prompt else weather_context

                stream = ask_gemini(messages_history, weather_context=combined_context, stream=True, language=language)
                
                for chunk in stream:
                    full_response += chunk
                    yield json.dumps({'chunk': chunk}) + "\n"
                
                try:
                    clean_text, refs = parse_xai_refs(full_response)
                except Exception:
                    clean_text, refs = full_response, []

                Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=clean_text,
                    references=refs
                )
                
                yield json.dumps({'success': True, 'full_text': full_response, 'references': refs, 'conversation_id': conversation.id}) + "\n"
                
                if conversation.messages.count() == 2 and (not conversation.title or conversation.title == "New Chat"):
                     def update_title_background(conv_id, text):
                        try:
                            from utils.gemini_api import summarize_title
                            c = Conversation.objects.get(id=conv_id)
                            c.title = summarize_title(text)
                            c.save()
                        except Exception as e:
                            print(f"Error updating title: {e}")

                     import threading
                     thread = threading.Thread(target=update_title_background, args=(conversation.id, user_message))
                     thread.daemon = True
                     thread.start()

            except Exception as e:
                print(f"Stream Error: {e}")
                yield json.dumps({'error': str(e)}) + "\n"

        return StreamingHttpResponse(response_generator(), content_type='application/x-ndjson')
        
    except Exception as e:
        print(f"Error in send_message: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def new_conversation(request):
    """Create a new conversation"""
    try:
        if request.user.is_authenticated:
            conversation = Conversation.objects.create(user=request.user)
        else:
            conversation = Conversation.objects.create()
        request.session['conversation_id'] = conversation.id
        return JsonResponse({'success': True, 'conversation_id': conversation.id, 'title': conversation.title})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_GET
def api_conversation_history(request, conversation_id):
    """Return JSON history for a conversation"""
    try:
        if request.user.is_authenticated:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        else:
            session_conv_id = request.session.get('conversation_id')
            if conversation_id != session_conv_id:
                return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            conversation = get_object_or_404(Conversation, id=conversation_id, user__isnull=True)

        messages = conversation.messages.all().order_by('created_at')
        message_list = []
        for m in messages:
            msg_data = {
                'id': m.id,
                'role': m.role,
                'content': m.content,
                'created_at': m.created_at.isoformat(),
                'references': m.references,
            }
            if m.image:
                msg_data['image_url'] = m.image.url
            message_list.append(msg_data)
            
        return JsonResponse({
            'success': True, 
            'conversation': {
                'id': conversation.id,
                'title': conversation.title,
                'updated_at': conversation.updated_at.isoformat()
            },
            'messages': message_list
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_GET
def api_list_conversations(request):
    """List conversations for the current user/session"""
    try:
        if request.user.is_authenticated:
            conversations = Conversation.objects.filter(user=request.user).order_by('-updated_at')
        else:
            # For anonymous users, we rely on the session ID
            conv_id = request.session.get('conversation_id')
            if conv_id:
                conversations = Conversation.objects.filter(id=conv_id, user__isnull=True)
            else:
                conversations = []
                
        data = [{
            'id': c.id,
            'title': c.title,
            'updated_at': c.updated_at.isoformat()
        } for c in conversations]
        
        return JsonResponse({'success': True, 'conversations': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_image(request):
    """Handle plant image upload and analysis"""
    try:
        from utils.gemini_api import analyze_plant_image
        from utils.image_processing import validate_image
        from django.core.files.storage import default_storage
        
        if 'image' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No image provided'}, status=400)
        
        image_file = request.FILES['image']
        
        if image_file.size > 5 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'Image exceeds 5MB limit.'}, status=400)
        
        # Validate image
        is_valid, error_msg = validate_image(image_file)
        if not is_valid:
            return JsonResponse({'success': False, 'error': error_msg}, status=400)

        # Compress image before storing (resize to ≤1024×1024, JPEG quality 85)
        from utils.image_processing import compress_image
        from django.core.files.uploadedfile import InMemoryUploadedFile
        try:
            compressed = compress_image(image_file)
            image_file = InMemoryUploadedFile(
                compressed, 'image', 'plant.jpg', 'image/jpeg', compressed.getbuffer().nbytes, None
            )
        except Exception:
            # If compression fails, fall through with the original file
            image_file.seek(0)
        
        # Get current conversation — enforce ownership
        conversation_id = request.POST.get('conversation_id') or request.session.get('conversation_id')
        try:
            if request.user.is_authenticated:
                if conversation_id:
                    conversation = Conversation.objects.get(id=conversation_id, user=request.user)
                else:
                    conversation = Conversation.objects.filter(user=request.user).order_by('-updated_at').first()
                    if not conversation:
                        conversation = Conversation.objects.create(user=request.user)
            else:
                if conversation_id:
                    conversation = Conversation.objects.get(id=conversation_id, user__isnull=True)
                else:
                    # Check if session has a conversation that is anonymous
                    session_conv_id = request.session.get('conversation_id')
                    if session_conv_id:
                        try:
                            conversation = Conversation.objects.get(id=session_conv_id, user__isnull=True)
                        except Conversation.DoesNotExist:
                            conversation = Conversation.objects.create()
                    else:
                        conversation = Conversation.objects.create()
        except Conversation.DoesNotExist:
            if request.user.is_authenticated:
                conversation = Conversation.objects.create(user=request.user)
            else:
                conversation = Conversation.objects.create()
            request.session['conversation_id'] = conversation.id

        # Get optional text caption
        text_content = request.POST.get('message', '').strip()
        if not text_content:
            text_content = '[Plant image uploaded for analysis]'
            
        # Save user message with image
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            content=text_content,
            image=image_file
        )
            # Get the saved image path
        image_path = user_message.image.path
        
        from django.http import StreamingHttpResponse

        # Build context for vision analysis
        system_prompt = build_system_prompt(request.user if request.user.is_authenticated else None)
        weather_context = request.session.get('weather_context') or ''
        combined_context = f"{system_prompt}\n\n[WEATHER INFO]: {weather_context}" if system_prompt else weather_context

        # Save AI response placeholder and then yield chunks
        def vision_response_generator():
            full_response = ""
            try:
                # Analyze image with Gemini Vision in streaming mode
                stream = analyze_plant_image(image_path, system_context=combined_context, stream=True)
                
                for chunk in stream:
                    full_response += chunk
                    yield json.dumps({'chunk': chunk}) + "\n"
                
                # Parse references from the final response
                try:
                    clean_text, refs = parse_xai_refs(full_response)
                except Exception:
                    clean_text, refs = full_response, []

                # Save AI response to DB
                Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=clean_text,
                    references=refs
                )
                
                # Signal completion with references
                yield json.dumps({
                    'success': True, 
                    'full_text': clean_text, 
                    'references': refs,
                    'image_url': user_message.image.url
                }) + "\n"
                
                if conversation.messages.count() == 2:
                    conversation.title = "Plant Disease Analysis"
                    conversation.save()

            except Exception as e:
                print(f"Error in vision stream: {e}")
                yield json.dumps({'success': False, 'error': str(e)}) + "\n"

        return StreamingHttpResponse(vision_response_generator(), content_type='application/x-ndjson')
        
    except Exception as e:
        print(f"Error in upload_image: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def rename_conversation(request, conversation_id):
    """Rename a conversation — only the owning user may rename it"""
    try:
        if request.user.is_authenticated:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        else:
            conversation = get_object_or_404(Conversation, id=conversation_id, user__isnull=True)
        data = json.loads(request.body)
        new_title = data.get('title', '').strip()

        if not new_title:
            return JsonResponse({'success': False, 'error': 'Empty title'}, status=400)

        conversation.title = new_title[:200]
        conversation.save()

        return JsonResponse({'success': True, 'title': conversation.title})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def delete_conversation(request, conversation_id):
    """Delete a conversation — only the owning user may delete it"""
    try:
        if request.user.is_authenticated:
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        else:
            conversation = get_object_or_404(Conversation, id=conversation_id, user__isnull=True)
        conversation.delete()

        if str(request.session.get('conversation_id')) == str(conversation_id):
            if 'conversation_id' in request.session:
                del request.session['conversation_id']

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def get_weather_data(request):
    """Fetch and store weather data"""
    try:
        data = json.loads(request.body)
        lat = data.get('lat')
        lon = data.get('lon')
        city = data.get('city')
        
        if city:
            weather_data = get_weather_by_city(city)
            forecast_data = get_forecast_by_city(city)
        elif lat and lon:
            weather_data = get_weather(lat, lon)
            forecast_data = get_forecast(lat, lon)
        else:
            return JsonResponse({'success': False, 'error': 'Missing coordinates or city'}, status=400)
        
        if "error" in weather_data:
            return JsonResponse({'success': False, 'error': weather_data['error']})
        if "error" in forecast_data:
            return JsonResponse({'success': False, 'error': forecast_data['error']})
            
        current_report = format_weather_for_ai(weather_data)
        forecast_report = format_forecast_for_ai(forecast_data)
        
        full_report = f"{current_report}\n\n{forecast_report}"
        
        # Store in session with a timestamp so stale weather is not injected indefinitely
        import time
        request.session['weather_context'] = full_report
        request.session['weather_context_ts'] = time.time()
        
        return JsonResponse({
            'success': True, 
            'report': full_report,
            'data': {'current': weather_data, 'forecast': forecast_data}
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def transcribe_audio(request):
    """Transcribe audio via Gemini REST API directly — bypasses SDK Files API auto-upload."""
    try:
        import base64
        import requests as http_requests

        if 'audio' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No audio provided'}, status=400)

        audio_file = request.FILES['audio']
        if audio_file.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'Audio exceeds 10MB limit.'}, status=400)

        language = request.POST.get('language', 'en')
        if language not in ['en', 'ha', 'ig', 'yo']:
            language = 'en'

        audio_bytes = b''.join(audio_file.chunks())

        content_type = getattr(audio_file, 'content_type', '') or 'audio/webm'
        if 'ogg' in content_type:
            mime_type = 'audio/ogg'
        elif 'mp4' in content_type:
            mime_type = 'audio/mp4'
        elif 'wav' in content_type:
            mime_type = 'audio/wav'
        else:
            mime_type = 'audio/webm'

        language_names = {'en': 'English', 'ha': 'Hausa', 'ig': 'Igbo', 'yo': 'Yoruba'}
        lang_name = language_names.get(language, 'English')
        prompt = (
            f"Transcribe this audio exactly as spoken. "
            f"The language is {lang_name}. "
            "Return ONLY the transcription text, nothing else."
        )

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return JsonResponse({'success': False, 'error': 'Gemini API key not configured.'}, status=500)

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(audio_bytes).decode("utf-8"),
                            }
                        },
                        {"text": prompt},
                    ]
                }
            ]
        }

        resp = http_requests.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            raise Exception(f"{resp.status_code} {resp.text}")

        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return JsonResponse({'success': True, 'text': text})

    except Exception as e:
        print(f"Transcription Error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# Global cache for MMS models
mms_models = {}

def load_mms_model(lang_code):
    """Load and cache MMS model for a given language code"""
    if lang_code in mms_models:
        return mms_models[lang_code]
    
    # Map app codes to MMS codes
    # yo -> yor, ig -> ibo, ha -> hau
    iso_codes = {
        'ha': 'hau',
        'ig': 'ibo',
        'yo': 'yor'
    }
    mms_code = iso_codes.get(lang_code, lang_code)
    
    model_id = f"facebook/mms-tts-{mms_code}"
    try:
        from transformers import VitsModel, AutoTokenizer
        print(f"Loading MMS Model: {model_id}...")
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = VitsModel.from_pretrained(model_id)
        mms_models[lang_code] = (tokenizer, model)
        return tokenizer, model
    except Exception as e:
        print(f"Error loading MMS model {model_id}: {e}")
        return None, None

@csrf_exempt
@require_http_methods(["GET", "POST"])
def speak_text(request):
    """Convert text to speech using YarnGPT APIs"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
        
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            text = data.get('text', '').strip()
            language = data.get('language', 'en')
        else:
            text = request.GET.get('text', '').strip()
            language = request.GET.get('language', 'en')
            
        if language not in ['en', 'ha', 'ig', 'yo']:
            language = 'en'
        
        if not text:
            return JsonResponse({'success': False, 'error': 'No text provided'}, status=400)
        
        # Clean text
        clean_text = text.replace('*', '').replace('#', '')
        
        # Use YarnGPT API for all languages
        from utils.gemini_api import YARNGPT_API_KEY, YARNGPT_API_URL
        import requests
        from django.http import StreamingHttpResponse
        
        headers = {
            "Authorization": f"Bearer {YARNGPT_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Decide voice based on language
        # Documented voices: Idera (Yoruba/Eng), Zainab (Hausa), Chinenye (Igbo)
        voice = "Idera" 
        if language == 'ha':
            voice = "Zainab"
        elif language == 'ig':
            voice = "Chinenye"
        elif language == 'yo':
            voice = "Idera"
            
        payload = {
            "text": clean_text,
            "voice": voice
        }
            
        # Use stream=True to start passing chunks as soon as they arrive from YarnGPT
        api_response = requests.post(YARNGPT_API_URL, headers=headers, json=payload, stream=True)
        
        if api_response.status_code == 200:
            content_type = api_response.headers.get('Content-Type', 'audio/mpeg')
            
            # Pipe the response chunks directly to the browser
            response = StreamingHttpResponse(
                api_response.iter_content(chunk_size=8192),
                content_type=content_type
            )
            response['Cache-Control'] = 'no-cache'
            return response
        else:
            error_text = api_response.text
            return JsonResponse({'success': False, 'error': f"YarnGPT API Error: {error_text}"}, status=500)
        
    except Exception as e:
        try:
            print(f"TTS Error: {e}")
        except:
            pass
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
