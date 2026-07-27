import os
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

# URL base

BASE_URL = "https://sonic.sega.jp/ankokunokishi/"

# Arquivo XML

XML_FILE = "screenshot.xml"

# Pasta onde os arquivos serão salvos

PASTA_DESTINO = ""

# Lê o XML

tree = ET.parse(XML_FILE)
root = tree.getroot()

# Evita baixar a mesma imagem mais de uma vez

urls_baixadas = set()

# Percorre todos os <entry>

for entry in root.findall("entry"):

    for atributo in ["tm", "pic"]:

        caminho_relativo = entry.get(atributo)

        if not caminho_relativo:
            continue

        # Monta a URL completa
        url = urljoin(BASE_URL, caminho_relativo)

        # Evita duplicados
        if url in urls_baixadas:
            continue

        urls_baixadas.add(url)

        # Mantém a estrutura de pastas
        caminho_local = os.path.join(
            PASTA_DESTINO,
            caminho_relativo.replace("/", os.sep)
        )

        # Cria a pasta necessária
        os.makedirs(
            os.path.dirname(caminho_local),
            exist_ok=True
        )

        print(f"\nBaixando: {url}")

        try:

            resposta = requests.get(
                url,
                stream=True,
                timeout=60
            )

            if resposta.status_code == 200:

                with open(caminho_local, "wb") as arquivo:

                    for bloco in resposta.iter_content(
                        chunk_size=1024 * 1024
                    ):

                        if bloco:
                            arquivo.write(bloco)

                tamanho_mb = os.path.getsize(
                    caminho_local
                ) / (1024 * 1024)

                print(
                    f"OK: {caminho_local} "
                    f"({tamanho_mb:.2f} MB)"
                )

            else:

                print(
                    f"ERRO HTTP {resposta.status_code}: "
                    f"{url}"
                )

        except requests.RequestException as erro:

            print(
                f"ERRO ao baixar {url}: {erro}"
            )

print("\nDownload concluído.")
print(f"Total de arquivos encontrados: {len(urls_baixadas)}")
