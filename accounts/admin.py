from django.contrib import admin

from .admin_mixins import AuthorityScopedAdminMixin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(AuthorityScopedAdminMixin, admin.ModelAdmin):
    list_display = ("user", "role", "authority", "is_mfa_enabled")
    list_filter = ("role", "is_mfa_enabled", "authority")
    search_fields = ("user__username", "user__email", "phone")
