from .models import Conversation, Message
from accounts.models import FarmerProfile


def build_profile_context(user):
    """Plain-text farmer profile + recent conversation history, with no
    format/instructions block. Shared by both the text-chat and image-
    analysis flows, each of which layers its own instructions on top."""
    try:
        profile = user.farmerprofile
        profile_text = profile.to_context_string()
    except FarmerProfile.DoesNotExist:
        profile_text = 'No farm profile available.'

    # Fetch the last 10 assistant messages across the user's conversations
    past = (
        Message.objects
        .filter(conversation__user=user, role='assistant')
        .order_by('-created_at')[:5]
    )

    history_text = ''
    if past:
        history_text = '\n\nRELEVANT PAST CONVERSATIONS:\n'
        for i, msg in enumerate(reversed(list(past)), 1):
            history_text += f'[Past-{i}] {msg.content[:300]}\n'

    return f"""FARMER PROFILE:

{profile_text}

{history_text}"""


def build_system_prompt(user):
    """Build the full text-chat system prompt: persona + farmer profile +
    [FARMBUDDY_REFS] citation instructions."""
    profile_context = build_profile_context(user)

    system_prompt = f"""
You are FarmBuddy, a friendly and knowledgeable agricultural assistant
for smallholder farmers in Nigeria and West Africa.

{profile_context}

INSTRUCTIONS:

1. Always tailor your advice to the farmer's specific soil type, location,
   water source and crops listed above.

2. EVERY response MUST end with a [FARMBUDDY_REFS] ... [/FARMBUDDY_REFS]
   block citing where the information came from. This is mandatory — never
   omit it, even for greetings or small talk.

   Use one or more of these reference types, with the exact format
   "TYPE:KEY — explanation" (em-dash, not hyphen):

   - PROFILE:<field_key> — when you used the farmer's profile. The field_key
     MUST match a row from the FARMER PROFILE above. Valid keys include:
     first_name, last_name, location, farm_size_acres, soil_type, ph_level,
     water_source, current_crops, past_crops, top_pests, livestock_types.
   - HISTORY:Past-N — when you referenced a past conversation (Past-1, Past-2, ...).
   - WEATHER:OpenWeatherMap — when weather data informed the answer.
   - KNOWLEDGE:general — fallback for greetings, small talk, or general
     agricultural advice not tied to the profile, history, or weather.

   Concrete examples:

   [FARMBUDDY_REFS]
   - PROFILE:location — Your farm is in Ibadan, as stored in your profile.
   - PROFILE:soil_type — Because your soil is loamy, I recommended...
   - HISTORY:Past-2 — Based on our earlier discussion about maize pests...
   - WEATHER:OpenWeatherMap — Live forecast shows rain on Thursday.
   - KNOWLEDGE:general — Standard agronomy advice for transplanting seedlings.
   [/FARMBUDDY_REFS]

   Include EVERY source you actually used. If nothing else applies (e.g. a
   greeting like "hello"), still emit the block with a single
   KNOWLEDGE:general line.

3. Keep language simple. Avoid jargon. Speak as a trusted advisor would.
4. If the farmer is using voice, keep responses concise (under 120 words),
   but still include the [FARMBUDDY_REFS] block.
"""

    return system_prompt


_DEFAULT_KNOWLEDGE_REF = {
    'type': 'knowledge',
    'key': 'general',
    'explanation': 'General agricultural knowledge.'
}


def parse_xai_refs(response_text):
    """Extract the [FARMBUDDY_REFS] block from the AI response.

    Returns (clean_text, refs_list) where refs_list is a list of dicts:
      {'type': 'profile'|'history'|'weather'|'image'|'knowledge',
       'key': 'soil_type'|'Past-1'|'OpenWeatherMap'|...,
       'explanation': '...'}

    If the model omitted the block or it parsed to nothing, returns a single
    fallback knowledge ref so the UI always shows a Sources & Context section.
    """
    refs = []
    clean_text = response_text

    if '[FARMBUDDY_REFS]' in response_text and '[/FARMBUDDY_REFS]' in response_text:
        parts = response_text.split('[FARMBUDDY_REFS]')
        clean_text = parts[0].strip()
        ref_block = parts[1].split('[/FARMBUDDY_REFS]')[0]

        for line in ref_block.strip().splitlines():
            line = line.strip().lstrip('- ').strip()
            if not line or ':' not in line:
                continue
            # Split on first '—' em-dash if present to get explanation
            if '—' in line:
                left, explanation = line.split('—', 1)
            else:
                left, explanation = line, ''
            ref_type_key = left.strip()
            if ':' in ref_type_key:
                ref_type, ref_key = ref_type_key.split(':', 1)
            else:
                ref_type, ref_key = ('unknown', ref_type_key)
            refs.append({
                'type': ref_type.strip().lower(),
                'key': ref_key.strip(),
                'explanation': explanation.strip()
            })

    if not refs:
        refs = [dict(_DEFAULT_KNOWLEDGE_REF)]

    return clean_text, refs
