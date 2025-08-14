# core/views.py

from django.shortcuts import render
from django.http import JsonResponse
import json
import os
import time
import requests
import ffmpeg
from django.conf import settings
from google.cloud import storage
from .models import Video, Tag, Audio

# Garante que o Django saiba onde encontrar o FFmpeg
FFMPEG_PATH = r"C:\FFmpeg\bin\ffmpeg.exe"

# --- VIEWS ESTÁTICAS ---
def homepage(request):
    return render(request, 'core/index.html')

def videos_por_tag(request, nome_da_tag):
    tag = Tag.objects.get(nome=nome_da_tag)
    videos = Video.objects.filter(tags=tag)
    contexto = {'tag': tag, 'videos': videos}
    return render(request, 'core/videos_por_tag.html', contexto)

def chat_view(request):
    # Limpa o histórico da conversa ao carregar a página do chat
    if 'historico_chat' in request.session:
        del request.session['historico_chat']
    return render(request, 'core/chat.html')


# --- VIEW PRINCIPAL DO CHAT COM IA E EDIÇÃO DE VÍDEO ---
def process_chat_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message')

            # Recupera o histórico da conversa da sessão
            historico = request.session.get('historico_chat', [])
            historico.append(f"Usuário: {user_message}")

            # --- ETAPA 1: IA CONVERSACIONAL (VIA REQUISIÇÃO DIRETA) ---
            GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
            if not GEMINI_API_KEY:
                raise Exception("A chave de API do Gemini não foi encontrada.")

            # URL da API v1 estável
            gemini_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
            
            prompt = f"""
                Você é "Geni", uma assistente de IA amigável e criativa para um sistema de geração de vídeos. Sua tarefa é conversar com o usuário para descobrir o que ele quer.

                Seu objetivo é coletar as seguintes informações em formato de tags:
                1. O tema principal (ex: esportes, natureza, tecnologia).
                2. O sentimento/clima (ex: motivacional, suspense, engraçado, calmo).
                3. O estilo da música (ex: épica, calma, rock).

                Se você sentir que tem tags suficientes (pelo menos 2 ou 3 descritivas), responda APENAS com um JSON no seguinte formato:
                {{"status": "ready", "tags": ["tag1", "tag2", "tag3"], "response_text": "Entendido! Tenho tudo que preciso. Vou começar a criar seu vídeo sobre [tema] com um clima [sentimento] e música [estilo]."}}

                Se precisar de mais informações, faça UMA pergunta clara e amigável para obter o próximo detalhe e responda APENAS com um JSON no seguinte formato:
                {{"status": "clarifying", "question": "Sua pergunta aqui.", "tags": ["tags_ja_coletadas"]}}

                Histórico da conversa até agora:
                {historico}

                Analise a última mensagem do usuário e gere sua resposta.
                JSON:
            """
            
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            api_response = requests.post(gemini_url, json=payload)
            api_response.raise_for_status()
            
            response_json = api_response.json()
            raw_response_text = response_json['candidates'][0]['content']['parts'][0]['text']

            json_start_index = raw_response_text.find('{')
            json_end_index = raw_response_text.rfind('}') + 1
            if json_start_index != -1 and json_end_index != 0:
                json_string = raw_response_text[json_start_index:json_end_index]
                response_data = json.loads(json_string)
            else:
                raise Exception("A IA não retornou um JSON válido.")

            # --- LÓGICA DE CONVERSA ---
            if response_data.get('status') == 'clarifying':
                historico.append(f"Geni: {response_data.get('question')}")
                request.session['historico_chat'] = historico
                return JsonResponse({'response': response_data.get('question')})
            
            elif response_data.get('status') == 'ready':
                # Limpa o histórico para uma nova conversa
                request.session['historico_chat'] = []
                tag_list = response_data.get('tags', [])

                # AVISO: A renderização do vídeo é uma tarefa pesada.
                # A implementação ideal aqui seria iniciar uma tarefa em segundo plano (com Celery).
                # Por enquanto, executaremos diretamente, mas o site ficará "travado" durante a renderização.

                videos_encontrados = Video.objects.filter(tags__nome__in=tag_list).distinct()
                audios_encontrados = Audio.objects.filter(tags__nome__in=tag_list).distinct()

                if not videos_encontrados.exists():
                    return JsonResponse({'response': f"Puxa, não encontrei vídeos com as tags {tag_list}. Que tal tentarmos outras?"})

                video_para_editar = videos_encontrados.first()
                audio_para_editar = audios_encontrados.first() if audios_encontrados.exists() else None

                # --- ETAPA DE EDIÇÃO COM FFMPEG ---
                temp_video_path = "temp_video.mp4"
                temp_audio_path = "temp_audio.mp3"
                nome_video_final = f"video_final_{video_para_editar.id}_{int(time.time())}.mp4"
                caminho_video_final_local = nome_video_final

                video_url = video_para_editar.arquivo_video.url
                with open(temp_video_path, "wb") as f:
                    f.write(requests.get(video_url).content)

                input_video = ffmpeg.input(temp_video_path)
                
                if audio_para_editar:
                    audio_url = audio_para_editar.arquivo_audio.url
                    with open(temp_audio_path, "wb") as f:
                        f.write(requests.get(audio_url).content)
                    input_audio = ffmpeg.input(temp_audio_path)
                    ffmpeg.output(input_video.video, input_audio.audio, caminho_video_final_local, vcodec='copy', acodec='aac').run(cmd=FFMPEG_PATH, overwrite_output=True)
                else:
                    ffmpeg.output(input_video.video, caminho_video_final_local, vcodec='copy').run(cmd=FFMPEG_PATH, overwrite_output=True)

                # --- ETAPA DE UPLOAD PARA O GCS ---
                storage_client = storage.Client()
                bucket = storage_client.get_bucket(settings.GS_BUCKET_NAME)
                destination_blob_name = f'videos_gerados/{nome_video_final}'
                blob = bucket.blob(destination_blob_name)
                blob.upload_from_filename(caminho_video_final_local)
                
                video_url_final = f'https://storage.googleapis.com/{settings.GS_BUCKET_NAME}/{destination_blob_name}'
                
                # Limpa arquivos temporários
                os.remove(temp_video_path)
                if audio_para_editar:
                    os.remove(temp_audio_path)
                os.remove(caminho_video_final_local)
                
                bot_response = response_data.get('response_text', 'Seu vídeo está pronto!')
                return JsonResponse({'response': bot_response, 'video_url': video_url_final})
            
            else:
                return JsonResponse({'response': "Não entendi muito bem. Poderia descrever de outra forma?"})

        except Exception as e:
            if 'historico_chat' in request.session:
                del request.session['historico_chat']
            return JsonResponse({'error': f'Ocorreu um erro geral: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Método inválido'}, status=405)