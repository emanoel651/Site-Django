# core/management/commands/bulk_add_audios.py

import os
from django.core.management.base import BaseCommand
from django.core.files import File
from core.models import Audio, Tag # MUDANÇA: Importa o modelo Audio
from django.conf import settings
from google.cloud import storage

class Command(BaseCommand):
    help = 'Adiciona áudios de uma pasta em massa para o banco de dados e associa uma tag.'

    def add_arguments(self, parser):
        parser.add_argument('folder_path', type=str, help='O caminho para a pasta que contém os áudios.')
        parser.add_argument('tag_name', type=str, help='O nome da tag a ser associada aos áudios.')

    def handle(self, *args, **options):
        folder_path = options['folder_path']
        tag_name = options['tag_name']

        # 1. Conectar ao Google Cloud
        try:
            storage_client = storage.Client()
            bucket = storage_client.get_bucket(settings.GS_BUCKET_NAME)
            self.stdout.write(self.style.SUCCESS(f'Conectado com sucesso ao bucket "{settings.GS_BUCKET_NAME}".'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Falha ao conectar com o Google Cloud: {e}'))
            return

        # 2. Obter ou criar a Tag no Django
        tag, created = Tag.objects.get_or_create(nome=tag_name)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Tag "{tag_name}" criada.'))
        else:
            self.stdout.write(self.style.WARNING(f'Usando a tag já existente "{tag_name}".'))

        # 3. Iterar, fazer o upload e salvar no Django
        for filename in os.listdir(folder_path):
            # MUDANÇA: Procura por extensões de áudio
            if not filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                continue

            local_file_path = os.path.join(folder_path, filename)
            # MUDANÇA: Salva na pasta 'audios' do bucket
            destination_blob_name = f'audios/{filename}'

            self.stdout.write(f'Processando "{filename}"...')

            try:
                # ETAPA DE UPLOAD DIRETO
                self.stdout.write(f'  -> Fazendo upload para: {destination_blob_name}')
                blob = bucket.blob(destination_blob_name)
                blob.upload_from_filename(local_file_path)
                self.stdout.write(self.style.SUCCESS('  -> Upload concluído.'))

                # ETAPA DE SALVAMENTO NO DJANGO (usando o modelo Audio)
                audio, audio_created = Audio.objects.get_or_create(
                    titulo=os.path.splitext(filename)[0],
                    defaults={'arquivo_audio': destination_blob_name}
                )
                
                if audio_created:
                     self.stdout.write(self.style.SUCCESS(f'  -> Registro para "{audio.titulo}" salvo no Django.'))
                else:
                    self.stdout.write(self.style.WARNING(f'  -> Registro para "{audio.titulo}" já existia e foi atualizado.'))

                # Associa a tag
                audio.tags.add(tag)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Falha ao processar o arquivo {filename}: {e}'))

        self.stdout.write(self.style.SUCCESS('Processo de importação de áudios em massa finalizado!'))