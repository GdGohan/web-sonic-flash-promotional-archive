import os
import requests
from urllib.parse import urlparse, unquote

# Prefixo original que será pesquisado no Wayback
TARGET_URL = "http://sonic.sega.jp/ankokunokishi/*"

# Pasta de destino
PASTA_DESTINO = ""

# API CDX do Wayback Machine
CDX_URL = "https://web.archive.org/cdx/search/cdx"

print("Consultando o Wayback Machine...")

params = {
    "url": TARGET_URL,
    "output": "json",
    "fl": "original,statuscode,mimetype",
    "filter": "statuscode:200",
    "collapse": "urlkey",
}

try:
    resposta = requests.get(
        CDX_URL,
        params=params,
        timeout=60
    )

    resposta.raise_for_status()
    dados = resposta.json()

except Exception as erro:
    print(f"Erro ao consultar o Wayback Machine: {erro}")
    exit()


# Remove o cabeçalho
if dados and dados[0][0] == "original":
    dados = dados[1:]


# Lista de URLs
urls = []

for item in dados:

    if not item:
        continue

    url = item[0]

    if url not in urls:
        urls.append(url)


print(f"\nArquivos encontrados: {len(urls)}")


# Baixa os arquivos mantendo a estrutura da URL
for url_original in urls:

    parsed = urlparse(url_original)

    # Caminho original da URL
    caminho_url = unquote(parsed.path)

    # Remove a barra inicial
    caminho_relativo = caminho_url.lstrip("/")

    # Se a URL terminar com "/", trata como index.html
    if not caminho_relativo or caminho_relativo.endswith("/"):
        caminho_relativo = os.path.join(
            caminho_relativo,
            "index.html"
        )

    # Cria as subpastas necessárias
    pasta_arquivo = os.path.dirname(caminho_relativo)

    os.makedirs(
        pasta_arquivo,
        exist_ok=True
    )

    print(f"\nArquivo: {caminho_relativo}")
    print(f"URL: {url_original}")

    if os.path.exists(caminho_relativo):

        print("Já existe. Pulando.")
        continue

    try:

        resposta_download = requests.get(
            url_original,
            stream=True,
            timeout=120
        )

        if resposta_download.status_code != 200:

            print(
                f"Erro HTTP: "
                f"{resposta_download.status_code}"
            )

            continue

        with open(caminho, "wb") as arquivo:

            for bloco in resposta_download.iter_content(
                chunk_size=1024 * 1024
            ):

                if bloco:
                    arquivo.write(bloco)

        tamanho_mb = os.path.getsize(caminho_relativo) / (
            1024 * 1024
        )

        print(
            f"OK: {caminho_relativo} "
            f"({tamanho_mb:.2f} MB)"
        )

    except requests.RequestException as erro:

        print(
            f"Erro ao baixar {caminho_relativo}: {erro}"
        )


print("\nDownload concluído.")