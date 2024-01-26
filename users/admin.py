from django.contrib import admin
from .models import Profile, Settings
from vote.models import Vote


admin.site.register(Profile)
admin.site.register(Settings)
admin.site.register(Vote)
