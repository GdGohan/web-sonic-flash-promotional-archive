from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from pathlib import Path
import json


HOST = "localhost"
PORT = 8000

# Pasta onde este arquivo .py está localizado
ROOT = Path(__file__).resolve().parent

GITHUB_API = (
    "https://api.github.com/repos/"
    "ruffle-rs/ruffle/releases"
)


class Handler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(ROOT),
            **kwargs
        )

    def end_headers(self):
        # Permite requisições CORS para o servidor local.
        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "*"
        )

        self.end_headers()

    def do_GET(self):

        # Endpoint usado pelo ruffle.js para obter
        # o ZIP do Nightly sem sofrer com CORS.
        if self.path == "/api/ruffle-zip":
            self.download_ruffle()
            return

        # Qualquer outro caminho é servido normalmente
        # a partir da pasta onde está este Python.
        super().do_GET()

    def download_ruffle(self):

        try:
            print()
            print("[Ruffle Proxy] Consultando releases...")

            # ----------------------------------------
            # 1. Consulta os Nightlies
            # ----------------------------------------

            request = Request(
                GITHUB_API + "?per_page=100",
                headers={
                    "User-Agent": "Ruffle-Nightly-Loader",
                    "Accept": "application/vnd.github+json"
                }
            )

            with urlopen(request) as response:
                releases = json.loads(
                    response.read().decode("utf-8")
                )

            nightlies = [
                release
                for release in releases
                if (
                    release.get("prerelease") is True
                    and release.get(
                        "tag_name",
                        ""
                    ).startswith("nightly-")
                )
            ]

            if not nightlies:
                raise Exception(
                    "Nenhum Nightly do Ruffle encontrado."
                )

            # Ordena pelo lançamento mais recente.
            nightlies.sort(
                key=lambda release:
                    release.get("published_at")
                    or release.get("created_at"),
                reverse=True
            )

            release = nightlies[0]

            print(
                "[Ruffle Proxy] Nightly:",
                release["tag_name"]
            )

            # ----------------------------------------
            # 2. Localiza o web-selfhosted.zip
            # ----------------------------------------

            asset = next(
                (
                    asset
                    for asset in release.get("assets", [])
                    if (
                        "web-selfhosted" in asset.get(
                            "name",
                            ""
                        )
                        and asset.get(
                            "name",
                            ""
                        ).endswith(".zip")
                    )
                ),
                None
            )

            if not asset:
                raise Exception(
                    "O pacote web-selfhosted.zip "
                    "não foi encontrado."
                )

            print(
                "[Ruffle Proxy] Asset:",
                asset["name"]
            )

            # ----------------------------------------
            # 3. Python baixa o ZIP
            #
            # Python pode seguir o redirect do GitHub.
            # CORS não se aplica a essa requisição.
            # ----------------------------------------

            asset_url = asset["browser_download_url"]

            print(
                "[Ruffle Proxy] Baixando ZIP..."
            )

            download_request = Request(
                asset_url,
                headers={
                    "User-Agent": "Ruffle-Nightly-Loader"
                }
            )

            with urlopen(download_request) as response:
                data = response.read()

            print(
                "[Ruffle Proxy] Download concluído:",
                f"{len(data):,}",
                "bytes"
            )

            # ----------------------------------------
            # 4. Envia o ZIP para o navegador
            # ----------------------------------------

            self.send_response(200)

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.send_header(
                "Content-Type",
                "application/zip"
            )

            self.send_header(
                "Content-Length",
                str(len(data))
            )

            self.send_header(
                "Cache-Control",
                "no-store"
            )

            self.send_header(
                "Content-Disposition",
                f'inline; filename="{asset["name"]}"'
            )

            self.end_headers()

            self.wfile.write(data)

            print(
                "[Ruffle Proxy] ZIP enviado ao navegador."
            )

        except Exception as error:

            print()
            print(
                "[Ruffle Proxy] ERRO:",
                repr(error)
            )

            message = str(error).encode("utf-8")

            self.send_response(500)

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(message))
            )

            self.end_headers()

            self.wfile.write(message)


print()
print("========================================")
print(" Servidor local do Ruffle")
print("========================================")
print()
print(f"Pasta:   {ROOT}")
print(f"URL:     http://{HOST}:{PORT}")
print()
print("Proxy do Ruffle:")
print(f"http://{HOST}:{PORT}/api/ruffle-zip")
print()
print("Pressione CTRL+C para parar.")
print()


server = ThreadingHTTPServer(
    (HOST, PORT),
    Handler
)

server.serve_forever()