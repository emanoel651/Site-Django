# teste_gcloud.py
import os
from google.cloud import storage

# --- CONFIGURAÇÕES ---
CREDENTIALS_FILE = 'gcp-credentials.json'
BUCKET_NAME = 'base_de_dados_gvai' # O nome do seu bucket
# -------------------

print("Iniciando teste de upload direto para o Google Cloud Storage...")

try:
    # Define o caminho para as credenciais
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_FILE

    # Cria um cliente de storage
    storage_client = storage.Client()

    print(f"Cliente de storage criado para o projeto: {storage_client.project}")

    # Pega o bucket
    bucket = storage_client.get_bucket(BUCKET_NAME)
    print(f"Acessando o bucket: {bucket.name}")

    # Define o nome do arquivo de destino no bucket e o conteúdo
    destination_blob_name = 'teste_direto/hello.txt'
    source_content = 'Olá, Mundo! O teste de upload funcionou.'

    # Cria um "blob" (o objeto que será o arquivo)
    blob = bucket.blob(destination_blob_name)

    print(f"Preparando para enviar dados para: {destination_blob_name}")

    # Faz o upload do conteúdo
    blob.upload_from_string(source_content)

    print("-" * 30)
    print("SUCESSO!")
    print(f"O arquivo '{destination_blob_name}' foi enviado para o bucket '{BUCKET_NAME}'.")
    print("Por favor, verifique o bucket no seu navegador.")
    print("-" * 30)

except Exception as e:
    print("-" * 30)
    print("FALHA!")
    print("Ocorreu um erro durante o teste de upload:")
    print(e)
    print("-" * 30)