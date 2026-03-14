from accounts.models import FarmerProfile


def user_language(request):
    """Inject the user's preferred language into every template context."""
    lang = 'en'
    if request.user.is_authenticated:
        profile = FarmerProfile.objects.filter(user=request.user).first()
        if profile:
            lang = profile.preferred_language
    return {'user_lang': lang}
