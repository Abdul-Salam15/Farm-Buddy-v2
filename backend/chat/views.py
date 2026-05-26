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
from utils.openai_api import ask_openai, analyze_plant_image
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
                stream = ask_openai(messages_history, weather_context=weather_context, profile_context=system_prompt, stream=True, language=language)
                
                for chunk in stream:
                    full_response += chunk
                    yield json.dumps({'chunk': chunk}) + "\n"
                
                try:
                    clean_text, refs = parse_xai_refs(full_response)
                except Exception:
                    clean_text, refs = full_response, []

                # Strip any leading [Status: ...] lines injected during function calling
                import re as _re
                clean_text = _re.sub(r'^\[Status:[^\]]*\]\s*\n*', '', clean_text).strip()
                full_response_display = _re.sub(r'^\[Status:[^\]]*\]\s*\n*', '', full_response).strip()

                Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=clean_text,
                    references=refs
                )

                yield json.dumps({'success': True, 'full_text': full_response_display, 'references': refs, 'conversation_id': conversation.id}) + "\n"
                
                if conversation.messages.count() == 2 and (not conversation.title or conversation.title == "New Chat"):
                     def update_title_background(conv_id, text):
                        try:
                            from utils.openai_api import summarize_title
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


@require_GET
def api_search_messages(request):
    """Search message content and return matching conversations with snippets."""
    query = request.GET.get('q', '').strip()
    if len(query) < 2 or not request.user.is_authenticated:
        return JsonResponse({'success': True, 'results': []})

    try:
        messages = (
            Message.objects
            .filter(conversation__user=request.user, content__icontains=query)
            .select_related('conversation')
            .order_by('-conversation__updated_at', 'id')
        )

        seen = set()
        results = []
        for msg in messages:
            cid = msg.conversation_id
            if cid in seen:
                continue
            seen.add(cid)
            content = msg.content
            idx = content.lower().find(query.lower())
            start = max(0, idx - 40)
            end = min(len(content), idx + len(query) + 60)
            snippet = ('…' if start > 0 else '') + content[start:end].strip() + ('…' if end < len(content) else '')
            results.append({
                'conversation_id': cid,
                'conversation_title': msg.conversation.title,
                'snippet': snippet,
                'updated_at': msg.conversation.updated_at.isoformat(),
                'message_id': msg.id,
            })
            if len(results) >= 20:
                break

        return JsonResponse({'success': True, 'results': results})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_image(request):
    """Handle plant image upload and analysis"""
    try:
        from utils.openai_api import analyze_plant_image
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

        # Write image bytes to a temp file for Vision analysis (works with any
        # storage backend including Cloudinary, which has no local .path).
        import tempfile as _tempfile
        image_file.seek(0)
        _tmp_image = _tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        _tmp_image.write(image_file.read())
        _tmp_image.flush()
        _tmp_image.close()
        image_path = _tmp_image.name
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

        from django.http import StreamingHttpResponse

        # Build context for vision analysis
        system_prompt = build_system_prompt(request.user if request.user.is_authenticated else None)
        weather_context = request.session.get('weather_context') or ''
        combined_context = f"{system_prompt}\n\n[WEATHER INFO]: {weather_context}" if system_prompt else weather_context

        # Save AI response placeholder and then yield chunks
        def vision_response_generator():
            full_response = ""
            try:
                # Analyze image with OpenAI Vision in streaming mode
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
            finally:
                import os as _os
                if _os.path.exists(image_path):
                    _os.remove(image_path)

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
    """Transcribe audio using OpenAI Whisper."""
    import tempfile
    from utils.openai_api import transcribe_audio_file

    try:
        if 'audio' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No audio provided'}, status=400)

        audio_file_obj = request.FILES['audio']
        if audio_file_obj.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'Audio exceeds 10MB limit.'}, status=400)

        language = request.POST.get('language', 'en')
        if language not in ['en', 'ha', 'ig', 'yo']:
            language = 'en'

        content_type = getattr(audio_file_obj, 'content_type', '') or 'audio/webm'
        if 'ogg' in content_type:
            ext, mime_type = '.ogg', 'audio/ogg'
        elif 'mp4' in content_type:
            ext, mime_type = '.mp4', 'audio/mp4'
        elif 'wav' in content_type:
            ext, mime_type = '.wav', 'audio/wav'
        else:
            ext, mime_type = '.webm', 'audio/webm'

        audio_bytes = b''.join(audio_file_obj.chunks())
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            text = transcribe_audio_file(tmp_path, mime_type, language)
            return JsonResponse({'success': True, 'text': text})

        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

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

        # Strip markdown formatting so it isn't read aloud literally
        import re as _re
        clean_text = text
        clean_text = _re.sub(r'\[FARMBUDDY_REFS\].*?\[/FARMBUDDY_REFS\]', '', clean_text, flags=_re.DOTALL)
        clean_text = _re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
        clean_text = _re.sub(r'\*(.*?)\*', r'\1', clean_text)
        clean_text = _re.sub(r'_(.*?)_', r'\1', clean_text)
        clean_text = _re.sub(r'`[^`]*`', '', clean_text)
        clean_text = _re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_text)
        clean_text = _re.sub(r'^#{1,6}\s*', '', clean_text, flags=_re.MULTILINE)
        clean_text = _re.sub(r'^\s*[-*]\s+', '', clean_text, flags=_re.MULTILINE)
        clean_text = _re.sub(r'^\s*\d+\.\s+', '', clean_text, flags=_re.MULTILINE)
        clean_text = _re.sub(r'\n{3,}', '\n\n', clean_text).strip()
        # Cap at 2000 chars as a safety bound; YarnGPT handles long text fine
        # and audio is prefetched in the background, so latency is hidden.
        if len(clean_text) > 2000:
            clean_text = clean_text[:2000].rsplit(' ', 1)[0] + '...'
        
        # Use YarnGPT API for all languages
        from utils.openai_api import YARNGPT_API_KEY, YARNGPT_API_URL
        import requests
        
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

        import hashlib
        from django.core.cache import cache
        from django.http import HttpResponse
        cache_key = f"tts_{hashlib.md5(f'{clean_text}:{voice}'.encode()).hexdigest()}"
        cached_audio = cache.get(cache_key)
        if cached_audio:
            response = HttpResponse(cached_audio, content_type='audio/mpeg')
            response['Cache-Control'] = 'private, max-age=86400'
            return response

        # Try YarnGPT first (Nigerian voices). 15s read timeout — if it hasn't
        # responded by then it is overloaded; fall through to OpenAI TTS.
        audio_bytes = None
        content_type = 'audio/mpeg'
        try:
            api_response = requests.post(
                YARNGPT_API_URL, headers=headers, json=payload,
                timeout=(5, 15)
            )
            if api_response.status_code == 200:
                content_type = api_response.headers.get('Content-Type', 'audio/mpeg')
                audio_bytes = api_response.content
            else:
                print(f"YarnGPT API Error ({api_response.status_code}): {api_response.text[:200]}")
        except Exception as yarn_err:
            print(f"YarnGPT failed ({yarn_err}), falling back to gTTS")

        if audio_bytes is None:
            from gtts import gTTS
            import io as _io
            gtts_lang = {'en': 'en', 'ha': 'ha', 'ig': 'ig', 'yo': 'yo'}.get(language, 'en')
            buf = _io.BytesIO()
            gTTS(text=clean_text, lang=gtts_lang).write_to_fp(buf)
            audio_bytes = buf.getvalue()
            content_type = 'audio/mpeg'

        cache.set(cache_key, audio_bytes, timeout=86400)
        response = HttpResponse(audio_bytes, content_type=content_type)
        response['Cache-Control'] = 'private, max-age=86400'
        return response

    except Exception as e:
        print(f"TTS Error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
