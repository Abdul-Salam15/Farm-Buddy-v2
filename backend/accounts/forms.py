from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import FarmerProfile


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email


class FarmerProfileForm(forms.ModelForm):
    class Meta:
        model = FarmerProfile
        exclude = ['user', 'created_at', 'updated_at']
        labels = {
            'first_name': 'First name',
            'last_name': 'Last name',
            'location': 'Where is your farm? (town, state)',
            'farm_size_acres': 'Farm size in acres (leave blank if unsure)',
            'soil_type': 'What does your soil look like?',
            'ph_level': 'How would you describe your soil?',
            'water_source': 'How do you water your crops?',
            'current_crops': 'What are you growing now?',
            'past_crops': 'What have you grown before?',
            'has_livestock': 'Do you keep animals?',
            'livestock_types': 'What animals? (e.g. goats, chickens)',
        }
        widgets = {
            'current_crops': forms.TextInput(attrs={'placeholder': 'e.g. maize, tomatoes, groundnuts'}),
            'past_crops': forms.TextInput(attrs={'placeholder': 'e.g. cassava, yam'}),
            'has_livestock': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
            'livestock_types': forms.TextInput(attrs={'placeholder': 'e.g. goats, chickens'}),
        }


class UserSettingsForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False, label="First Name")
    last_name = forms.CharField(max_length=150, required=False, label="Last Name")
    preferred_language = forms.ChoiceField(choices=FarmerProfile.LANGUAGE_CHOICES, required=True, label="Default Language")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(UserSettingsForm, self).__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            try:
                self.fields['preferred_language'].initial = self.user.farmerprofile.preferred_language
            except FarmerProfile.DoesNotExist:
                pass

    def save(self):
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.save()

            # Use update_or_create to avoid IntegrityError on required fields for new users
            FarmerProfile.objects.update_or_create(
                user=self.user,
                defaults={
                    'first_name': self.cleaned_data['first_name'],
                    'last_name': self.cleaned_data['last_name'],
                    'preferred_language': self.cleaned_data['preferred_language'],
                }
            )
