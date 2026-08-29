from django.contrib import admin

from .models import Farm, FarmMembership


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FarmMembership)
class FarmMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "farm", "role", "created_at")
    list_filter = ("role",)
