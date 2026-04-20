from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import FarmerProfile


class FarmerProfileInline(admin.StackedInline):
    model = FarmerProfile
    can_delete = False
    verbose_name_plural = "Farmer Profile"
    fk_name = "user"
    fields = (
        ("preferred_language",),
        ("first_name", "last_name"),
        ("phone_number", "location"),
        ("farm_size_acres", "soil_type"),
        ("ph_level", "water_source"),
        ("current_crops", "past_crops"),
        ("top_pests",),
        ("has_livestock", "livestock_types"),
        ("telegram_chat_id", "telegram_link_token"),
    )
    extra = 0
    readonly_fields = ("telegram_link_token",)


class UserAdmin(BaseUserAdmin):
    inlines = (FarmerProfileInline,)
    list_display = (
        "username", "email", "get_full_name", "get_location",
        "get_language", "get_telegram_linked", "is_active", "is_staff", "date_joined"
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "farmerprofile__preferred_language")
    search_fields = ("username", "email", "first_name", "last_name", "farmerprofile__location")

    def get_full_name(self, obj):
        try:
            p = obj.farmerprofile
            return f"{p.first_name or ''} {p.last_name or ''}".strip() or "—"
        except FarmerProfile.DoesNotExist:
            return "—"
    get_full_name.short_description = "Full Name"

    def get_location(self, obj):
        try:
            return obj.farmerprofile.location or "—"
        except FarmerProfile.DoesNotExist:
            return "—"
    get_location.short_description = "Location"

    def get_language(self, obj):
        try:
            lang_map = {"en": "🇬🇧 English", "ha": "🇳🇬 Hausa", "ig": "🇳🇬 Igbo", "yo": "🇳🇬 Yoruba"}
            return lang_map.get(obj.farmerprofile.preferred_language, "—")
        except FarmerProfile.DoesNotExist:
            return "—"
    get_language.short_description = "Language"

    def get_telegram_linked(self, obj):
        try:
            linked = bool(obj.farmerprofile.telegram_chat_id)
            color = "#16a34a" if linked else "#6b7280"
            label = "✓ Linked" if linked else "✗ Not linked"
            return format_html('<span style="color:{};font-weight:600">{}</span>', color, label)
        except FarmerProfile.DoesNotExist:
            return "—"
    get_telegram_linked.short_description = "Telegram"


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user", "get_full_name", "location", "farm_size_acres",
        "soil_type", "preferred_language", "has_livestock",
        "get_telegram_linked", "created_at",
    )
    list_filter = (
        "preferred_language", "soil_type", "ph_level",
        "water_source", "has_livestock",
    )
    search_fields = (
        "user__username", "user__email", "first_name",
        "last_name", "location", "current_crops",
    )
    readonly_fields = ("created_at", "updated_at", "telegram_link_token")
    list_select_related = ("user",)
    fieldsets = (
        ("Account", {
            "fields": ("user",)
        }),
        ("Personal Info", {
            "fields": (("first_name", "last_name"), "phone_number", "preferred_language"),
        }),
        ("Farm Details", {
            "fields": (
                "location",
                ("farm_size_acres", "soil_type"),
                ("ph_level", "water_source"),
                ("current_crops", "past_crops"),
                "top_pests",
            ),
        }),
        ("Livestock", {
            "fields": (("has_livestock", "livestock_types"),),
            "classes": ("collapse",),
        }),
        ("Telegram Integration", {
            "fields": ("telegram_chat_id", "telegram_link_token"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": (("created_at", "updated_at"),),
            "classes": ("collapse",),
        }),
    )
    ordering = ("-created_at",)

    def get_full_name(self, obj):
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip() or "—"
    get_full_name.short_description = "Full Name"

    def get_telegram_linked(self, obj):
        if obj.telegram_chat_id:
            return format_html(
                '<span style="color:#16a34a;font-weight:600">✓ Linked ({})</span>',
                obj.telegram_chat_id
            )
        return format_html('<span style="color:#6b7280">✗ Not linked</span>')
    get_telegram_linked.short_description = "Telegram"


# Re-register User with enhanced admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
