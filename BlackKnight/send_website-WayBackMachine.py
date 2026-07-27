import re
import sqlite3
import time
import sys
from urllib.parse import urljoin, urldefrag, urlparse

import requests
from bs4 import BeautifulSoup


# ==============================
# CONFIGURAÇÃO
# ==============================

START_URL = "https://sonic.sega.jp/ankokunokishi/SpecialMovie/"

DELAY = 6

EXTENSIONS = (
    ".html", ".htm", ".xhtml",
    ".css", ".js",
    ".jpg", ".jpeg", ".png", ".gif",
    ".ico", ".svg",
    ".swf", ".flv",
    ".xml", ".rdf",
    ".mp3", ".wav",
    ".mp4",
    ".json"
)


# ==============================

session = requests.Session()

session.headers.update({
    "User-Agent":
    "Mozilla/5.0 SitePreserver/1.0"
})


# ==============================
# BANCO
# ==============================

db = sqlite3.connect("archive.db")

cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS urls (
    url TEXT PRIMARY KEY,
    visited INTEGER DEFAULT 0,
    sent INTEGER DEFAULT 0
)
""")

db.commit()


# ==============================
# CONTROLE DE URL
# ==============================

def allowed(url):

    return url.startswith(START_URL)


def normalize(url):

    url = urldefrag(url)[0]

    return url.rstrip("/") if url != START_URL else url


def add_url(url):

    url = normalize(url)

    if not allowed(url):
        return

    cur.execute(
        "INSERT OR IGNORE INTO urls(url) VALUES(?)",
        (url,)
    )

    db.commit()



# ==============================
# EXTRATOR DE LINKS
# ==============================

def extract_links(base, content):

    found = set()


    # HTML

    try:

        soup = BeautifulSoup(
            content,
            "html.parser"
        )

        for tag in soup.find_all(True):

            for attr in ("href", "src", "data"):

                link = tag.get(attr)

                if link:

                    found.add(
                        urljoin(base, link)
                    )


    except:

        pass



    # CSS / JS

    regex = r"""
    (?:
        ["'(]
    )
    (
    [^"'() ]+\.(?:html?|css|js|png|jpg|jpeg|gif|ico|swf|flv|xml|rdf|mp3|wav)
    )
    """

    matches = re.findall(
        regex,
        content,
        re.I | re.X
    )


    for m in matches:

        found.add(
            urljoin(base, m)
        )


    return found



# ==============================
# CRAWLER
# ==============================


def crawl():

    print("\n=== CRAWL ===\n")


    add_url(START_URL)


    while True:

        cur.execute("""
        SELECT url FROM urls
        WHERE visited=0
        LIMIT 1
        """)

        row = cur.fetchone()


        if not row:
            break


        url = row[0]


        print("[SCAN]", url)


        try:

            r = session.get(
                url,
                timeout=30
            )


        except Exception:

            cur.execute(
                "UPDATE urls SET visited=1 WHERE url=?",
                (url,)
            )

            db.commit()

            continue



        cur.execute(
            "UPDATE urls SET visited=1 WHERE url=?",
            (url,)
        )

        db.commit()



        content_type = r.headers.get(
            "content-type",
            ""
        )


        # tenta analisar qualquer recurso textual

        if (
            "html" in content_type
            or "javascript" in content_type
            or "css" in content_type
            or url.endswith(
                (".js",".css",".html",".htm")
            )
        ):

            for link in extract_links(
                url,
                r.text
            ):

                add_url(link)



    print("\nCrawl terminado.\n")



# ==============================
# WAYBACK
# ==============================


def send_wayback():


    print("\n=== WAYBACK ===\n")


    cur.execute("""
    SELECT url FROM urls
    WHERE sent=0
    ORDER BY url
    """)


    urls = cur.fetchall()

    total = len(urls)


    for i, row in enumerate(urls,1):


        url = row[0]


        print(
            f"[{i}/{total}] {url}"
        )


        while True:

            try:

                r = session.post(
                    "https://web.archive.org/save",
                    data={
                        "url": url
                    },
                    timeout=90
                )


                if r.status_code == 429:

                    print(
                        "Limite Wayback. Esperando..."
                    )

                    time.sleep(60)

                    continue


                break


            except Exception as e:


                print(e)

                time.sleep(30)



        print(
            "Status:",
            r.status_code
        )


        cur.execute("""
        UPDATE urls
        SET sent=1
        WHERE url=?
        """,
        (url,))


        db.commit()


        time.sleep(DELAY)



# ==============================
# EXPORTAR
# ==============================


def export():

    with open(
        "urls.txt",
        "w",
        encoding="utf-8"
    ) as f:


        for row in cur.execute(
            "SELECT url FROM urls ORDER BY url"
        ):

            f.write(
                row[0]+"\n"
            )



# ==============================

if __name__ == "__main__":


    crawl()

    export()


    print(
        "URLs encontradas:"
    )

    cur.execute(
        "SELECT COUNT(*) FROM urls"
    )

    print(
        cur.fetchone()[0]
    )


    send_wayback()


    print("\nFINALIZADO")