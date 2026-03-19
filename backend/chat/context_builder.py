from .models import Conversation, Message
from accounts.models import FarmerProfile


def build_system_prompt(user):
    """Build a plain-text system prompt from the user's FarmerProfile and recent assistant messages."""
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

    system_prompt = f"""
You are FarmBuddy, a friendly and knowledgeable agricultural assistant
for smallholder farmers in Nigeria and West Africa.

FARMER PROFILE:

{profile_text}

{history_text}

INSTRUCTIONS:

1. Always tailor your advice to the farmer's specific soil type, location,
   water source and crops listed above.

2. When your answer is informed by the farmer's profile or a past conversation,
   end your response with a section formatted EXACTLY like this:

   [FARMBUDDY_REFS]
   - PROFILE:soil_type — Because your soil is loamy, I recommended...
   - HISTORY:Past-2 — Based on our earlier discussion about maize pests...
   [/FARMBUDDY_REFS]

3. If no profile or history is relevant, omit the [FARMBUDDY_REFS] section.
4. Keep language simple. Avoid jargon. Speak as a trusted advisor would.
5. If the farmer is using voice, keep responses concise (under 120 words).
"""

    return system_prompt


def parse_xai_refs(response_text):
    """Extract the [FARMBUDDY_REFS] block from the AI response.

    Returns (clean_text, refs_list) where refs_list is a list of dicts:
      {'type': 'profile'|'history', 'key': 'soil_type'|'Past-1', 'explanation': '...'}
    """
    refs = []
    if '[FARMBUDDY_REFS]' not in response_text:
        return response_text, refs

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

    return clean_text, refs
