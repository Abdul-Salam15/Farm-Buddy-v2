from django.contrib import admin
from django.utils.html import format_html
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    fields = ("role", "short_content", "created_at")
    readonly_fields = ("role", "short_content", "created_at")
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ("created_at",)

    def short_content(self, obj):
        return obj.content[:120] + "…" if len(obj.content) > 120 else obj.content
    short_content.short_description = "Content"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "user", "get_message_count",
        "get_last_role", "updated_at", "created_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = (MessageInline,)
    ordering = ("-updated_at",)
    date_hierarchy = "created_at"
    list_per_page = 30

    def get_message_count(self, obj):
        count = obj.messages.count()
        return format_html(
            '<span style="font-weight:600;color:#16a34a">{}</span>', count
        )
    get_message_count.short_description = "Messages"

    def get_last_role(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if not last:
            return "—"
        color = "#16a34a" if last.role == "assistant" else "#3b82f6"
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            color, last.role.capitalize()
        )
    get_last_role.short_description = "Last Message"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id", "conversation", "get_user", "role",
        "get_preview", "has_image", "created_at",
    )
    list_filter = ("role", "created_at")
    search_fields = (
        "content", "conversation__title",
        "conversation__user__username",
    )
    readonly_fields = ("created_at", "references")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50

    def get_user(self, obj):
        return obj.conversation.user or "—"
    get_user.short_description = "User"

    def get_preview(self, obj):
        preview = obj.content[:100] + "…" if len(obj.content) > 100 else obj.content
        color = "#16a34a" if obj.role == "assistant" else "#e6edf3"
        return format_html('<span style="color:{}">{}</span>', color, preview)
    get_preview.short_description = "Content"

    def has_image(self, obj):
        if obj.image:
            return format_html('<span style="color:#16a34a;font-weight:600">✓</span>')
        return "—"
    has_image.short_description = "Image"
