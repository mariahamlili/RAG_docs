from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

# Default User model; farm membership lives in farms.FarmMembership.

admin.site.unregister(User)
admin.site.register(User, DjangoUserAdmin)
