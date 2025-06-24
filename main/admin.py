from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from main import models


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "website_title",
        "custom_domain",
        "is_premium",
        "is_staff",
        "is_active",
        "date_joined",
        "page_count",
        "image_count",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "is_premium",
        "show_nav",
        "date_joined",
        "subscription_start_date",
    )
    search_fields = ("username", "email", "website_title", "custom_domain")
    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Website Settings",
            {"fields": ("website_title", "custom_domain", "homepage", "show_nav")},
        ),
        ("Customization", {"fields": ("custom_css",), "classes": ("collapse",)}),
        (
            "Subscription",
            {
                "fields": (
                    "is_premium",
                    "stripe_customer_id",
                    "stripe_subscription_id",
                    "subscription_start_date",
                    "subscription_end_date",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def page_count(self, obj):
        return obj.page_set.count()

    page_count.short_description = "Pages"

    def image_count(self, obj):
        return obj.image_set.count()

    image_count.short_description = "Images"


@admin.register(models.Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "user", "created_at", "updated_at", "word_count")
    list_filter = ("created_at", "updated_at", "user")
    search_fields = ("title", "slug", "body", "user__username")
    ordering = ("-updated_at",)
    fieldsets = (
        (None, {"fields": ("user", "title", "slug")}),
        (
            "Content",
            {
                "fields": ("body",),
                "description": "Content is written in Markdown format.",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")

    def word_count(self, obj):
        if obj.body:
            return len(obj.body.split())
        return 0

    word_count.short_description = "Words"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(models.Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "filename",
        "file_size_mb",
        "uploaded_at",
        "image_preview",
    )
    list_filter = ("uploaded_at", "extension", "user")
    search_fields = ("name", "slug", "user__username")
    ordering = ("-uploaded_at",)
    fieldsets = (
        (None, {"fields": ("user", "name", "slug")}),
        (
            "File Info",
            {
                "fields": ("extension", "uploaded_at", "file_size_display"),
            },
        ),
        ("Preview", {"fields": ("image_preview_large",)}),
    )
    readonly_fields = ("uploaded_at", "file_size_display", "image_preview_large")

    def file_size_mb(self, obj):
        return f"{obj.data_size} MB"

    file_size_mb.short_description = "Size"

    def file_size_display(self, obj):
        return f"{obj.data_size} MB ({len(obj.data):,} bytes)"

    file_size_display.short_description = "File Size"

    def image_preview(self, obj):
        if obj.extension.lower() in ["jpg", "jpeg", "png", "gif", "webp"]:
            return format_html(
                '<img src="data:image/{};base64,{}" style="max-width: 50px; max-height: 50px;" />',
                obj.extension,
                obj.data_as_base64,
            )
        return "No preview"

    image_preview.short_description = "Preview"

    def image_preview_large(self, obj):
        if obj.extension.lower() in ["jpg", "jpeg", "png", "gif", "webp"]:
            return format_html(
                '<img src="data:image/{};base64,{}" style="max-width: 400px; max-height: 400px;" />',
                obj.extension,
                obj.data_as_base64,
            )
        return "No preview available"

    image_preview_large.short_description = "Image Preview"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


admin.site.site_header = "Pulsar Admin"
admin.site.site_title = "Pulsar Admin"
admin.site.index_title = "Welcome to Pulsar Administration"
