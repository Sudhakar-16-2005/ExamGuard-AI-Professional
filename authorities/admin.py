from django.contrib import admin

from accounts.admin_mixins import AuthorityScopedAdminMixin

from .models import Authority


@admin.register(Authority)
class AuthorityAdmin(AuthorityScopedAdminMixin, admin.ModelAdmin):
    authority_lookup = "pk"
    list_display = ("code", "name", "authority_type", "jurisdiction", "is_active")
    list_filter = ("authority_type", "is_active")
    search_fields = ("code", "name", "jurisdiction", "contact_email")
    readonly_fields = ("created_at", "updated_at")
