from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password as check_hashed_password
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import CustomUserCreationForm, FarmerProfileForm, UserSettingsForm
from .models import FarmerProfile, PasswordResetOTP
from chat.models import Conversation
import json
import random
import secrets
import os
import logging
from datetime import timedelta
from django.utils import timezone
import resend
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.models import User
from chat.models import Message

logger = logging.getLogger(__name__)

# Daily suggestions for different languages
TIPS = {
    'en': [
        "Water your crops early in the morning to reduce evaporation.",
        "Check soil moisture before watering - squeeze a handful of soil.",
        "Mulch around plants to retain moisture and suppress weeds.",
        "Rotate your crops annually to maintain soil health.",
        "Use compost to enrich your soil naturally.",
        "Monitor for pests regularly to catch problems early.",
        "Ensure good drainage to prevent waterlogging.",
        "Plant nitrogen-fixing crops to improve soil fertility.",
        "Keep a record of what grows well in your soil.",
        "Prune dead leaves to encourage new growth.",
    ],
    'ha': [
        "Bayar da ruwa ga amfanin gona da sassafe don rage fitar ruwa.",
        "Bincika damshin ƙasa kafin shayarwa.",
        "Yi amfani da takin gargajiya don haɓaka ƙasarku.",
        "Juya amfanin gona a kowace shekara don kiyaye lafiyar ƙasa.",
    ],
    'ig': [
        "Na-agba ihe ọkụkụ gị mmiri n'isi ụtụtụ iji belata evaporation.",
        "Lelee mmiri dị n'ala tupu ị gbaa mmiri.",
        "Jiri compost mee ka ala gị baa ọgaranya n'ụzọ sitere n'okike.",
    ],
    'yo': [
        "Fun awọn irugbin rẹ ni omi ni kutukutu owurọ lati dinku evaporation.",
        "Ṣayẹwo ọrinrin ile ṣaaju ki o to fun omi.",
        "Lo compost lati jẹ ki ile rẹ jẹ ọlọrọ nipa ti ara.",
    ],

}

def get_daily_tip(lang):
    """Returns a tip based on the day of the year to ensure it changes daily."""
    from datetime import datetime
    day_of_year = datetime.now().timetuple().tm_yday
    lang_tips = TIPS.get(lang, TIPS['en'])
    return lang_tips[day_of_year % len(lang_tips)]

# Extensive list of general tips for English (can be randomized later)
SUGGESTIONS = [
    "Water your crops early in the morning to reduce evaporation.",
    "Check soil moisture before watering - squeeze a handful of soil.",
    "Mulch around plants to retain moisture and suppress weeds.",
    "Rotate your crops annually to maintain soil health.",
    "Use compost to enrich your soil naturally.",
    "Monitor for pests regularly to catch problems early.",
    "Ensure good drainage to prevent waterlogging.",
    "Plant nitrogen-fixing crops to improve soil fertility.",
    "Keep a record of what grows well in your soil.",
    "Prune dead leaves to encourage new growth.",
]

@csrf_exempt
def signup_step1(request):
    if request.method == 'POST':
        try:
            if request.headers.get('Content-Type') == 'application/json':
                data = json.loads(request.body)
                # Map password to password1/password2 for CustomUserCreationForm
                data['password1'] = data.get('password')
                data['password2'] = data.get('confirmPassword')
                form = CustomUserCreationForm(data)
            else:
                form = CustomUserCreationForm(request.POST)
    
            if form.is_valid():
                user = form.save()
                login(request, user)
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': True, 'message': 'Account created successfully!'})
                messages.success(request, "Account created successfully! Welcome to FarmBuddy.")
                return redirect('signup_step2')
            else:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception:
            logger.exception("signup_step1 error")
            return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form, 'step': 1})


@csrf_exempt
def signup_step2(request):
    if not request.user.is_authenticated:
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'error': 'Unauthorized. Please sign up Step 1 first.'}, status=401)
        return redirect('login')
        
    profile, created = FarmerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            if request.headers.get('Content-Type') == 'application/json':
                data = json.loads(request.body)
                # Sanitize numeric fields: "" -> None
                if 'farm_size_acres' in data and data['farm_size_acres'] == '':
                    data['farm_size_acres'] = None
                form = FarmerProfileForm(data, instance=profile)
            else:
                form = FarmerProfileForm(request.POST, instance=profile)

            if form.is_valid():
                profile = form.save()

                # Hash the security answer if submitted in plaintext
                raw_answer = data.get('security_answer', '').strip() if request.headers.get('Content-Type') == 'application/json' else request.POST.get('security_answer', '').strip()
                if raw_answer:
                    profile.set_security_answer(raw_answer)

                # Sync user model names
                user = request.user
                if profile.first_name:
                    user.first_name = profile.first_name
                if profile.last_name:
                    user.last_name = profile.last_name
                user.save()

                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': True, 'message': 'Profile updated!'})
                return redirect('index')
            else:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        except Exception as e:
            logger.exception("signup_step2 error")
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'success': False, 'error': 'Server error'}, status=500)

    else:
        form = FarmerProfileForm(instance=profile)
    
    return render(request, 'accounts/signup_step2.html', {'form': form, 'step': 2, 'show_welcome': created})


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            if request.headers.get('Content-Type') == 'application/json':
                data = json.loads(request.body)
                form = AuthenticationForm(data=data)
            else:
                form = AuthenticationForm(data=request.POST)
    
            if form.is_valid():
                user = form.get_user()
                anon_conv_id = request.session.get('conversation_id')
                login(request, user)
                if anon_conv_id:
                    from chat.models import Conversation as Conv
                    Conv.objects.filter(id=anon_conv_id, user__isnull=True).update(user=user)
                    request.session['conversation_id'] = anon_conv_id
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': True, 'user': {'username': user.username, 'email': user.email}})
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('index')
            else:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception:
            logger.exception("login_view error")
            return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


@require_POST
@csrf_exempt
def logout_view(request):
    logout(request)
    if request.headers.get('Content-Type') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({'success': True})
    return redirect('login')


def _recent_chats(user):
    """Return the 5 most recent conversations with a short preview for the profile page."""
    result = []
    try:
        convs = Conversation.objects.filter(user=user).order_by('-updated_at')[:5]
        for conv in convs:
            last_msg = conv.messages.order_by('-created_at').first()
            preview = ''
            if last_msg:
                preview = last_msg.content[:100]
                if len(last_msg.content) > 100:
                    preview += '...'
            result.append({
                'id': conv.id,
                'title': conv.title or 'Chat',
                'preview': preview,
                'updated_at': conv.updated_at.isoformat(),
            })
    except Exception:
        pass
    return result


@csrf_exempt
@login_required
def profile_view(request):
    profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            if request.headers.get('Content-Type') == 'application/json':
                data = json.loads(request.body)
                form = FarmerProfileForm(data, instance=profile)
            else:
                form = FarmerProfileForm(request.POST, instance=profile)
    
            if form.is_valid():
                profile = form.save()
                # Sync with User model
                user = request.user
                user.first_name = profile.first_name or ""
                user.last_name = profile.last_name or ""
                user.save()
                
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': True, 'message': 'Farm Data updated successfully!'})
                messages.success(request, 'Farm Data updated successfully!')
                return redirect('profile')
            else:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception:
            logger.exception("profile_view error")
            return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
    else:
        form = FarmerProfileForm(instance=profile)
        if request.headers.get('Content-Type') == 'application/json' or 'application/json' in request.headers.get('Accept', ''):
            # Return profile data as JSON
            data = {
                'username': request.user.username,
                'email': request.user.email,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'preferred_language': profile.preferred_language,
                'location': profile.location,
                'farm_size_acres': str(profile.farm_size_acres) if profile.farm_size_acres else '',
                'soil_type': profile.soil_type,
                'ph_level': profile.ph_level,
                'water_source': profile.water_source,
                'current_crops': profile.current_crops,
                'past_crops': profile.past_crops,
                'top_pests': profile.top_pests,
                'has_livestock': profile.has_livestock,
                'livestock_types': profile.livestock_types,
                'telegram_is_linked': bool(profile.telegram_chat_id),
                'telegram_link_token': profile.get_or_create_link_token(),
                'telegram_bot_link': "https://t.me/{}?start={}".format(
                    os.getenv("TELEGRAM_BOT_USERNAME", "myfarmbuddy_bot"),
                    profile.get_or_create_link_token()
                ),
                'daily_tip': get_daily_tip(profile.preferred_language or 'en'),
                'recent_chats': _recent_chats(request.user),
            }
            return JsonResponse({'success': True, 'profile': data})

    # Daily suggestions
    lang = profile.preferred_language or 'en'
    daily_suggestion = get_daily_tip(lang)
    
    # Get last 5 chat messages from user
    last_chats = Message.objects.filter(
        conversation__user=request.user
    ).order_by('-created_at')[:5]
    
    # Prepare forecast data (mock 7-day forecast)
    # In production, this would come from weather API
    forecast_data = {
        'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'temps': [28, 30, 29, 31, 27, 26, 28],
        'humidity': [65, 60, 70, 55, 75, 72, 68],
    }
    
    user_lang = getattr(getattr(request.user, 'farmerprofile', None), 'preferred_language', 'en')

    labels = {
        'en': {
            'tip_label': '💡 Daily Tip',
            'connected_label': '📱 Stay Connected',
            'connected_sub': 'Get farming advice on Telegram',
            'telegram_btn': 'Open Telegram Bot',
            'edit_farm': 'Edit Farm Data',
            'save_farm': 'Save Farm Data',
            'forecast_label': '📊 Weekly Forecast',
            'chat_label': '💬 Recent Chat History',
            'no_msgs': 'No recent messages. Start chatting to see your history here.',
        },
        'ha': {
            'tip_label': '💡 Shawarar Rana',
            'connected_label': '📱 Kasance da Mu',
            'connected_sub': 'Sami shawarwarin noma a Telegram',
            'telegram_btn': 'Bude Telegram Bot',
            'edit_farm': 'Gyara Bayanan Gona',
            'save_farm': 'Ajiye Bayanan Gona',
            'forecast_label': '📊 Hasashen Mako',
            'chat_label': '💬 Tattaunawar Karshe',
            'no_msgs': 'Babu saƙonni kwanan nan. Fara hira don ganin tarihin ku a nan.',
        },
        'ig': {
            'tip_label': '💡 Ndụmọdụ Kwa Ụbọchị',
            'connected_label': '📱 Nọrọ na njikọ',
            'connected_sub': 'Nweta ndụmọdụ ọrụ ugbo na Telegram',
            'telegram_btn': 'Mepee Telegram Bot',
            'edit_farm': 'Dezie Data Ugbo',
            'save_farm': 'Chekwaa Data Ugbo',
            'forecast_label': '📊 Amụma Izu Nke a',
            'chat_label': '💬 Mkparịta Ọhụrụ Ndị Na-adịbeghị anya',
            'no_msgs': 'Enweghị ozi ndị na-adịbeghị anya. Malite nkata ka ịhụ akụkọ ihe mere eme gị ebe a.',
        },
        'yo': {
            'tip_label': '💡 Imọran Ojoojumọ',
            'connected_label': '📱 Wa ni Isopọ',
            'connected_sub': 'Gba imọran ogbin lori Telegram',
            'telegram_btn': 'Ṣii Telegram Bot',
            'edit_farm': 'Ṣatunkọ Data Oko',
            'save_farm': 'Fi Data Oko Pam',
            'forecast_label': '📊 Àsọtẹ́lẹ̀ Ọ̀sẹ̀',
            'chat_label': '💬 Itan Ifọrọwerọ Titun',
            'no_msgs': 'Ko si ifiranṣẹ tuntun. Bẹrẹ ifọrọwerọ lati wo itan rẹ nibi.',
        },
    }

    # Get or create telegram link token
    profile = request.user.farmerprofile
    link_token = profile.get_or_create_link_token()
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "myfarmbuddy_bot")
    telegram_bot_link = f"https://t.me/{bot_username}?start={link_token}"

    context = {
        'form': form,
        'last_chats': last_chats,
        'forecast_data': json.dumps(forecast_data),
        'daily_suggestion': daily_suggestion,
        'telegram_bot_link': telegram_bot_link,
        **labels.get(user_lang, labels['en'])
    }

    return render(request, 'accounts/profile.html', context)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def user_settings_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
        
    if request.method == 'GET':
        profile = getattr(request.user, 'farmerprofile', None)
        return JsonResponse({
            'success': True,
            'user': {
                'username': request.user.username,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'preferred_language': profile.preferred_language if profile else 'en'
            }
        })

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'update_profile':
                user_form = UserSettingsForm(data, user=request.user)
                if user_form.is_valid():
                    user_form.save()
                    return JsonResponse({'success': True, 'message': 'Profile updated successfully!'})
                return JsonResponse({'success': False, 'errors': user_form.errors}, status=400)
                
            elif action == 'change_password':
                password_form = PasswordChangeForm(request.user, data)
                if password_form.is_valid():
                    user = password_form.save()
                    login(request, user)
                    return JsonResponse({'success': True, 'message': 'Password updated successfully!'})
                return JsonResponse({'success': False, 'errors': password_form.errors}, status=400)

            elif action == 'update_security':
                answer = data.get('security_answer', '').strip()
                confirm = data.get('security_answer_confirm', '').strip()
                if not answer:
                    return JsonResponse({'success': False, 'error': 'Answer cannot be empty.'}, status=400)
                if answer.lower() != confirm.lower():
                    return JsonResponse({'success': False, 'error': 'Answers do not match.'}, status=400)
                profile = getattr(request.user, 'farmerprofile', None)
                if not profile:
                    return JsonResponse({'success': False, 'error': 'Profile not found.'}, status=404)
                profile.set_security_answer(answer)
                profile.save()
                return JsonResponse({'success': True, 'message': 'Security answer updated successfully!'})

            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
        except Exception as e:
            logger.exception("user_settings_view error")
            return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
            
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)



@csrf_exempt
@login_required
@require_POST
def update_language_preference(request):
    """API endpoint to update user language via AJAX from the global navbar"""
    try:
        data = json.loads(request.body)
        new_var = data.get('language')
        if new_var in dict(FarmerProfile.LANGUAGE_CHOICES):
            profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
            profile.preferred_language = new_var
            profile.save()
            return JsonResponse({'status': 'success'})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception:
        logger.exception("update_language_preference error")
        return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

def _mask_email(email: str) -> str:
    """Return a***@domain.com style masked email."""
    if not email or '@' not in email:
        return ''
    local, domain = email.split('@', 1)
    return local[0] + '***@' + domain


@csrf_exempt
def forgot_password_view(request):
    """API endpoint for password recovery — security question or email OTP."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            username = data.get('username')

            if not username:
                return JsonResponse({'success': False, 'error': 'Username is required'}, status=400)

            try:
                user = User.objects.get(username__iexact=username)
                profile = user.farmerprofile
            except (User.DoesNotExist, FarmerProfile.DoesNotExist):
                return JsonResponse({'success': False, 'error': 'If this account exists, recovery is available.'}, status=404)

            # ── Security question flow (existing) ──────────────────────────
            if action == 'get_question':
                return JsonResponse({
                    'success': True,
                    'question': "What is the name of your grand father?",
                    'has_answer': bool(profile.security_answer),
                    'has_email': bool(user.email),
                    'email_hint': _mask_email(user.email),
                })

            elif action == 'reset_password':
                answer = data.get('answer', '')
                new_password = data.get('new_password', '')

                if not profile.security_answer:
                    return JsonResponse({'success': False, 'error': 'Security question not set for this account.'}, status=400)

                answer_matches = False
                stored = profile.security_answer
                if stored.startswith('pbkdf2_') or stored.startswith('bcrypt') or stored.startswith('argon2'):
                    answer_matches = check_hashed_password(answer.strip().lower(), stored)
                else:
                    answer_matches = (answer.strip().lower() == stored.strip().lower())
                    if answer_matches:
                        profile.set_security_answer(answer.strip().lower())

                if answer_matches:
                    if len(new_password) < 8:
                        return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters'}, status=400)
                    user.set_password(new_password)
                    user.save()
                    return JsonResponse({'success': True, 'message': 'Password reset successful!'})
                else:
                    return JsonResponse({'success': False, 'error': 'Incorrect security answer'}, status=400)

            # ── OTP flow (new) ──────────────────────────────────────────────
            elif action == 'request_otp':
                if not user.email:
                    return JsonResponse({'success': False, 'error': 'No email address on this account.'}, status=400)

                # Rate-limit: block if a fresh OTP was created < 60 seconds ago
                existing = PasswordResetOTP.objects.filter(user=user, is_used=False).first()
                if existing:
                    age = (timezone.now() - existing.created_at).total_seconds()
                    if age < 60:
                        wait = int(60 - age)
                        return JsonResponse({'success': False, 'too_soon': True, 'wait_seconds': wait}, status=429)

                otp_code = str(secrets.randbelow(900000) + 100000)
                PasswordResetOTP.objects.update_or_create(
                    user=user,
                    defaults={
                        'otp': otp_code,
                        'expires_at': timezone.now() + timedelta(minutes=10),
                        'is_used': False,
                    }
                )

                try:
                    from django.conf import settings as django_settings
                    resend.api_key = django_settings.RESEND_API_KEY
                    resend.Emails.send({
                        'from_': django_settings.DEFAULT_FROM_EMAIL,
                        'to': [user.email],
                        'subject': 'FarmBuddy – Your Password Reset Code',
                        'text': (
                            f'Hello {user.username},\n\n'
                            f'Your FarmBuddy password reset code is:\n\n'
                            f'    {otp_code}\n\n'
                            f'This code expires in 10 minutes. Do not share it with anyone.\n\n'
                            f'If you did not request a password reset, you can safely ignore this email.\n\n'
                            f'— The FarmBuddy Team'
                        ),
                    })
                except Exception:
                    logger.exception("Failed to send OTP email to %s", user.email)
                    return JsonResponse({'success': False, 'error': 'Failed to send email. Please try again or use the security question.'}, status=500)

                return JsonResponse({'success': True, 'email_hint': _mask_email(user.email)})

            elif action == 'verify_otp':
                otp_input = data.get('otp', '').strip()
                new_password = data.get('new_password', '')

                try:
                    record = PasswordResetOTP.objects.get(user=user)
                except PasswordResetOTP.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'No reset code found. Please request a new one.'}, status=400)

                if not record.is_valid():
                    return JsonResponse({'success': False, 'error': 'Your code has expired. Please request a new one.'}, status=400)

                if not secrets.compare_digest(record.otp, otp_input):
                    return JsonResponse({'success': False, 'error': 'Invalid code. Please check and try again.'}, status=400)

                if len(new_password) < 8:
                    return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters.'}, status=400)

                record.is_used = True
                record.save(update_fields=['is_used'])
                user.set_password(new_password)
                user.save()
                return JsonResponse({'success': True, 'message': 'Password reset successful!'})

            return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
        except Exception as e:
            logger.exception("forgot_password_view error")
            return JsonResponse({'success': False, 'error': 'Server error'}, status=500)

    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
