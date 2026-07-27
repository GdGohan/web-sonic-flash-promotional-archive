import os
import requests
from urllib.parse import urlparse, unquote

TARGET_URL = "www.sonicteam.com/movie/blackknight/*"

PASTA_DESTINO = "blackknight"

CDX_URL = "https://web.archive.org/cdx/search/cdx"

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

    print("Status CDX:", resposta.status_code)

    resposta.raise_for_status()

    dados = resposta.json()

except Exception as erro:
    print("Erro ao consultar o Wayback Machine:")
    print(repr(erro))
    print(resposta.text if "resposta" in locals() else "")
    input("\nPressione ENTER para sair...")
    exit()


# Remove cabeçalho
if dados and dados[0][0] == "timestamp":
    dados = dados[1:]


print(f"Arquivos encontrados: {len(dados)}")

os.makedirs(PASTA_DESTINO, exist_ok=True)


for item in dados:

    if len(item) < 2:
        continue

    timestamp = item[0]
    url_original = item[1]

    parsed = urlparse(url_original)

    caminho_url = unquote(parsed.path)

    caminho_relativo = caminho_url.lstrip("/")

    if not caminho_relativo or caminho_relativo.endswith("/"):
        caminho_relativo = os.path.join(
            caminho_relativo,
            "index.html"
        )

    caminho_final = os.path.join(
        PASTA_DESTINO,
        caminho_relativo
    )

    pasta_arquivo = os.path.dirname(caminho_final)

    os.makedirs(
        pasta_arquivo,
        exist_ok=True
    )

    print("\nArquivo:", caminho_final)
    print("Original:", url_original)

    if os.path.exists(caminho_final):

        print("Já existe. Pulando.")
        continue

    print("Download:", url_original)

    try:

        resposta_download = requests.get(
            url_original,
            stream=True,
            timeout=120
        )

        print(
            "Status download:",
            resposta_download.status_code
        )

        if resposta_download.status_code != 200:

            print(
                "Erro HTTP:",
                resposta_download.status_code
            )

            continue


        with open(caminho_final, "wb") as arquivo:

            for bloco in resposta_download.iter_content(
                chunk_size=1024 * 1024
            ):

                if bloco:

                    arquivo.write(bloco)


        tamanho_mb = (
            os.path.getsize(caminho_final)
            / (1024 * 1024)
        )


        print(
            f"OK: {caminho_final} "
            f"({tamanho_mb:.2f} MB)"
        )


    except requests.RequestException as erro:

        print(
            "Erro ao baixar:",
            repr(erro)
        )


print("\nDownload concluído.")

input("\nPressione ENTER para sair...")