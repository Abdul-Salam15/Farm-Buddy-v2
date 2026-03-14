from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class FarmerProfile(models.Model):
    SOIL_CHOICES = [
        ('sandy', 'Sandy'),
        ('loamy', 'Loamy'),
        ('clay', 'Clay'),
        ('silt', 'Silty'),
        ('peaty', 'Peaty'),
        ('chalky', 'Chalky'),
        ('unknown', 'I am not sure'),
    ]

    PH_CHOICES = [
        ('acidic', 'Acidic  (tastes sour, kills grass)'),
        ('neutral', 'Neutral (normal soil)'),
        ('alkaline', 'Alkaline (white crust on soil surface)'),
        ('unknown', 'I am not sure'),
    ]

    WATER_CHOICES = [
        ('rainfed', 'Rainfed only'),
        ('irrigated', 'I have irrigation'),
        ('seasonal', 'Seasonal stream / borehole'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ha', 'Hausa'),
        ('ig', 'Igbo'),
        ('yo', 'Yoruba'),
        ('pcm', 'Pidgin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True, help_text='Town, state or region')
    farm_size_acres = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)])
    soil_type = models.CharField(max_length=20, choices=SOIL_CHOICES, default='unknown')
    ph_level = models.CharField(max_length=20, choices=PH_CHOICES, default='unknown')
    water_source = models.CharField(max_length=20, choices=WATER_CHOICES, default='rainfed')
    current_crops = models.TextField(blank=True, help_text='Comma separated, e.g. maize, cassava')
    past_crops = models.TextField(blank=True, help_text='What have you grown before?')
    top_pests = models.TextField(blank=True, help_text='Pests usually encountered (e.g. armyworms, aphids)')
    has_livestock = models.BooleanField(default=False)
    livestock_types = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Security Settings
    security_answer = models.CharField(max_length=200, blank=True, help_text="Answer to security question (grandfather's name)")

    # Telegram Integration
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_link_token = models.CharField(max_length=64, null=True, blank=True, unique=True)

    def get_or_create_link_token(self):
        if not self.telegram_link_token:
            import secrets
            self.telegram_link_token = secrets.token_hex(16)
            self.save()
        return self.telegram_link_token

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def to_context_string(self):
        return (
            f'Farmer name: {self.first_name} {self.last_name}\n'
            f'Location: {self.location}\n'
            f'Farm size: {self.farm_size_acres} acres\n'
            f'Soil type: {self.get_soil_type_display()}\n'
            f'Soil pH: {self.get_ph_level_display()}\n'
            f'Water source: {self.get_water_source_display()}\n'
            f'Current crops: {self.current_crops or "Not specified"}\n'
            f'Main Pests: {self.top_pests or "Not specified"}\n'
            f'Previous crops: {self.past_crops or "Not specified"}\n'
            f'Livestock: {self.livestock_types or "None"}'
        )
