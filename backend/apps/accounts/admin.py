from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User
from apps.core.admin_site import admin_site


class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    fieldsets = DjangoUserAdmin.fieldsets + (("SmartCrop", {"fields": ("role",)}),)


admin_site.register(User, UserAdmin)
