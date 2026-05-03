import os
import tempfile
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import django
from datetime import datetime
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler

# Setup Django environment (no-op if already configured, e.g. when called from management command)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmbuddy_web.settings')
if not django.conf.settings.configured:
    django.setup()

from accounts.models import FarmerProfile
from chat.models import Conversation, Message
from utils.gemini_api import ask_gemini, analyze_plant_image, model
from utils.weather_api import get_forecast_by_city
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password as check_hashed_password
from django.db import close_old_connections
import logging

logger = logging.getLogger(__name__)

# --- DB SYNC HELPERS ---
# These functions MUST be called using sync_to_async from inside handlers.
# Each one calls close_old_connections() so stale connections (e.g. after
# Render sleeps) are discarded before any ORM access.

def _db(func):
    """Decorator: close stale DB connections before each ORM call."""
    def wrapper(*args, **kwargs):
        close_old_connections()
        return func(*args, **kwargs)
    return wrapper

@_db
def db_get_profile_by_token(token):
    try:
        profile = FarmerProfile.objects.get(telegram_link_token=token)
        return profile, profile.user.first_name or profile.user.username
    except FarmerProfile.DoesNotExist:
        return None, None

@_db
def db_link_profile(token, chat_id):
    try:
        profile = FarmerProfile.objects.get(telegram_link_token=token)
        profile.telegram_chat_id = chat_id
        profile.telegram_link_token = None
        profile.save()
        return profile.user.first_name or profile.user.username
    except FarmerProfile.DoesNotExist:
        return None

@_db
def db_unlink_chat(chat_id):
    try:
        profile = FarmerProfile.objects.get(telegram_chat_id=chat_id)
        profile.telegram_chat_id = None
        profile.save()
        return True
    except FarmerProfile.DoesNotExist:
        return False

@_db
def db_get_profile_info(chat_id):
    try:
        profile = FarmerProfile.objects.get(telegram_chat_id=chat_id)
        u = profile.user
        return {
            'username': u.first_name or u.username,
            'lang': profile.preferred_language or 'en',
            'location': profile.location or '---',
            'soil_display': profile.get_soil_type_display(),
            'soil_type': profile.soil_type,
            'farm_size': str(profile.farm_size_acres or '0'),
            'user_obj': u,
            'profile_obj': profile
        }
    except FarmerProfile.DoesNotExist:
        return None

@_db
def db_get_or_create_conv(user):
    conv, _ = Conversation.objects.get_or_create(user=user, title="Telegram Chat")
    return conv

@_db
def db_save_msg(conv, role, content):
    return Message.objects.create(conversation=conv, role=role, content=content)

@_db
def db_get_history(conv, limit=10):
    msgs = Message.objects.filter(conversation=conv).order_by('-created_at')[:limit]
    return [{"role": m.role, "content": m.content} for m in reversed(msgs)]

@_db
def db_update_profile(chat_id, **kwargs):
    profile = FarmerProfile.objects.get(telegram_chat_id=chat_id)
    for k, v in kwargs.items():
        setattr(profile, k, v)
    profile.save()
    return profile

@_db
def db_authenticate_user(username, password):
    user = authenticate(username=username, password=password)
    return user

@_db
def db_check_username(username):
    return User.objects.filter(username__iexact=username).exists()

@_db
def db_register_user(username, password, full_name, location, language, acres=0, soil='unknown', pests='', security_answer=''):
    if User.objects.filter(username=username).exists():
        return None
    user = User.objects.create_user(username=username, password=password, first_name=full_name)
    profile = FarmerProfile.objects.create(
        user=user,
        first_name=full_name,
        location=location,
        preferred_language=language,
        farm_size_acres=acres,
        soil_type=soil,
        top_pests=pests,
    )
    if security_answer:
        profile.set_security_answer(security_answer.strip().lower())
    return user, profile

@_db
def db_migrate_security_answer(profile, answer):
    profile.set_security_answer(answer)

@_db
def db_get_profile_by_username(username):
    try:
        user = User.objects.get(username__iexact=username)
        profile = FarmerProfile.objects.get(user=user)
        return user, profile
    except (User.DoesNotExist, FarmerProfile.DoesNotExist):
        return None, None

@_db
def db_update_password(user, new_password):
    user.set_password(new_password)
    user.save()
    return True

@_db
def db_link_user_by_id(user_id, chat_id):
    try:
        profile = FarmerProfile.objects.get(user_id=user_id)
        profile.telegram_chat_id = chat_id
        profile.save()
        return profile
    except FarmerProfile.DoesNotExist:
        return None

def get_localized_labels(lang):
    labels = {
        'en': {
            'dash_header': "📊 **Your Farm Dashboard**",
            'name': "Name",
            'location': "Location",
            'soil_type': "Soil Type",
            'farm_size': "Farm Size",
            'tip_header': "💡 **Daily Agricultural Tip**",
            'not_linked': "❌ Your account is not linked. Use /start to link.",
            'acres': "acres",
            'welcome_back': "Welcome back, {name}! How can I help you today?\n\nCommands:\n/dashboard - View farm summary\n/tip - Get daily advice\n/forecast - View weekly weather graph\n/language - Change language\n/edit_profile - Update farm data",
            'analyzing_photo': "📸 Analyzing your leaf photo... please wait.",
            'no_location': "📍 Location not set. Please set your location on the website to see weather forecasts.",
            'forecast_title': "7-Day Weather Forecast",
            'temp': "Temp (°C)",
            'humidity': "Humidity (%)",
            'edit_start': "📝 Let's update your farm profile. What is the **location** of your farm? (e.g. 'Abuja, FCT')",
            'edit_size': "📐 Great! What is your **farm size** in acres? (Just send a number, or 0 if unsure)",
            'edit_soil': "🌱 Almost done! What is your **soil type**?",
            'edit_desc': "📝 How would you **describe** your soil? (e.g. 'Dark and rich')",
            'edit_done': "✅ Thank you! Your farm profile has been updated.",
            'cancel': "❌ Profile update cancelled.",
            'loamy': "Loamy",
            'sandy': "Sandy",
            'clay': "Clay",
            'silty': "Silty",
            'not_sure': "I am not sure",
            'select_language': "🌍 **Select your preferred language:**",
            'language_changed': "✅ Language changed to **English**. All future messages will be in English.",
            'logout_success': "✅ You have been logged out. Your account is now unlinked from this Telegram chat.",
            'auth_welcome': "Welcome to FarmBuddy! 🌾\n\nPlease choose an option to get started:",
            'btn_login': "🔑 Login",
            'btn_signup': "📝 Sign Up",
            'btn_forgot': "❓ Forgot Password",
            'btn_link': "🔗 Link Web Account",
            'prompt_username': "Enter your **username**:",
            'prompt_password': "Enter your **password**:",
            'prompt_grandfather': "🛡️ **Security Question**: What is the name of your grand father?",
            'prompt_new_password': "Enter your **new password** (at least 6 characters):",
            'auth_success': "✅ Login successful! Welcome back, {name}.",
            'auth_failed': "❌ Invalid username or password. Please try again or use /start to reset.",
            'reset_success': "✅ Password reset successful! You can now log in with your new password.",
            'reset_failed': "❌ Answer incorrect. Password reset failed.",
            'user_not_found': "❌ Username not found.",
            'signup_user': "Great! Let's create your account. What **username** would you like to use?",
            'signup_pass': "Choose a **strong password** (at least 6 characters):",
            'signup_name': "What is your **full name**?",
            'signup_loc': "Which **town and state** do you farm in?",
            'signup_size': "What is your **farm size** in acres? (Just send a number)",
            'signup_soil': "What is your **soil type**?",
            'signup_pests': "Which **pests or diseases** do you usually encounter? (e.g. armyworms, aphids)",
            'signup_lang': "Which **language** do you prefer?",
            'user_exists': "❌ This username is already taken. Please try another one:",
            'signup_done': "🎉 Account created successfully! You can now use FarmBuddy.",
            'connect_info': "To use FarmBuddy on Telegram, you can either:\n\n1. Use the **'Open Telegram'** button on the website's 'My Farm' page.\n2. **Log in** directly here if you already have an account.\n3. **Sign up** to create a new account.",
        },
        'ha': {
            'dash_header': "📊 **Dashboard na Gona ta**",
            'name': "Suna",
            'location': "Wuri",
            'soil_type': "Irin Kasa",
            'farm_size': "Girman Gona",
            'tip_header': "💡 **Shawarar Rana**",
            'not_linked': "❌ Ba a haɗa asusunku ba. Yi amfani da /start don haɗawa.",
            'acres': "acres",
            'welcome_back': "Barka da dawowa, {name}! Ta yaya zan iya taimaka muku yau?\n\nDokokin:\n/dashboard - Duba takaitaccen bayani\n/tip - Sami shawara\n/forecast - Duba jadawalin yanayi\n/language - Canza yare\n/edit_profile - Sabunta bayanan gona",
            'analyzing_photo': "📸 Ana nazarin hoton ganyenku... jira kadan.",
            'no_location': "📍 Ba a saita wuri ba. Da fatan za a saita wurin ku a gidan yanar gizon don ganin hasashen yanayi.",
            'forecast_title': "Hasashen Yanayi Na Kwanaki 7",
            'temp': "Zafi (°C)",
            'humidity': "Danshi (%)",
            'edit_start': "📝 Bari mu sabunta bayanan gonar ku. Menene **wurin** gonar ku? (misali 'Kano')",
            'edit_size': "📐 Madalla! Menene **girman gonar ku** a eka? (Aika lamba kawai)",
            'edit_soil': "🌱 Kusan karewa! Wane **irin kasa** ce a gonar ku?",
            'edit_desc': "📝 Ta yaya zaku **bayyana** kasar ku? (misali 'Bakar kasa')",
            'edit_done': "✅ Na gode! An sabunta bayanan gonar ku.",
            'cancel': "❌ An soke sabuntawa.",
            'loamy': "Loamy",
            'sandy': "Sandy",
            'clay': "Clay",
            'silty': "Silty",
            'not_sure': "Ban sani ba",
            'select_language': "🌍 **Zaɓi yaren da kake so:**",
            'language_changed': "✅ An canza yare zuwa **Hausa**. Duk saƙonni na gaba za su kasance a cikin Hausa.",
            'logout_success': "✅ Kun fita daga asusunku. An cire haɗin asusunku daga wannan Telegram chat.",
            'auth_welcome': "Barka da zuwa FarmBuddy! 🌾\n\nDa fatan za a zaɓi zaɓi don farawa:",
            'btn_login': "🔑 Shiga",
            'btn_signup': "📝 Yi Rajista",
            'btn_forgot': "❓ Mantan Kalmar Sirri",
            'btn_link': "🔗 Haɗa Lambar Web",
            'prompt_username': "Shigar da **sunan mai amfani** (username):",
            'prompt_password': "Shigar da **kalmar sirri** (password):",
            'prompt_grandfather': "🛡️ **Tambayar Tsaro**: Menene sunan kakan ku (mahaifin mahaifinku)?",
            'prompt_new_password': "Shigar da **sabuwar kalmar sirri** (aƙalla haruffa 6):",
            'auth_success': "✅ An yi nasarar shiga! Barka da dawowa, {name}.",
            'auth_failed': "❌ Sunan mai amfani ko kalmar sirri ba daidai ba. Da fatan za a sake gwadawa ko amfani da /start.",
            'reset_success': "✅ An yi nasarar canza kalmar sirri! Yanzu zaka iya shiga da sabuwar kalmar sirri.",
            'reset_failed': "❌ Amsar ba daidai ba tafi. Ba a sanya sabuwar kalmar sirri ba.",
            'user_not_found': "❌ Ba a sami sunan mai amfani ba.",
            'signup_user': "Madalla! Bari mu ƙirƙiri asusunku. Wane **suna** kuke son amfani da shi?",
            'signup_pass': "Zaɓi **kalmar sirri mai ƙarfi** (aƙalla haruffa 6):",
            'signup_name': "Menene **cikakken sunanku**?",
            'signup_loc': "Wace **gari da jiha** kuke noma?",
            'signup_size': "Menene **girman gonar ku** a eka? (Aika lamba kawai)",
            'signup_soil': "Wane **irin kasa** ce a gonar ku?",
            'signup_pests': "Wace **kwari ko cututtuka** kuke yawan fuskanta? (misali armyworms, aphids)",
            'signup_lang': "Wane **yare** kuka fi so?",
            'user_exists': "❌ An riga an ɗauki wannan sunan. Da fatan za a gwada wani:",
            'signup_done': "🎉 An ƙirƙiri asusu cikin nasara! Yanzu zaku iya amfani da FarmBuddy.",
            'connect_info': "Don amfani da FarmBuddy akan Telegram, zaku iya:\n\n1. Yi amfani da maballin **'Open Telegram'** akan shafin 'My Farm'.\n2. **Shiga (Log in)** kai tsaye a nan idan riga kuna da asusu.\n3. **Yi Rajista (Sign up)** don ƙirƙirar sabon asusu.",
        },
        'ig': {
            'dash_header': "📊 **Dashboard nke Ugbo Gị**",
            'name': "Aha",
            'location': "Ebe",
            'soil_type': "Ụdị Ala",
            'farm_size': "Ogo Ugbo",
            'tip_header': "💡 **Ndụmọdụ Kwa Ụbọchị**",
            'not_linked': "❌ Ejikọghị akaụntụ gị. Jiri /start jikọọ.",
            'acres': "acres",
            'welcome_back': "Nnọọ ọzọ, {name}! Kedu otu m ga-esi nyere gị aka taa?\n\nIwu:\n/dashboard - Nweta nchịkọta ugbo\n/tip - Nweta ndụmọdụ\n/forecast - Lelee eserese ihu igwe\n/language - Gbanwee asụsụ\n/edit_profile - Melite data ugbo",
            'analyzing_photo': "📸 Na-enyocha foto akwụkwọ gị... biko chere.",
            'no_location': "📍 Edetaghị ebe. Biko tọọ ebe ị nọ na webụsaịtị ka ị hụ amụma ihu igwe.",
            'forecast_title': "Amụma Ihu Igwe nke Ụbọchị 7",
            'temp': "Okpomọkụ (°C)",
            'humidity': "Iru mmiri (%)",
            'edit_start': "📝 Ka anyị melite profaịlụ ugbo gị. Ebee ka **ebe** ugbo gị dị? (dịka 'Enugu')",
            'edit_size': "📐 Ọ dị mma! Gịnị bụ **ogo ugbo gị** na acres? (Naanị zipu nọmba)",
            'edit_soil': "🌱 Ọ fọrọ nke nta ka emechaa! Kedu **ụdị ala** ọ bụ?",
            'edit_desc': "📝 Kedu otu ị ga-esi **akọwa** ala gị? (dịka 'Ojii ma nwee nri')",
            'edit_done': "✅ Daalụ! Emelitere profaịlụ ugbo gị.",
            'cancel': "❌ Akagburu mmelite profaịlụ.",
            'loamy': "Loamy",
            'sandy': "Sandy",
            'clay': "Clay",
            'silty': "Silty",
            'not_sure': "Amaghị m",
            'select_language': "🌍 **Họrọ asụsụ kacha amasị gị:**",
            'language_changed': "✅ Agbanarịla asụsụ gaa na **Asụsụ Igbo**. Ozi niile n'ọdịnihu ga-adị n'asụsụ Igbo.",
            'logout_success': "✅ Ị pụọla na akaụntụ gị. Agụpụla akaụntụ gị na nkata Telegram a.",
            'auth_welcome': "Nnọọ na FarmBuddy! 🌾\n\nBiko họrọ otu ụzọ ị ga-esi malite:",
            'btn_login': "🔑 Banye",
            'btn_signup': "📝 Debanye aha",
            'btn_forgot': "❓ Chezọrọ paswọọdụ",
            'btn_link': "🔗 Jikọọ Webụ",
            'prompt_username': "Tinye **aha njirimara** gị:",
            'prompt_password': "Tinye **paswọọdụ** gị:",
            'prompt_grandfather': "🛡️ **Ajụjụ Nchebe**: Gịnị bụ aha nna nna gị?",
            'prompt_new_password': "Tinye **paswọọdụ ọhụrụ** (opekata mpe mkpụrụedemede 6):",
            'auth_success': "✅ Mbanye gara nke ọma! Nnọọ ọzọ, {name}.",
            'auth_failed': "❌ Aha njirimara ma ọ bụ paswọọdụ adịghị mma. Biko gbalịa ọzọ ma ọ bụ jiri /start.",
            'reset_success': "✅ Ntọala paswọọdụ gara nke ọma! Ugbu a ị nwere ike iji paswọọdụ ọhụrụ gị bata.",
            'reset_failed': "❌ Azịza ya adịghị mma. Ntọala paswọọdụ dara.",
            'user_not_found': "❌ Ahụghị aha njirimara.",
            'signup_user': "Ọ dị mma! Ka anyị mepụta akaụntụ gị. Kedu **aha njirimara** ị ga-achọ iji?",
            'signup_pass': "Họrọ **paswọọdụ siri ike** (opekata mpe mkpụrụedemede 6):",
            'signup_name': "Gịnị bụ **aha gị zuru ezu**?",
            'signup_loc': "Kedu **obodo na steeti** ị na-arụ ọrụ ugbo?",
            'signup_size': "Gịnị bụ **ogo ugbo gị** na acres? (Naanị zipu nọmba)",
            'signup_soil': "Kedu **ụdị ala** ọ bụ?",
            'signup_pests': "Kedu **ihe ọkụkụ ma ọ bụ ọrịa** ị na-ezutekarị? (dịka armyworms, aphids)",
            'signup_lang': "Kedu **asụsụ** kacha amasị gị?",
            'user_exists': "❌ Ejila aha njirimara a. Biko gbalịa ọzọ:",
            'signup_done': "🎉 Emepụtala akaụntụ gị nke ọma! Ugbu a ị nwere ike iji FarmBuddy.",
            'connect_info': "Iji jiri FarmBuddy na Telegram, ị nwere ike:\n\n1. Jiri bọtịnụ **'Open Telegram'** na webụsaịtị 'My Farm'.\n2. **Banye (Log in)** ozugbo ebe a ma ọ bụrụ na ị nwere akaụntụ.\n3. **Debanye aha (Sign up)** iji mepụta akaụntụ ọhụrụ.",
        },
        'yo': {
            'dash_header': "📊 **Dashboard Oko Rẹ**",
            'name': "Orukọ",
            'location': "Ipo",
            'soil_type': "Irú Ilẹ̀",
            'farm_size': "Iwọn Oko",
            'tip_header': "💡 **Ìmọ̀ràn Ojoojumọ**",
            'not_linked': "❌ Akọọlẹ rẹ ko ni asopọ. Lo /start lati sopọ.",
            'acres': "acres",
            'welcome_back': "Kaabo pada, {name}! Bawo ni MO ṣe le ran ọ lọwọ loni?\n\nAwọn aṣẹ:\n/dashboard - Wo akopọ oko\n/tip - Gba imọran\n/forecast - Wo aworan asọtẹlẹ oju-ọjọ\n/language - Yi ede pada\n/edit_profile - Ṣe imudojuiwọn data oko",
            'analyzing_photo': "📸 Ṣiṣayẹwo fọto ewe rẹ... jọwọ duro.",
            'no_location': "📍 A ko ṣeto ipo. Jọwọ ṣeto ipo rẹ lori oju opo wẹẹbu lati wo awọn asọtẹlẹ oju-ọjọ.",
            'forecast_title': "Asọtẹlẹ Oju-ọjọ Ọjọ 7",
            'temp': "Ìyípo-òru (°C)",
            'humidity': "Ìmọ̀-ọ̀rin (%)",
            'edit_start': "📝 Jẹ ki a mu profaili oko rẹ dojuiwọn. Nibo ni **ipo** oko rẹ wa? (apejuwe 'Ibadan')",
            'edit_size': "📐 O dara! Kini **iwọn oko** rẹ ni eka? (Kan fi nọmba ranṣẹ)",
            'edit_soil': "🌱 O fẹrẹ pari! Iru **ilẹ** wo ni?",
            'edit_desc': "📝 Bawo ni iwọ yoo ṣe ** ṣapejuwe** ilẹ rẹ? (apejuwe 'Dudu ati ọlọrọ')",
            'edit_done': "✅ O ṣeun! A ti ṣe imudojuiwọn profaili oko rẹ.",
            'cancel': "❌ A ti fagilee imudojuiwọn profaili.",
            'loamy': "Loamy",
            'sandy': "Sandy",
            'clay': "Clay",
            'silty': "Silty",
            'not_sure': "Mi o mọ",
            'select_language': "🌍 **Yan ede ti o fẹ:**",
            'language_changed': "✅ A ti yipada ede si **Èdè Yorùbá**. Gbogbo awọn ifiranṣẹ iwaju yoo wa ni ede Yoruba.",
            'logout_success': "✅ O ti jade kuro ninu akọọlẹ rẹ. A ti yọ akọọlẹ rẹ kuro ninu nkan Telegram yii.",
            'auth_welcome': "Kaabo si FarmBuddy! 🌾\n\nJọwọ yan aṣayan kan lati bẹrẹ:",
            'btn_login': "🔑 Wọle",
            'btn_signup': "📝 Forukọsilẹ",
            'btn_forgot': "❓ Gbagbe ọrọ igbaniwọle",
            'auth_failed': "❌ Orukọ olumulo tabi ọrọ igbaniwọle ko tọ. Jọwọ gbiyanju lẹẹkansii tabi lo /start.",
            'reset_success': "✅ Ntọala ọrọ igbaniwọle ni aṣeyọri! O le wọle bayi pẹlu ọrọ igbaniwọle tuntun rẹ.",
            'reset_failed': "❌ Idahun ko tọ. Atunṣe ọrọ igbaniwọle kuna.",
            'user_not_found': "❌ A ko ri orukọ olumulo.",
            'signup_user': "O dara! Jẹ ki a ṣẹda akọọlẹ rẹ. Orukọ wo ni o fẹ lo?",
            'signup_pass': "Yan **ọrọ igbaniwọle to lagbara** (o kere ju awọn lẹta 6):",
            'signup_name': "Kini **orukọ rẹ ni kikun**?",
            'signup_loc': "Ilu ati ipinlẹ wo ni o ti n ṣe iṣẹ ogbin?",
            'signup_size': "Kini **iwọn oko** rẹ ni eka? (Kan fi nọmba ranṣẹ)",
            'signup_soil': "Iru **ilẹ** wo ni?",
            'signup_pests': "Awọn **kokoro tabi arun** wo ni o maa n ba pade? (apejuwe armyworms, aphids)",
            'signup_lang': "Ede wo ni o fẹ?",
            'user_exists': "❌ Orukọ yii ti wa tẹlẹ. Jọwọ gbiyanju orukọ miiran:",
            'signup_done': "🎉 A ti ṣẹda akọọlẹ rẹ ni aṣeyọri! O le lo FarmBuddy ni bayi.",
            'connect_info': "Lati lo FarmBuddy lori Telegram, o le:\n\n1. Lo bọtini **'Open Telegram'** lori oju opo wẹẹbu 'My Farm'.\n2. **Wọle (Log in)** taara nibi ti o ba ti ni akọọlẹ tẹlẹ.\n3. **Forukọsilẹ (Sign up)** lati ṣẹda akọọlẹ tuntun.",
        }
    }
    labels['pcm'] = labels['en']
    return labels.get(lang, labels['en'])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command for linking accounts."""
    chat_id = update.effective_chat.id
    logger.debug("Received /start command from %s", chat_id)
    
    if context.args:
        token = context.args[0]
        # Use sync helper to link
        name = await sync_to_async(db_link_profile)(token, chat_id)
        if name:
            message = (
                f"🎉 **Account Linked!**\n\n"
                f"Welcome, {name}! 🌾\n"
                f"Your FarmBuddy account is now successfully linked to Telegram.\n\n"
                f"You can now use /dashboard to see your farm summary or just type a question to chat with me!"
            )
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Invalid or expired linking token. Please go to the 'My Farm' page on the website and click 'Open Telegram Bot' again.")
    else:
        # Check if already linked
        info = await sync_to_async(db_get_profile_info)(chat_id)
        if info:
            l = get_localized_labels(info['lang'])
            welcome = l['welcome_back'].format(name=info['username'])
            await update.message.reply_text(welcome)
        else:
            l = get_localized_labels('en')
            keyboard = [
                [InlineKeyboardButton(l['btn_login'],  callback_data='auth_login')],
                [InlineKeyboardButton(l['btn_signup'], callback_data='auth_signup')],
                [InlineKeyboardButton(l['btn_forgot'], callback_data='auth_forgot')],
                [InlineKeyboardButton(l['btn_link'],   callback_data='auth_link')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(l['auth_welcome'], reply_markup=reply_markup, parse_mode='Markdown')

async def onboard_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback after language is selected in /start."""
    query = update.callback_query
    await query.answer()
    
    lang = query.data.replace('onboard_lang_', '')
    context.user_data['pref_lang'] = lang
    l = get_localized_labels(lang)
    
    keyboard = [
        [InlineKeyboardButton(l['btn_login'], callback_data='auth_login')],
        [InlineKeyboardButton(l['btn_signup'], callback_data='auth_signup')],
        [InlineKeyboardButton(l['btn_forgot'], callback_data='auth_forgot')],
        [InlineKeyboardButton(l['btn_link'], callback_data='auth_link')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(l['auth_welcome'], reply_markup=reply_markup)

# PASSWORD RESET FLOW
async def reset_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    l = get_localized_labels('en')
    target = query.message if query else update.message
    await target.reply_text(l['prompt_username'], parse_mode='Markdown')
    return R_USERNAME

async def reset_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    user, profile = await sync_to_async(db_get_profile_by_username)(username)
    
    if not user:
        l = get_localized_labels('en')
        await update.message.reply_text(l['user_not_found'])
        return ConversationHandler.END
    
    context.user_data['reset_user_obj'] = user
    context.user_data['reset_profile_obj'] = profile
    
    l = get_localized_labels(profile.preferred_language or 'en')
    await update.message.reply_text(l['prompt_grandfather'], parse_mode='Markdown')
    return R_ANSWER

async def reset_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    profile = context.user_data.get('reset_profile_obj')
    l = get_localized_labels(profile.preferred_language or 'en')
    
    if profile.security_answer:
        stored = profile.security_answer
        if stored.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
            answer_matches = check_hashed_password(answer.strip().lower(), stored)
        else:
            # Legacy plaintext — compare and migrate
            answer_matches = (answer.strip().lower() == stored.strip().lower())
            if answer_matches:
                await sync_to_async(db_migrate_security_answer)(profile, answer.strip().lower())
        
        if answer_matches:
            await update.message.reply_text(l['prompt_new_password'], parse_mode='Markdown')
            return R_NEW_PASS
        else:
            await update.message.reply_text(l['reset_failed'])
            return ConversationHandler.END
    else:
        await update.message.reply_text(l['reset_failed'])
        return ConversationHandler.END

async def reset_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_pw = update.message.text
    if len(new_pw) < 6:
        await update.message.reply_text("❌ Password too short (min 6 characters). Try again:")
        return R_NEW_PASS
    
    user = context.user_data.get('reset_user_obj')
    profile = context.user_data.get('reset_profile_obj')
    await sync_to_async(db_update_password)(user, new_pw)
    
    l = get_localized_labels(profile.preferred_language or 'en')
    await update.message.reply_text(l['reset_success'])
    return ConversationHandler.END

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explain how to link accounts."""
    chat_id = update.effective_chat.id
    info = await sync_to_async(db_get_profile_info)(chat_id)
    lang = info['lang'] if info else 'en'
    l = get_localized_labels(lang)
    
    await update.message.reply_text(l['connect_info'], parse_mode='Markdown')

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /logout command."""
    chat_id = update.effective_chat.id
    info = await sync_to_async(db_get_profile_info)(chat_id)
    if info:
        l = get_localized_labels(info['lang'])
        await sync_to_async(db_unlink_chat)(chat_id)
        await update.message.reply_text(l['logout_success'])
    else:
        await update.message.reply_text("❌ You are not logged in.")

# --- AUTH CONVERSATIONS ---
L_USERNAME, L_PASSWORD = range(10, 12)
S_USERNAME, S_PASSWORD, S_GRANDFATHER, S_NAME, S_LOCATION, S_ACRES, S_SOIL, S_PESTS, S_LANGUAGE = range(20, 29)
R_USERNAME, R_ANSWER, R_NEW_PASS = range(30, 33)

# LOGIN FLOW
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    # We can't easily detect language here yet, so default to EN prompt or check context
    l = get_localized_labels('en')
    target = query.message if query else update.message
    await target.reply_text(l['prompt_username'], parse_mode='Markdown')
    return L_USERNAME

async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['auth_username'] = update.message.text
    l = get_localized_labels('en')
    await update.message.reply_text(l['prompt_password'], parse_mode='Markdown')
    return L_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get('auth_username')
    password = update.message.text
    chat_id = update.effective_chat.id
    
    user = await sync_to_async(db_authenticate_user)(username, password)
    if user:
        profile = await sync_to_async(db_link_user_by_id)(user.id, chat_id)
        l = get_localized_labels(profile.preferred_language if profile else 'en')
        await update.message.reply_text(l['auth_success'].format(name=user.first_name or user.username))
        return ConversationHandler.END
    else:
        l = get_localized_labels('en')
        await update.message.reply_text(l['auth_failed'])
        return ConversationHandler.END

# SIGNUP FLOW
async def signup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    l = get_localized_labels('en')
    target = query.message if query else update.message
    await target.reply_text(l['signup_user'], parse_mode='Markdown')
    return S_USERNAME

async def signup_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    exists = await sync_to_async(db_check_username)(username)
    l = get_localized_labels('en')
    
    if exists:
        await update.message.reply_text(l['user_exists'])
        return S_USERNAME
    
    context.user_data['su_username'] = username
    await update.message.reply_text(l['signup_pass'], parse_mode='Markdown')
    return S_PASSWORD
async def signup_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    if len(password) < 6:
        await update.message.reply_text("❌ Password too short. Please enter at least 6 characters:")
        return S_PASSWORD
    
    context.user_data['su_password'] = password
    l = get_localized_labels('en')
    await update.message.reply_text(l['prompt_grandfather'], parse_mode='Markdown')
    return S_GRANDFATHER

async def signup_grandfather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['su_grandfather'] = update.message.text
    l = get_localized_labels('en')
    await update.message.reply_text(l['signup_name'], parse_mode='Markdown')
    return S_NAME

async def signup_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['su_name'] = update.message.text
    l = get_localized_labels('en')
    await update.message.reply_text(l['signup_loc'], parse_mode='Markdown')
    return S_LOCATION

async def signup_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['su_loc'] = update.message.text
    l = get_localized_labels('en')
    await update.message.reply_text(l['signup_size'], parse_mode='Markdown')
    return S_ACRES

async def signup_acres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['su_acres'] = float(update.message.text)
    except ValueError:
        context.user_data['su_acres'] = 0
    
    l = get_localized_labels('en')
    # Soil type keyboard
    keyboard = [
        [InlineKeyboardButton(l['loamy'], callback_data='su_soil_loamy'), InlineKeyboardButton(l['sandy'], callback_data='su_soil_sandy')],
        [InlineKeyboardButton(l['clay'], callback_data='su_soil_clay'), InlineKeyboardButton(l['silty'], callback_data='su_soil_silty')],
        [InlineKeyboardButton(l['not_sure'], callback_data='su_soil_unknown')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(l['signup_soil'], reply_markup=reply_markup)
    return S_SOIL

async def signup_soil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    soil_choice = query.data.replace('su_soil_', '')
    context.user_data['su_soil'] = soil_choice
    
    l = get_localized_labels('en')
    await query.edit_message_text(f"Selected Soil: {soil_choice.capitalize()}")
    await context.bot.send_message(update.effective_chat.id, l['signup_pests'], parse_mode='Markdown')
    return S_PESTS

async def signup_pests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['su_pests'] = update.message.text
    chat_id = update.effective_chat.id
    l = get_localized_labels('en')

    data = context.user_data
    user, profile = await sync_to_async(db_register_user)(
        data['su_username'],
        data['su_password'],
        data['su_name'],
        data['su_loc'],
        'en',
        acres=data.get('su_acres', 0),
        soil=data.get('su_soil', 'unknown'),
        pests=data.get('su_pests', ''),
        security_answer=data.get('su_grandfather', '')
    )

    if user:
        await sync_to_async(db_link_user_by_id)(user.id, chat_id)
        await update.message.reply_text(
            l['signup_done'] + "\n\nYou can change your language anytime with /language.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Signup failed. Please try again with /start.")

    return ConversationHandler.END

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show farm summary."""
    chat_id = update.effective_chat.id
    info = await sync_to_async(db_get_profile_info)(chat_id)
    if info:
        l = get_localized_labels(info['lang'])
        text = (
            f"{l['dash_header']}\n\n"
            f"👤 **{l['name']}**: {info['username']}\n"
            f"📍 **{l['location']}**: {info['location']}\n"
            f"🌱 **{l['soil_type']}**: {info['soil_display']}\n"
            f"📐 **{l['farm_size']}**: {info['farm_size']} {l['acres']}\n"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Account not linked. Use /start with the token from the website.")

async def tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show daily agricultural tip."""
    chat_id = update.effective_chat.id
    info = await sync_to_async(db_get_profile_info)(chat_id)
    if info:
        l = get_localized_labels(info['lang'])
        from accounts.views import TIPS
        tip_text = TIPS.get(info['lang'], TIPS['en'])
        await update.message.reply_text(f"{l['tip_header']}\n\n{tip_text}", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Account not linked.")

def _build_forecast_image(forecast_data, city_name, lang_labels):
    """Build a two-panel forecast chart: temperature top, humidity+rain bottom."""
    BG      = '#0d1117'
    PANEL   = '#161b22'
    BORDER  = '#30363d'
    TEXT    = '#e6edf3'
    SUBTEXT = '#8b949e'

    C_TEMP  = '#f97316'   # orange  – avg temperature line
    C_HIGH  = '#fbbf24'   # amber   – daily high tick marks
    C_LOW   = '#60a5fa'   # blue    – daily low tick marks
    C_HUM   = '#34d399'   # emerald – humidity bars
    C_RAIN  = '#818cf8'   # indigo  – rain probability bars

    # --- Parse 3-hour intervals into daily summaries ---
    daily = {}
    for entry in forecast_data.get('list', []):
        d = entry['dt_txt'].split(' ')[0]
        if d not in daily:
            daily[d] = {'temps': [], 'hum': [], 'rain': []}
        daily[d]['temps'].append(entry['main']['temp'])
        daily[d]['hum'].append(entry['main']['humidity'])
        daily[d]['rain'].append(entry.get('pop', 0) * 100)

    dates = sorted(daily.keys())[:5]
    if not dates:
        raise ValueError("No forecast data returned")

    labels   = [datetime.strptime(d, "%Y-%m-%d").strftime("%a\n%d %b") for d in dates]
    avg_temp = [round(sum(daily[d]['temps']) / len(daily[d]['temps']), 1) for d in dates]
    max_temp = [round(max(daily[d]['temps']), 1) for d in dates]
    min_temp = [round(min(daily[d]['temps']), 1) for d in dates]
    avg_hum  = [round(sum(daily[d]['hum'])   / len(daily[d]['hum']),   1) for d in dates]
    avg_rain = [round(sum(daily[d]['rain'])  / len(daily[d]['rain']),  1) for d in dates]

    x     = np.arange(len(labels))
    bar_w = 0.5

    # --- Two-panel figure ---
    fig, (ax_t, ax_b) = plt.subplots(
        2, 1, figsize=(9, 7),
        gridspec_kw={'height_ratios': [3, 2], 'hspace': 0.08}
    )
    fig.patch.set_facecolor(BG)
    for ax in (ax_t, ax_b):
        ax.set_facecolor(PANEL)
        ax.set_xticks(x)
        ax.tick_params(colors=SUBTEXT, length=0)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.grid(axis='y', color=BORDER, linestyle='--', alpha=0.45, zorder=1)

    # ── TOP: Temperature ──────────────────────────────────────────────────────
    # Shaded high-low band
    ax_t.fill_between(x, min_temp, max_temp, color=C_TEMP, alpha=0.10, zorder=2)

    # High / low tick bars
    for i in range(len(x)):
        ax_t.plot([x[i], x[i]], [min_temp[i], max_temp[i]],
                  color=BORDER, linewidth=1.2, zorder=3)
        ax_t.plot(x[i], max_temp[i], marker='^', color=C_HIGH,
                  markersize=7, zorder=4)
        ax_t.plot(x[i], min_temp[i], marker='v', color=C_LOW,
                  markersize=7, zorder=4)

    # Average temp line
    ax_t.plot(x, avg_temp, color=C_TEMP, linewidth=2.4, marker='o',
              markersize=8, markerfacecolor=C_TEMP, markeredgecolor=BG,
              markeredgewidth=1.5, zorder=5, label='Avg temp')

    # Labels above/below markers
    t_pad = (max(max_temp) - min(min_temp)) * 0.07 or 1
    for i, (avg, hi, lo) in enumerate(zip(avg_temp, max_temp, min_temp)):
        ax_t.annotate(f"{avg:.0f}°", (x[i], avg),
                      textcoords="offset points", xytext=(0, 10),
                      ha='center', fontsize=9, color=C_TEMP, fontweight='bold')
        ax_t.annotate(f"↑{hi:.0f}°", (x[i], hi),
                      textcoords="offset points", xytext=(12, 0),
                      ha='left', fontsize=7.5, color=C_HIGH)
        ax_t.annotate(f"↓{lo:.0f}°", (x[i], lo),
                      textcoords="offset points", xytext=(12, 0),
                      ha='left', fontsize=7.5, color=C_LOW)

    temp_margin = max(3, (max(max_temp) - min(min_temp)) * 0.3)
    ax_t.set_ylim(min(min_temp) - temp_margin, max(max_temp) + temp_margin + 3)
    ax_t.set_xticklabels([])   # shared with bottom panel
    ax_t.set_ylabel('Temperature (°C)', color=SUBTEXT, fontsize=9)
    ax_t.tick_params(axis='y', colors=SUBTEXT, labelsize=8)

    legend_handles = [
        mpatches.Patch(color=C_TEMP,  label='Avg temp (°C)'),
        mpatches.Patch(color=C_HIGH,  label='Daily high'),
        mpatches.Patch(color=C_LOW,   label='Daily low'),
    ]
    ax_t.legend(handles=legend_handles, loc='upper right', fontsize=8,
                facecolor='#0d1117', edgecolor=BORDER, labelcolor=TEXT,
                framealpha=0.9, ncol=3)

    ax_t.set_title(f"🌾  5-Day Forecast  ·  {city_name}",
                   color=TEXT, fontsize=13, fontweight='bold', pad=10, loc='left')

    # ── BOTTOM: Humidity & Rain ───────────────────────────────────────────────
    w = bar_w / 2
    bars_h = ax_b.bar(x - w/2, avg_hum,  width=w, color=C_HUM,  alpha=0.85,
                      zorder=3, label='Humidity (%)')
    bars_r = ax_b.bar(x + w/2, avg_rain, width=w, color=C_RAIN, alpha=0.85,
                      zorder=3, label='Rain chance (%)')

    # Value labels on bars
    for bar, val in zip(bars_h, avg_hum):
        if val > 0:
            ax_b.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                      f"{val:.0f}%", ha='center', va='bottom',
                      fontsize=7.5, color=C_HUM, fontweight='bold')
    for bar, val in zip(bars_r, avg_rain):
        if val > 0:
            ax_b.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                      f"{val:.0f}%", ha='center', va='bottom',
                      fontsize=7.5, color=C_RAIN, fontweight='bold')

    ax_b.set_ylim(0, 110)
    ax_b.set_xticklabels(labels, fontsize=9, color=SUBTEXT)
    ax_b.tick_params(axis='y', colors=SUBTEXT, labelsize=8)
    ax_b.set_ylabel('Percent (%)', color=SUBTEXT, fontsize=9)
    ax_b.legend(loc='upper right', fontsize=8,
                facecolor='#0d1117', edgecolor=BORDER, labelcolor=TEXT,
                framealpha=0.9)

    fig.text(0.99, 0.005, 'Data: OpenWeatherMap', ha='right', va='bottom',
             fontsize=7, color='#484f58')

    plt.tight_layout(pad=1.2)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=140, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf


async def forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch real weather data and send a styled 5-day forecast chart."""
    chat_id = update.effective_chat.id
    try:
        info = await sync_to_async(db_get_profile_info)(chat_id)
        if not info:
            await update.message.reply_text(
                "❌ Account not linked. Use /start with your token from the FarmBuddy website."
            )
            return

        location = info.get('location', '').strip()
        if not location:
            await update.message.reply_text(
                "📍 No location set on your profile. Update your location on the FarmBuddy website, then try again."
            )
            return

        city_name = location.split(',')[0].strip()
        await update.message.chat.send_action("upload_photo")

        forecast_data = await sync_to_async(get_forecast_by_city)(city_name)

        if 'error' in forecast_data:
            await update.message.reply_text(
                f"⚠️ Could not fetch weather for *{city_name}*: {forecast_data['error']}\n\n"
                "Make sure your profile location matches a real city name.",
                parse_mode='Markdown'
            )
            return

        l = get_localized_labels(info['lang'])
        buf = await sync_to_async(_build_forecast_image)(forecast_data, city_name, l)
        await update.message.reply_photo(photo=buf, caption=f"📍 {location}")

    except Exception as e:
        logger.exception("forecast error")
        await update.message.reply_text(f"❌ Error generating forecast: {str(e)}")

async def language_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection keyboard."""
    chat_id = update.effective_chat.id
    info = await sync_to_async(db_get_profile_info)(chat_id)
    if info:
        l = get_localized_labels(info['lang'])
        keyboard = [
            [InlineKeyboardButton("English 🇬🇧", callback_data='lang_en'), InlineKeyboardButton("Hausa 🇳🇬", callback_data='lang_ha')],
            [InlineKeyboardButton("Igbo 🇳🇬", callback_data='lang_ig'), InlineKeyboardButton("Yoruba 🇳🇬", callback_data='lang_yo')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(l['select_language'], reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Account not linked. Use /start to link.")

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process language selection callback."""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    lang_choice = query.data.replace('lang_', '')
    
    # Update DB
    await sync_to_async(db_update_profile)(chat_id, preferred_language=lang_choice)
    
    # Get new labels
    l = get_localized_labels(lang_choice)
    
    await query.edit_message_text(l['language_changed'], parse_mode='Markdown')

# --- HANDLERS ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages using Gemini."""
    chat_id = update.effective_chat.id
    user_text = update.message.text
    logger.debug("Received message from %s: %s...", chat_id, user_text[:20])
    
    info = await sync_to_async(db_get_profile_info)(chat_id)
    if info:
        user = info['user_obj']
        profile = info['profile_obj']
        lang = info['lang']
        
        # Get profile context for AI
        profile_context = await sync_to_async(profile.to_context_string)()
        
        # 1. Sync to DB
        conv = await sync_to_async(db_get_or_create_conv)(user)
        await sync_to_async(db_save_msg)(conv, 'user', user_text)
        
        # 2. Get history (last 10)
        history = await sync_to_async(db_get_history)(conv)
        
        # 3. Ask Gemini with profile context
        await update.message.chat.send_action("typing")
        response_text = await sync_to_async(ask_gemini)(history, profile_context=profile_context, language=lang)
        
        # 4. Save Assistant reply
        await sync_to_async(db_save_msg)(conv, 'assistant', response_text)
        
        # 5. Reply to User
        await update.message.reply_text(response_text, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Your account is not linked. Please use /start with your token from the FarmBuddy website.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leaf photo uploads for diagnosis."""
    chat_id = update.effective_chat.id
    logger.debug("Received photo from %s", chat_id)
    try:
        info = await sync_to_async(db_get_profile_info)(chat_id)
        if info:
            user = info['user_obj']
            lang = info['lang']
            l = get_localized_labels(lang)
            
            # Download photo
            photo_file = await update.message.photo[-1].get_file()
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                await photo_file.download_to_drive(tmp.name)
                tmp_path = tmp.name
            
            await update.message.reply_text(l['analyzing_photo'])
            await update.message.chat.send_action("upload_photo")
            
            # Analyze using Gemini Vision
            analysis_result = analyze_plant_image(tmp_path)
            
            # Clean up
            import os
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
            # Sync to DB
            conv = await sync_to_async(db_get_or_create_conv)(user)
            await sync_to_async(db_save_msg)(conv, 'user', "[Uploaded a leaf photo for diagnosis]")
            await sync_to_async(db_save_msg)(conv, 'assistant', analysis_result)
            
            await update.message.reply_text(analysis_result, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Account not linked.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error analyzing photo: {str(e)}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice notes using Gemini's multi-modal capabilities."""
    chat_id = update.effective_chat.id
    print(f"DEBUG: Received voice from {chat_id}", flush=True)
    try:
        info = await sync_to_async(db_get_profile_info)(chat_id)
        if info:
            user = info['user_obj']
            lang = info['lang']
            l = get_localized_labels(lang)
            
            # Download voice note
            voice_file = await update.message.voice.get_file()
            
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
                await voice_file.download_to_drive(tmp.name)
                tmp_path = tmp.name
            
            # We can actually use Gemini to "transcribe and answer" at once
            await update.message.reply_text("🎧 Listening to your voice message...")
            await update.message.chat.send_action("record_voice")
            
            # Upload to Gemini
            try:
                # For simplicity, we'll use genai.upload_file
                import google.generativeai as genai
                mime_type = "audio/ogg"
                audio_part = genai.upload_file(path=tmp_path, mime_type=mime_type)
                
                # 1. Sync User part
                conv = await sync_to_async(db_get_or_create_conv)(user)
                await sync_to_async(db_save_msg)(conv, 'user', "[Sent a voice note]")
                
                # 2. Ask Gemini
                prompt = f"Listen to this audio and respond in {lang} language. Personalize for a Nigerian farmer."
                response = model.generate_content([prompt, audio_part])
                response_text = response.text.strip()
                
                # 3. Save Assistant reply
                await sync_to_async(db_save_msg)(conv, 'assistant', response_text)
                
                # 4. Reply
                await update.message.reply_text(response_text, parse_mode='Markdown')
            finally:
                import os
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            await update.message.reply_text("❌ Account not linked.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing voice: {str(e)}")

# Profile Edit Conversation States
LOCATION, SIZE, SOIL_TYPE, SOIL_DESC = range(4)

async def edit_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the profile edit flow."""
    chat_id = update.effective_chat.id
    info = await sync_to_async(db_get_profile_info)(chat_id)
    if info:
        l = get_localized_labels(info['lang'])
        await update.message.reply_text(l['edit_start'])
        return LOCATION
    else:
        await update.message.reply_text("❌ Account not linked.")
        return ConversationHandler.END

async def edit_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save location and ask for size."""
    chat_id = update.effective_chat.id
    location = update.message.text
    
    await sync_to_async(db_update_profile)(chat_id, location=location)
    
    info = await sync_to_async(db_get_profile_info)(chat_id)
    l = get_localized_labels(info['lang'])
    
    await update.message.reply_text(l['edit_size'])
    return SIZE

async def edit_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save size and ask for soil type."""
    chat_id = update.effective_chat.id
    size_text = update.message.text
    
    try:
        size_val = float(size_text)
        await sync_to_async(db_update_profile)(chat_id, farm_size_acres=size_val)
    except ValueError:
        pass
    
    info = await sync_to_async(db_get_profile_info)(chat_id)
    l = get_localized_labels(info['lang'])
    
    # Soil type keyboard
    keyboard = [
        [InlineKeyboardButton(l['loamy'], callback_data='loamy'), InlineKeyboardButton(l['sandy'], callback_data='sandy')],
        [InlineKeyboardButton(l['clay'], callback_data='clay'), InlineKeyboardButton(l['silty'], callback_data='silty')],
        [InlineKeyboardButton(l['not_sure'], callback_data='not_sure')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(l['edit_soil'], reply_markup=reply_markup)
    return SOIL_TYPE

async def edit_soil_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save soil type and ask for description."""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    soil_choice = query.data
    
    await sync_to_async(db_update_profile)(chat_id, soil_type=soil_choice)
    
    info = await sync_to_async(db_get_profile_info)(chat_id)
    l = get_localized_labels(info['lang'])
    
    await query.edit_message_text(f"Selected: {soil_choice.capitalize()}")
    await context.bot.send_message(chat_id, l['edit_desc'])
    return SOIL_DESC

async def edit_soil_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save description and end flow."""
    chat_id = update.effective_chat.id
    desc = update.message.text
    
    await sync_to_async(db_update_profile)(chat_id, ph_level=desc)
    
    info = await sync_to_async(db_get_profile_info)(chat_id)
    l = get_localized_labels(info['lang'])
    
    await update.message.reply_text(l['edit_done'], reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel flow."""
    chat_id = update.effective_chat.id
    info = await sync_to_async(db_get_profile_info)(chat_id)
    if info:
        l = get_localized_labels(info['lang'])
        await update.message.reply_text(l['cancel'], reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

from asgiref.sync import sync_to_async

def run_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    # Create a custom request with longer timeout to prevent ConnectTimeout issues
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    
    print("Initializing FarmBuddy Bot...", flush=True)

    async def post_init(application):
        await application.bot.set_my_commands([
            BotCommand("start", "Login or Sign up"),
            BotCommand("language", "Select Preferred Language"),
            BotCommand("dashboard", "Farm Summary"),
            BotCommand("edit_profile", "Interactive Profile Update"),
            BotCommand("tip", "Daily Tip"),
            BotCommand("forecast", "Get weather forecast for the next 7 days"),
            BotCommand("connect", "Link web profile to Telegram"),
            BotCommand("signup", "Create an account on FarmBuddy"),
            BotCommand("login", "Login to your FarmBuddy account"),
            BotCommand("logout", "Exit your FarmBuddy account"),
            BotCommand("cancel", "Cancel any active process"),
        ])
        print("Bot commands registered.", flush=True)

    application = ApplicationBuilder().token(token).request(request).post_init(post_init).build()

    async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.exception("Unhandled exception in bot handler", exc_info=context.error)
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text("❌ Something went wrong. Please try again in a moment.")
            except Exception:
                pass

    application.add_error_handler(global_error_handler)

    async def global_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat:
            print(f"DEBUG: GLOBAL UPDATE from {update.effective_chat.id} - Type: {update.message.text if update.message else 'Not Text'}", flush=True)

    # Add a low-priority handler to log everything
    application.add_handler(MessageHandler(filters.ALL, global_debug), group=-1)
    
    start_handler = CommandHandler('start', start)
    dash_handler = CommandHandler('dashboard', dashboard)
    tip_handler = CommandHandler('tip', tip)
    logout_handler = CommandHandler('logout', logout)
    forecast_handler = CommandHandler('forecast', forecast)
    lang_handler = CommandHandler('language', language_select)
    connect_handler = CommandHandler('connect', connect)
    lang_cb_handler = CallbackQueryHandler(language_callback, pattern='^lang_')
    
    # Login Conversation
    login_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('login', login_start),
            CallbackQueryHandler(login_start, pattern='^auth_login$')
        ],
        states={
            L_USERNAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), login_username)],
            L_PASSWORD: [MessageHandler(filters.TEXT & (~filters.COMMAND), login_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="login_conv",
        persistent=False
    )

    # Signup Conversation
    signup_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('signup', signup_start),
            CallbackQueryHandler(signup_start, pattern='^auth_signup$')
        ],
        states={
            S_USERNAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), signup_username)],
            S_PASSWORD: [MessageHandler(filters.TEXT & (~filters.COMMAND), signup_password)],
            S_GRANDFATHER: [MessageHandler(filters.TEXT & (~filters.COMMAND), signup_grandfather)],
            S_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), signup_name)],
            S_LOCATION: [MessageHandler(filters.TEXT & (~filters.COMMAND), signup_location)],
            S_ACRES: [MessageHandler(filters.TEXT & (~filters.COMMAND), signup_acres)],
            S_SOIL: [CallbackQueryHandler(signup_soil, pattern='^su_soil_')],
            S_PESTS: [MessageHandler(filters.TEXT & (~filters.COMMAND), signup_pests)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="signup_conv",
        persistent=False
    )
    
    # Reset Conversation
    reset_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('forgot', reset_start),
            CallbackQueryHandler(reset_start, pattern='^auth_forgot$')
        ],
        states={
            R_USERNAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), reset_username)],
            R_ANSWER: [MessageHandler(filters.TEXT & (~filters.COMMAND), reset_answer)],
            R_NEW_PASS: [MessageHandler(filters.TEXT & (~filters.COMMAND), reset_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="reset_conv",
        persistent=False
    )
    
    link_info_handler = CallbackQueryHandler(connect, pattern='^auth_link$')

    # Edit Profile Conversation
    edit_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('edit_profile', edit_profile_start)],
        states={
            LOCATION: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_location)],
            SIZE: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_size)],
            SOIL_TYPE: [CallbackQueryHandler(edit_soil_type)],
            SOIL_DESC: [MessageHandler(filters.TEXT & (~filters.COMMAND), edit_soil_desc)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    photo_handler = MessageHandler(filters.PHOTO, handle_photo)
    voice_handler = MessageHandler(filters.VOICE, handle_voice)
    
    application.add_handler(start_handler)
    application.add_handler(dash_handler)
    application.add_handler(tip_handler)
    application.add_handler(logout_handler)
    application.add_handler(forecast_handler)
    application.add_handler(lang_handler)
    application.add_handler(connect_handler)
    application.add_handler(lang_cb_handler)
    application.add_handler(link_info_handler)
    
    application.add_handler(login_conv_handler)
    application.add_handler(signup_conv_handler)
    application.add_handler(reset_conv_handler)
    application.add_handler(edit_conv_handler)
    application.add_handler(message_handler)
    application.add_handler(photo_handler)
    application.add_handler(voice_handler)
    
    import time
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            print(f"FarmBuddy Bot is polling (Attempt {attempt + 1})...", flush=True)
            # Connectivity confirmed in previous diagnostic run
            application.run_polling(close_loop=False)
            break
        except Exception as e:
            print(f"Bot encountered an error: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Bot is shutting down.")

if __name__ == '__main__':
    run_bot()
