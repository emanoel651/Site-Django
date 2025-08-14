# core/admin.py
from django.contrib import admin
from .models import Video, Audio, Imagem, Tag

admin.site.register(Video)
admin.site.register(Audio)
admin.site.register(Imagem)
admin.site.register(Tag) # Registre o novo modelo de Tag