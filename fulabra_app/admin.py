from django.contrib import admin

from .models import *

admin.site.register(User)
admin.site.register(LobbyGroup)
admin.site.register(Word)
admin.site.register(Category)
