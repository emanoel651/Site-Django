# core/management/commands/bulk_add_videos.py

import os
from django.core.management.base import BaseCommand
from django.conf import settings
from google.cloud import storage
from core.models import Video, Tag

class Command(BaseCommand):
    help = 'Faz o upload de vídeos de uma pasta para o GCS e depois salva no banco de dados.'

    def add_arguments(self, parser):
        parser.add_argument('folder_path', type=str, help='O caminho para a pasta que contém os vídeos.')
        parser.add_argument('tag_name', type=str, help='O nome da tag a ser associada aos vídeos.')

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
            if not filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                continue

            local_file_path = os.path.join(folder_path, filename)
            destination_blob_name = f'videos/{filename}' # Caminho dentro do bucket

            self.stdout.write(f'Processando "{filename}"...')

            try:
                # ETAPA DE UPLOAD DIRETO
                self.stdout.write(f'  -> Fazendo upload para: {destination_blob_name}')
                blob = bucket.blob(destination_blob_name)
                blob.upload_from_filename(local_file_path)
                self.stdout.write(self.style.SUCCESS('  -> Upload concluído.'))

                # ETAPA DE SALVAMENTO NO DJANGO
                # Agora que o upload está garantido, criamos o registro no banco de dados.
                video, video_created = Video.objects.get_or_create(
                    titulo=os.path.splitext(filename)[0],
                    defaults={'arquivo_video': destination_blob_name}
                )
                
                if video_created:
                     self.stdout.write(self.style.SUCCESS(f'  -> Registro para "{video.titulo}" salvo no Django.'))
                else:
                    self.stdout.write(self.style.WARNING(f'  -> Registro para "{video.titulo}" já existia e foi atualizado.'))


                # Associa a tag
                video.tags.add(tag)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Falha ao processar o arquivo {filename}: {e}'))

        self.stdout.write(self.style.SUCCESS('Processo de importação em massa finalizado!'))