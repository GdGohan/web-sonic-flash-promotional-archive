import os
import requests
from urllib.parse import urlparse, unquote
from collections import defaultdict

# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Site original
TARGET_URL = "http://www.sega.com/sonicblackknight/*"

# Começar nesta captura e continuar até a mais recente
TIMESTAMP_INICIAL = "20090402094932"

# Pasta de destino
PASTA_DESTINO = "sonicblackknight"

# API CDX
CDX_URL = "https://web.archive.org/cdx/search/cdx"

# ============================================================
# OPÇÕES
# ============================================================

# True = baixa somente quando o conteúdo mudou
# False = baixa todas as capturas encontradas
BAIXAR_APENAS_MUDANCAS = True

# True = mantém uma pasta por timestamp
# Exemplo:
# sonicblackknight/
#   20090402094932/
#   20090402101532/
#
# False = mantém somente a estrutura original
# e o arquivo mais recente substitui o anterior.
SEPARAR_POR_TIMESTAMP = True

# ============================================================
# PREPARAÇÃO
# ============================================================

os.makedirs(PASTA_DESTINO, exist_ok=True)

print("=" * 80)
print("WAYBACK MACHINE - SONIC & THE BLACK KNIGHT")
print("=" * 80)

print(f"URL:              {TARGET_URL}")
print(f"Começando em:     {TIMESTAMP_INICIAL}")
print(f"Destino:          {PASTA_DESTINO}")
print(f"Somente mudanças: {BAIXAR_APENAS_MUDANCAS}")
print(f"Por timestamp:    {SEPARAR_POR_TIMESTAMP}")
print()

# ============================================================
# CONSULTA CDX
# ============================================================

print("Consultando o Wayback Machine...")
print("Isso pode demorar dependendo da quantidade de capturas.")
print()

params = {
    "url": TARGET_URL,
    "output": "json",

    # Campos retornados:
    # original
    # timestamp
    # statuscode
    # mimetype
    # digest
    # length
    "fl": (
        "original,"
        "timestamp,"
        "statuscode,"
        "mimetype,"
        "digest,"
        "length"
    ),

    # Apenas arquivos HTTP 200
    "filter": "statuscode:200",

    # Começar na data desejada
    "from": TIMESTAMP_INICIAL,

    # NÃO colocamos "to".
    # Portanto, vai até a captura mais recente disponível.

    # Quantidade máxima por página
    "collapse": "urlkey",
}

try:

    resposta = requests.get(
        CDX_URL,
        params=params,
        timeout=180,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    resposta.raise_for_status()

    dados = resposta.json()

except Exception as erro:

    print()
    print("ERRO ao consultar o Wayback Machine:")
    print(erro)
    exit(1)

# ============================================================
# REMOVE CABEÇALHO
# ============================================================

if dados and dados[0][0] == "original":
    dados = dados[1:]

print(f"Registros encontrados: {len(dados)}")
print()

if not dados:

    print("Nenhum arquivo encontrado.")
    exit(0)

# ============================================================
# ORGANIZA OS RESULTADOS
# ============================================================

#
# IMPORTANTE:
#
# Como estamos usando collapse=urlkey, teremos uma captura
# representativa de cada URL.
#
# Para reconstruir TODAS as versões históricas, remova o
# "collapse" acima.
#

arquivos = []

for item in dados:

    if len(item) < 6:
        continue

    url_original = item[0]
    timestamp = item[1]
    statuscode = item[2]
    mimetype = item[3]
    digest = item[4]
    length = item[5]

    arquivos.append({
        "url": url_original,
        "timestamp": timestamp,
        "statuscode": statuscode,
        "mimetype": mimetype,
        "digest": digest,
        "length": length,
    })

# Ordena cronologicamente
arquivos.sort(
    key=lambda x: x["timestamp"]
)

print(f"Arquivos preparados: {len(arquivos)}")
print()

# ============================================================
# DETECTA DUPLICATAS POR DIGEST
# ============================================================

digests_baixados = set()

# Estatísticas
baixados = 0
ignorados = 0
duplicados = 0
erros = 0

sessao = requests.Session()

sessao.headers.update({
    "User-Agent": "Mozilla/5.0"
})

# ============================================================
# DOWNLOAD
# ============================================================

for numero, item in enumerate(arquivos, start=1):

    url_original = item["url"]
    timestamp = item["timestamp"]
    digest = item["digest"]

    print()
    print("=" * 80)
    print(f"[{numero}/{len(arquivos)}]")
    print(f"Timestamp: {timestamp}")
    print(f"URL:       {url_original}")
    print(f"Digest:    {digest}")

    # --------------------------------------------------------
    # IGNORA CONTEÚDO DUPLICADO
    # --------------------------------------------------------

    if BAIXAR_APENAS_MUDANCAS:

        if digest in digests_baixados:

            print("Conteúdo idêntico a outro arquivo. Pulando.")

            duplicados += 1

            continue

    # --------------------------------------------------------
    # CAMINHO ORIGINAL
    # --------------------------------------------------------

    parsed = urlparse(url_original)

    caminho_url = unquote(parsed.path)

    caminho_relativo = caminho_url.lstrip("/")

    # Se termina em /
    if not caminho_relativo or caminho_relativo.endswith("/"):

        caminho_relativo = os.path.join(
            caminho_relativo,
            "index.html"
        )

    # Remove possíveis caracteres problemáticos
    caminho_relativo = caminho_relativo.replace(
        "\\",
        "/"
    )

    # --------------------------------------------------------
    # PASTA DO TIMESTAMP
    # --------------------------------------------------------

    if SEPARAR_POR_TIMESTAMP:

        pasta_timestamp = os.path.join(
            PASTA_DESTINO,
            timestamp
        )

        caminho_local = os.path.join(
            pasta_timestamp,
            caminho_relativo
        )

    else:

        caminho_local = os.path.join(
            PASTA_DESTINO,
            caminho_relativo
        )

    # --------------------------------------------------------
    # CRIA DIRETÓRIO
    # --------------------------------------------------------

    pasta_arquivo = os.path.dirname(
        caminho_local
    )

    os.makedirs(
        pasta_arquivo,
        exist_ok=True
    )

    print(f"Destino:   {caminho_local}")

    # --------------------------------------------------------
    # SE JÁ EXISTE
    # --------------------------------------------------------

    if os.path.exists(caminho_local):

        print("Arquivo já existe. Pulando.")

        ignorados += 1

        if digest:
            digests_baixados.add(digest)

        continue

    # --------------------------------------------------------
    # URL DO WAYBACK
    # --------------------------------------------------------

    url_wayback = (
        "https://web.archive.org/web/"
        f"{timestamp}id_/"
        f"{url_original}"
    )

    print(f"Download:  {url_wayback}")

    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    try:

        resposta_download = sessao.get(
            url_wayback,
            stream=True,
            timeout=180,
            allow_redirects=True
        )

        if resposta_download.status_code != 200:

            print(
                "Erro HTTP:",
                resposta_download.status_code
            )

            erros += 1

            continue

        # ----------------------------------------------------
        # SALVA
        # ----------------------------------------------------

        with open(
            caminho_local,
            "wb"
        ) as arquivo:

            for bloco in resposta_download.iter_content(
                chunk_size=1024 * 1024
            ):

                if bloco:

                    arquivo.write(bloco)

        # ----------------------------------------------------
        # TAMANHO
        # ----------------------------------------------------

        tamanho = os.path.getsize(
            caminho_local
        )

        tamanho_mb = tamanho / (
            1024 * 1024
        )

        print(
            f"OK - {tamanho_mb:.2f} MB"
        )

        baixados += 1

        if digest:
            digests_baixados.add(digest)

    except requests.RequestException as erro:

        print(
            "Erro no download:",
            erro
        )

        erros += 1

    except OSError as erro:

        print(
            "Erro ao salvar:",
            erro
        )

        erros += 1

# ============================================================
# RESUMO
# ============================================================

print()
print()
print("=" * 80)
print("DOWNLOAD CONCLUÍDO")
print("=" * 80)

print(f"Registros encontrados: {len(arquivos)}")
print(f"Baixados:              {baixados}")
print(f"Já existentes:         {ignorados}")
print(f"Duplicados:            {duplicados}")
print(f"Erros:                 {erros}")

print()
print(
    f"Arquivos salvos em: {PASTA_DESTINO}"
)