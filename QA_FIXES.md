# Farm-Buddy-v2 — QA Fix List

> Generated: 2026-04-17  
> Branch: `claude/qa-audit-farmbuddy-qLNJ8`  
> All line numbers reference the current state of the files on this branch.

---

## Table of Contents

1. [Critical Fixes](#critical-fixes)
2. [Major Fixes](#major-fixes)
3. [Minor Fixes](#minor-fixes)
4. [Quick-Reference Summary Table](#quick-reference-summary-table)

---

## Critical Fixes

---

### C-1 · `signup_step1` — `json.loads()` outside try block

**File:** `backend/accounts/views.py` — **Line 74–96**  
**Impact:** Any malformed JSON request body crashes the server with an unhandled `JSONDecodeError` (HTTP 500, no controlled response).

**Current code:**
```python
# Line 74
if request.method == 'POST':
    if request.headers.get('Content-Type') == 'application/json':
        data = json.loads(request.body)   # ← UNPROTECTED
        data['password1'] = data.get('password')
        data['password2'] = data.get('confirmPassword')
        form = CustomUserCreationForm(data)
    else:
        form = CustomUserCreationForm(request.POST)
```

**Fix — wrap the entire POST block in a try/except:**
```python
if request.method == 'POST':
    try:
        if request.headers.get('Content-Type') == 'application/json':
            data = json.loads(request.body)
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
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
else:
    form = CustomUserCreationForm()
return render(request, 'accounts/signup.html', {'form': form, 'step': 1})
```

---

### C-2 · `login_view` — `json.loads()` outside try block

**File:** `backend/accounts/views.py` — **Line 152–173**  
**Impact:** Malformed JSON body causes unhandled `JSONDecodeError`.

**Current code:**
```python
# Line 154
if request.method == 'POST':
    if request.headers.get('Content-Type') == 'application/json':
        data = json.loads(request.body)   # ← UNPROTECTED
        form = AuthenticationForm(data=data)
    else:
        form = AuthenticationForm(data=request.POST)
```

**Fix:**
```python
if request.method == 'POST':
    try:
        if request.headers.get('Content-Type') == 'application/json':
            data = json.loads(request.body)
            form = AuthenticationForm(data=data)
        else:
            form = AuthenticationForm(data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
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
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
else:
    form = AuthenticationForm()
return render(request, 'accounts/login.html', {'form': form})
```

---

### C-3 · `profile_view` — `json.loads()` outside try block

**File:** `backend/accounts/views.py` — **Line 190–212**  
**Impact:** Malformed JSON body on POST to `/accounts/profile/` causes unhandled `JSONDecodeError`.

**Current code:**
```python
# Line 190
if request.method == 'POST':
    if request.headers.get('Content-Type') == 'application/json':
        data = json.loads(request.body)   # ← UNPROTECTED
        form = FarmerProfileForm(data, instance=profile)
    else:
        form = FarmerProfileForm(request.POST, instance=profile)
```

**Fix — wrap POST block in try/except:**
```python
if request.method == 'POST':
    try:
        if request.headers.get('Content-Type') == 'application/json':
            data = json.loads(request.body)
            form = FarmerProfileForm(data, instance=profile)
        else:
            form = FarmerProfileForm(request.POST, instance=profile)

        if form.is_valid():
            profile = form.save()
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
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
```

---

### C-4 · Telegram bot — password reset compares plaintext to hashed value

**File:** `backend/telegram_bot/bot_logic.py` — **Line 436**  
**Impact:** Password reset via Telegram **always fails** for every account registered through the web app, because the stored `security_answer` is a Django PBKDF2 hash but the comparison treats it as plaintext.

**Current code:**
```python
# Line 436
if profile.security_answer and answer.strip().lower() == profile.security_answer.strip().lower():
```

**Fix — use Django's `check_password` with legacy plaintext fallback:**

Add the import at the top of `bot_logic.py` (after line 18):
```python
from django.contrib.auth.hashers import check_password as check_hashed_password
```

Replace line 436 with:
```python
if profile.security_answer:
    stored = profile.security_answer
    if stored.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
        answer_matches = check_hashed_password(answer.strip().lower(), stored)
    else:
        # Legacy plaintext — compare and migrate
        answer_matches = (answer.strip().lower() == stored.strip().lower())
        if answer_matches:
            profile.set_security_answer(answer.strip().lower())
    
    if answer_matches:
        await update.message.reply_text(l['prompt_new_password'], parse_mode='Markdown')
        return R_NEW_PASS
    else:
        await update.message.reply_text(l['reset_failed'])
        return ConversationHandler.END
else:
    await update.message.reply_text(l['reset_failed'])
    return ConversationHandler.END
```

---

### C-5 · Telegram bot — `full_name` field does not exist on `FarmerProfile`

**File:** `backend/telegram_bot/bot_logic.py` — **Line 100–109**  
**Impact:** `db_register_user()` crashes with `TypeError: FarmerProfile() got an unexpected keyword argument 'full_name'` — Telegram signup is completely broken. The field was removed in migration `0008`.

**Current code:**
```python
# Line 100
profile = FarmerProfile.objects.create(
    user=user,
    full_name=full_name,    # ← FIELD DOES NOT EXIST
    location=location,
    ...
)
```

**Fix — replace `full_name` with `first_name`:**
```python
profile = FarmerProfile.objects.create(
    user=user,
    first_name=full_name,   # FarmerProfile uses first_name
    location=location,
    preferred_language=language,
    farm_size_acres=acres,
    soil_type=soil,
    top_pests=pests,
)
# Hash and store the security answer using the model method
if security_answer:
    profile.set_security_answer(security_answer.strip().lower())
```

Note: `security_answer` is removed from `FarmerProfile.objects.create()` because raw values must go through `set_security_answer()` (see fix C-6 below).

---

### C-6 · Telegram bot — `ask_gemini()` called synchronously inside async handler

**File:** `backend/telegram_bot/bot_logic.py` — **Line 758**  
**Impact:** Blocks the entire Telegram bot event loop while waiting for the Gemini API. Under load this will time out or freeze the bot.

**Current code:**
```python
# Line 758
response_text = ask_gemini(history, profile_context=profile_context, language=lang)
```

**Fix:**
```python
response_text = await sync_to_async(ask_gemini)(history, profile_context=profile_context, language=lang)
```

`sync_to_async` is already imported at line 6 of `bot_logic.py`.

---

## Major Fixes

---

### M-1 · Telegram bot — security answer stored as plaintext during signup

**File:** `backend/telegram_bot/bot_logic.py` — **Line 108**  
**Impact:** Security answers from Telegram signups are stored in plain text, while web signups hash them. This inconsistency means a user who signed up via Telegram and tries to reset their password via the web will fail (web side uses `check_password` on a hash, but the stored value is plaintext).

**Current code:**
```python
# Line 108
security_answer=security_answer   # ← raw plaintext stored in DB
```

**Fix:** Already handled as part of fix C-5. Remove `security_answer` from `FarmerProfile.objects.create()` and call `profile.set_security_answer()` after creation:
```python
if security_answer:
    profile.set_security_answer(security_answer.strip().lower())
```

---

### M-2 · Duplicate chat URL routing

**File:** `backend/farmbuddy_web/urls.py` — **Lines 25 and 29**  
**Impact:** Every chat route (e.g. `/send_message/`) is reachable at both `/chat/send_message/` and `/send_message/`, causing routing ambiguity, potential CSRF origin mismatches, and confusing server logs.

**Current code:**
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),   # line 25
    path('accounts/', include('accounts.urls')),
    path('sw.js', ...),
    path('manifest.json', ...),
    path('', include('chat.urls')),        # line 29 — DUPLICATE
]
```

**Fix — remove the bare `''` include, keep only `/chat/`:**
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),
    path('accounts/', include('accounts.urls')),
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript')),
    path('manifest.json', TemplateView.as_view(template_name='manifest.json', content_type='application/json')),
]
```

> **Note:** After this change, update all frontend fetch URLs that call `/send_message/`, `/new_conversation/`, etc. to use the `/chat/` prefix (e.g. `/chat/send_message/`). Check `app/chat/page.tsx` — it already uses `API_BASE = \`${API_BASE_URL}/chat\`` so the frontend is already correct.

---

### M-3 · `@csrf_exempt` on authenticated settings endpoint

**File:** `backend/accounts/views.py` — **Line 321**  
**Impact:** `user_settings_view` is `@csrf_exempt` but also handles sensitive operations (password change, profile update). Any authenticated session can be exploited via CSRF from a third-party site.

**Current code:**
```python
# Line 321
@csrf_exempt
def user_settings_view(request):
    if not request.user.is_authenticated:
        ...
```

**Fix — remove `@csrf_exempt`, rely on Django's session CSRF. The Next.js frontend must send the `X-CSRFToken` header:**
```python
# Remove @csrf_exempt entirely.
# Add @require_http_methods to be explicit:
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def user_settings_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    ...
```

In the Next.js frontend (`app/settings/page.tsx`), add the CSRF token to all POST requests:
```typescript
// Helper to get CSRF cookie
function getCsrfToken(): string {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1] ?? ''
}

// Then in each fetch:
headers: {
  'Content-Type': 'application/json',
  'X-CSRFToken': getCsrfToken(),
},
```

---

### M-4 · `@csrf_exempt` on authenticated profile endpoint

**File:** `backend/accounts/views.py` — **Line 185**  
**Impact:** Same class of issue as M-3. `profile_view` is decorated with both `@csrf_exempt` and `@login_required`, removing CSRF protection from farm data updates.

**Current code:**
```python
# Line 185
@csrf_exempt
@login_required
def profile_view(request):
```

**Fix — remove `@csrf_exempt`:**
```python
@login_required
def profile_view(request):
```

Apply the same CSRF token helper in `app/profile/page.tsx` (same pattern as M-3).

---

### M-5 · `update_language_preference` missing `@require_POST`

**File:** `backend/accounts/views.py` — **Line 365**  
**Impact:** The endpoint accepts GET requests even though it modifies data. A GET link can trigger language changes cross-site.

**Current code:**
```python
# Line 365
@login_required
def update_language_preference(request):
    if request.method == 'POST':
        ...
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
```

**Fix — add `@require_POST`:**
```python
from django.views.decorators.http import require_POST  # already imported

@login_required
@require_POST
def update_language_preference(request):
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
        return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid language'}, status=400)
```

---

### M-6 · Internal exception details leaked to clients

**File:** `backend/accounts/views.py` — **Lines 141–144, 359–360, 435–436**  
**Impact:** `str(e)` in `JsonResponse` exposes Python stack internals, DB table names, file paths, and library versions to any caller.

**Three locations:**

```python
# Line 141 (signup_step2)
except Exception as e:
    print(f"DEBUG: Step 2 Exception: {str(e)}")
    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({'success': False, 'error': str(e)}, status=500)  # ← LEAKS

# Line 359 (user_settings_view)
except Exception as e:
    return JsonResponse({'success': False, 'error': str(e)}, status=500)  # ← LEAKS

# Line 435 (forgot_password_view)
except Exception as e:
    return JsonResponse({'success': False, 'error': str(e)}, status=500)  # ← LEAKS
```

**Fix for all three locations — log internally, return generic message:**
```python
import logging
logger = logging.getLogger(__name__)

# signup_step2 (line 141)
except Exception as e:
    logger.exception("signup_step2 error")
    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)

# user_settings_view (line 359)
except Exception as e:
    logger.exception("user_settings_view error")
    return JsonResponse({'success': False, 'error': 'Server error'}, status=500)

# forgot_password_view (line 435)
except Exception as e:
    logger.exception("forgot_password_view error")
    return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
```

Add `import logging` and `logger = logging.getLogger(__name__)` near the top of `views.py` (after the existing imports).

---

### M-7 · `'pcm'` (Pidgin) language choice in DB migration but missing from bot labels

**File:** `backend/accounts/migrations/0008_remove_farmerprofile_full_name_and_more.py`  
**Also affects:** `backend/telegram_bot/bot_logic.py` — `get_localized_labels()` (line 134)  
**Impact:** If a user selects `'pcm'` as their language, `get_localized_labels('pcm')` returns `None`, and any subsequent key access (e.g. `l['welcome_back']`) throws a `TypeError`.

**Option A — Remove `'pcm'` from the migration (recommended if Pidgin is not ready):**

Create a new migration:
```python
# backend/accounts/migrations/0009_remove_pcm_language.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0008_remove_farmerprofile_full_name_and_more'),
    ]
    operations = [
        migrations.AlterField(
            model_name='farmerprofile',
            name='preferred_language',
            field=models.CharField(
                max_length=10,
                choices=[('en','English'),('ha','Hausa'),('ig','Igbo'),('yo','Yoruba')],
                default='en',
            ),
        ),
    ]
```

**Option B — Add `'pcm'` labels to `get_localized_labels()` in `bot_logic.py`:**

Copy the `'en'` block in `get_localized_labels()` and add a `'pcm'` key with Pidgin translations. Also add a safe fallback:
```python
def get_localized_labels(lang):
    labels = { 'en': {...}, 'ha': {...}, 'ig': {...}, 'yo': {...} }
    return labels.get(lang, labels['en'])  # ← fallback to English
```

The fallback alone prevents the crash even without full Pidgin translations.

---

## Minor Fixes

---

### m-1 · `speak_text` missing `@require_http_methods` decorator

**File:** `backend/chat/views.py` — **Line 574**  
**Impact:** The endpoint handles both POST and GET internally but is not declared as such — Django will not enforce method restrictions, and API documentation tooling will not know which methods are valid.

**Current code:**
```python
# Line 574
@csrf_exempt
def speak_text(request):
    if not request.user.is_authenticated:
        ...
    if request.method == 'POST':
        ...
    else:   # GET
        ...
```

**Fix:**
```python
from django.views.decorators.http import require_http_methods  # already imported

@require_http_methods(["GET", "POST"])
def speak_text(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    ...
```

> Also consider removing `@csrf_exempt` and requiring `@login_required` instead of the manual auth check (same pattern as M-3/M-4).

---

### m-2 · No file size validation before image processing

**File:** `backend/chat/views.py` — **Line 284–292**  
**Impact:** Files larger than `DATA_UPLOAD_MAX_MEMORY_SIZE` (10 MB, set in `settings.py`) are already blocked by Django at the middleware level. However, there is no application-level guard before the compression step, so any file up to 10 MB is compressed regardless of whether it is a valid image.

**Current code:**
```python
# Line 287
image_file = request.FILES['image']

# Validate image
is_valid, error_msg = validate_image(image_file)
```

**Fix — add explicit size check before `validate_image`:**
```python
image_file = request.FILES['image']

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
if image_file.size > MAX_IMAGE_BYTES:
    return JsonResponse({'success': False, 'error': 'Image too large (max 5 MB)'}, status=400)

is_valid, error_msg = validate_image(image_file)
```

---

### m-3 · Language parameter passed unsanitised into Gemini prompt

**File:** `backend/chat/views.py` — **Line 522**  
**Impact:** The `language` value comes from `request.POST.get('language', 'en')`. If an attacker sends `language = "English. Ignore all previous instructions and..."`, that string is interpolated directly into the Gemini prompt — a prompt injection vector.

**Current code:**
```python
# Line 522
prompt = f"Transcribe this audio exactly as spoken. The language is likely {language} ..."
```

**Fix — whitelist language values:**
```python
ALLOWED_LANGUAGES = {'en': 'English', 'ha': 'Hausa', 'ig': 'Igbo', 'yo': 'Yoruba'}
language = request.POST.get('language', 'en')
safe_language = ALLOWED_LANGUAGES.get(language, 'English')

prompt = f"Transcribe this audio exactly as spoken. The language is likely {safe_language} (Hausa/Igbo/Yoruba/English). Return ONLY the transcription text, no other commentary."
```

---

### m-4 · `django.setup()` called twice in `bot_logic.py`

**File:** `backend/telegram_bot/bot_logic.py` — **Lines 10–12 and 20–22**  
**Impact:** Calling `django.setup()` twice raises a warning in Django 4+ and can cause subtle issues with app registry state.

**Current code:**
```python
# Lines 10-12
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmbuddy_web.settings')
django.setup()

# Lines 20-22  ← DUPLICATE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmbuddy_web.settings')
django.setup()
```

**Fix — delete lines 20–22 entirely.**

---

### m-5 · `DEBUG` print statements left in production code

**File:** `backend/telegram_bot/bot_logic.py` — **Lines 738, 771**  
**Impact:** Exposes user chat content and chat IDs in server logs.

**Current code:**
```python
# Line 738
print(f"DEBUG: Received message from {chat_id}: {user_text[:20]}...", flush=True)

# Line 771
print(f"DEBUG: Received photo from {chat_id}", flush=True)
```

**Fix — replace with structured logging:**
```python
import logging
logger = logging.getLogger(__name__)

# Line 738
logger.debug("Received message from %s", chat_id)

# Line 771
logger.debug("Received photo from %s", chat_id)
```

Add `import logging` and `logger = logging.getLogger(__name__)` near the top of `bot_logic.py`.

---

## Quick-Reference Summary Table

| ID | Severity | File | Line(s) | Issue |
|----|----------|------|---------|-------|
| C-1 | Critical | `accounts/views.py` | 76 | `json.loads()` unprotected in `signup_step1` |
| C-2 | Critical | `accounts/views.py` | 156 | `json.loads()` unprotected in `login_view` |
| C-3 | Critical | `accounts/views.py` | 192 | `json.loads()` unprotected in `profile_view` |
| C-4 | Critical | `telegram_bot/bot_logic.py` | 436 | Plaintext vs hashed security answer comparison |
| C-5 | Critical | `telegram_bot/bot_logic.py` | 102 | `full_name` field removed — Telegram signup crashes |
| C-6 | Critical | `telegram_bot/bot_logic.py` | 758 | `ask_gemini()` called sync in async handler |
| M-1 | Major | `telegram_bot/bot_logic.py` | 108 | Security answer stored plaintext via Telegram |
| M-2 | Major | `farmbuddy_web/urls.py` | 25, 29 | Duplicate chat URL routing |
| M-3 | Major | `accounts/views.py` | 321 | `@csrf_exempt` on `user_settings_view` |
| M-4 | Major | `accounts/views.py` | 185 | `@csrf_exempt` on `profile_view` |
| M-5 | Major | `accounts/views.py` | 365 | `update_language_preference` missing `@require_POST` |
| M-6 | Major | `accounts/views.py` | 141, 359, 435 | `str(e)` leaked to client in error responses |
| M-7 | Major | `accounts/migrations/0008` | — | `'pcm'` language in DB not handled by bot labels |
| m-1 | Minor | `chat/views.py` | 574 | `speak_text` missing `@require_http_methods` |
| m-2 | Minor | `chat/views.py` | 287 | No explicit file size check before image processing |
| m-3 | Minor | `chat/views.py` | 522 | Language param unsanitised in Gemini prompt |
| m-4 | Minor | `telegram_bot/bot_logic.py` | 20–22 | `django.setup()` called twice |
| m-5 | Minor | `telegram_bot/bot_logic.py` | 738, 771 | Debug `print()` statements left in production |
