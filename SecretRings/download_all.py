import os
import requests
from urllib.parse import urlparse, unquote

# Prefixo original que será pesquisado no Wayback
TARGET_URL = "http://sonic.sega.jp/secretrings/*"

# Pasta de destino
PASTA_DESTINO = ""

# API CDX do Wayback Machine
CDX_URL = "https://web.archive.org/cdx/search/cdx"

# Prefixo do Wayback
WAYBACK_PREFIX = "https://web.archive.org/web/"

print("Consultando o Wayback Machine...")

params = {
    "url": TARGET_URL,
    "output": "json",
    "fl": "timestamp,original,statuscode,mimetype",
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
if dados and dados[0][0] == "timestamp":
    dados = dados[1:]


# Lista de URLs
urls = []

for item in dados:

    if not item or len(item) < 2:
        continue

    timestamp = item[0]
    url = item[1]

    if url not in [x["url"] for x in urls]:

        urls.append({
            "url": url,
            "timestamp": timestamp
        })


print(f"\nArquivos encontrados: {len(urls)}")


# Session para reutilizar conexão HTTP
session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


def baixar_url(url, caminho):

    """
    Tenta baixar uma URL.

    Retorna True se conseguiu baixar.
    """

    try:

        resposta = session.get(
            url,
            stream=True,
            timeout=120,
            allow_redirects=True
        )

        if resposta.status_code != 200:

            print(
                f"HTTP {resposta.status_code}: {url}"
            )

            resposta.close()

            return False

        with open(caminho, "wb") as arquivo:

            for bloco in resposta.iter_content(
                chunk_size=1024 * 1024
            ):

                if bloco:
                    arquivo.write(bloco)

        return True

    except requests.RequestException as erro:

        print(f"Erro: {erro}")

        return False


# Baixa os arquivos mantendo a estrutura da URL
for item in urls:

    url_original = item["url"]
    timestamp = item["timestamp"]

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

    # Pasta de destino
    caminho_final = os.path.join(
        PASTA_DESTINO,
        caminho_relativo
    )

    # Cria as subpastas necessárias
    pasta_arquivo = os.path.dirname(caminho_final)

    if pasta_arquivo:
        os.makedirs(
            pasta_arquivo,
            exist_ok=True
        )

    print("\n" + "=" * 70)

    print(f"Arquivo: {caminho_final}")
    print(f"URL original: {url_original}")

    if os.path.exists(caminho_final):

        print("Já existe. Pulando.")

        continue


    # ============================================================
    # 1. PRIMEIRA TENTATIVA: SITE ORIGINAL
    # ============================================================

    print("Tentando URL original...")

    sucesso = baixar_url(
        url_original,
        caminho_final
    )


    # ============================================================
    # 2. SE FALHAR: WAYBACK MACHINE
    # ============================================================

    if not sucesso:

        print(
            "URL original falhou."
        )

        print(
            "Tentando pelo Wayback Machine..."
        )

        # Monta:
        #
        # https://web.archive.org/web/20200101123456/http://site.com/arquivo
        #
        url_wayback = (
            WAYBACK_PREFIX
            + timestamp
            + "/"
            + url_original
        )

        print(
            f"URL Wayback: {url_wayback}"
        )

        sucesso = baixar_url(
            url_wayback,
            caminho_final
        )


    # ============================================================
    # RESULTADO
    # ============================================================

    if sucesso:

        tamanho_mb = os.path.getsize(
            caminho_final
        ) / (1024 * 1024)

        print(
            f"OK: {caminho_final} "
            f"({tamanho_mb:.2f} MB)"
        )

    else:

        # Remove arquivo incompleto, caso tenha sido criado
        if os.path.exists(caminho_final):

            try:
                os.remove(caminho_final)
            except OSError:
                pass

        print(
            f"FALHOU: {url_original}"
        )


print("\nDownload concluído.")