# core/models.py
from django.db import models

class Tag(models.Model):
    """Modelo para representar tags que podem ser associadas a qualquer mídia."""
    nome = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nome

class Video(models.Model):
    """Modelo para representar um vídeo no banco de dados."""
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    arquivo_video = models.FileField(upload_to='videos/')
    data_upload = models.DateTimeField(auto_now_add=True)
    duracao_segundos = models.PositiveIntegerField(default=0, help_text="Duração do vídeo em segundos.")
    tags = models.ManyToManyField(Tag, blank=True) # Relacionamento com as tags

    def __str__(self):
        return self.titulo

class Audio(models.Model):
    """Modelo para representar uma música de fundo ou áudio."""
    titulo = models.CharField(max_length=200)
    artista = models.CharField(max_length=100, blank=True, null=True)
    arquivo_audio = models.FileField(upload_to='audios/')
    duracao_segundos = models.PositiveIntegerField(default=0, help_text="Duração do áudio em segundos.")
    mood = models.CharField(max_length=50, blank=True, null=True, help_text="Ex: suspense, feliz, épico, etc.")
    tags = models.ManyToManyField(Tag, blank=True) # Relacionamento com as tags

    def __str__(self):
        return f'{self.titulo} - {self.artista}'

class Imagem(models.Model):
    """Modelo para representar uma imagem (ex: miniatura do vídeo)."""
    titulo = models.CharField(max_length=200)
    arquivo_imagem = models.ImageField(upload_to='imagens/')
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return self.titulo