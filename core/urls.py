# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    # path('tag/<str:nome_da_tag>/', views.videos_por_tag, name='videos_por_tag'),
    path('chat/', views.chat_view, name='chat'), # <-- ADICIONE ESTA LINHA
    path('chat/process/', views.process_chat_message, name='process_chat_message'), # <-- ADICIONE ESTA LINHA
]