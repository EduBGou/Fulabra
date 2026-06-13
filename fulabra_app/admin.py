from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(User)
admin.site.register(LobbyGroup)
admin.site.register(Word)
