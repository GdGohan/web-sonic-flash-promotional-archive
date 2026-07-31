/*
 * ruffle.js - Ruffle Nightly Self-Hosted Loader
 *
 * Uso:
 *
 *   <script src="https://SEU-USUARIO.github.io/SEU-REPO/ruffle.js"></script>
 *
 * O script:
 *   1. Consulta os Nightlies do Ruffle no GitHub.
 *   2. Descobre o Nightly mais recente.
 *   3. Localiza o pacote web-selfhosted.zip.
 *   4. Baixa o ZIP.
 *   5. Extrai os arquivos em memória.
 *   6. Publica os arquivos extraídos através de Blob URLs.
 *   7. Carrega o ruffle.js original.
 *
 * Não precisa armazenar o Ruffle no GitHub Pages.
 */

(async function () {
    "use strict";

    const CONFIG = {
        owner: "ruffle-rs",
        repo: "ruffle",

        githubApi:
            "https://api.github.com/repos/ruffle-rs/ruffle/releases",

        // JSZip usado somente para abrir o ZIP no navegador.
        jszip:
            "https://cdn.jsdelivr.net/npm/jszip@3.10.1/+esm",

        // Cache em memória durante a página atual.
        cache: true
    };

    let zipCache = null;
    let blobUrls = new Map();

    function log(...args) {
        console.log("[Ruffle Loader]", ...args);
    }

    function error(...args) {
        console.error("[Ruffle Loader]", ...args);
    }

    async function getLatestNightly() {
        log("Consultando releases do Ruffle...");

        const response = await fetch(
            CONFIG.githubApi + "?per_page=100",
            {
                headers: {
                    "Accept": "application/vnd.github+json"
                },
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `GitHub API retornou HTTP ${response.status}`
            );
        }

        const releases = await response.json();

        /*
         * Os Nightlies atuais são releases como:
         *
         * nightly-2026-04-19
         *
         * e são marcados como prerelease.
         */
        const nightlies = releases.filter(release => {
            return (
                release.prerelease === true &&
                /^nightly-\d{4}-\d{2}-\d{2}$/i.test(
                    release.tag_name
                )
            );
        });

        if (!nightlies.length) {
            throw new Error(
                "Nenhum Nightly do Ruffle foi encontrado."
            );
        }

        // A API normalmente já retorna por data decrescente,
        // mas ordenamos explicitamente para não depender disso.
        nightlies.sort((a, b) => {
            return (
                new Date(b.published_at || b.created_at) -
                new Date(a.published_at || a.created_at)
            );
        });

        const nightly = nightlies[0];

        log("Nightly encontrado:", nightly.tag_name);

        return nightly;
    }

    function findWebPackage(release) {
        /*
         * Procuramos pelo asset cujo nome contenha:
         *
         * web-selfhosted
         *
         * O nome exato do ZIP pode mudar entre builds.
         */
        const asset = release.assets.find(asset => {
            return /web-selfhosted.*\.zip$/i.test(asset.name);
        });

        if (!asset) {
            console.error(
                "[Ruffle Loader] Assets disponíveis:"
            );

            for (const asset of release.assets) {
                console.error(" -", asset.name);
            }

            throw new Error(
                "Não encontrei o pacote web-selfhosted.zip."
            );
        }

        return asset;
    }

    async function downloadPackage(url) {
        log("Baixando pacote:", url);

        const response = await fetch(url, {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(
                `Download do Ruffle falhou: HTTP ${response.status}`
            );
        }

        return await response.arrayBuffer();
    }

    async function loadJSZip() {
        log("Carregando JSZip...");

        const module = await import(CONFIG.jszip);

        /*
         * O +esm do jsDelivr pode expor JSZip diretamente
         * ou através do default.
         */
        return module.default || module.JSZip || module;
    }

    async function extractZip(arrayBuffer) {
        const JSZip = await loadJSZip();

        log("Extraindo pacote...");

        const zip = await JSZip.loadAsync(arrayBuffer);

        const files = new Map();

        for (const [name, entry] of Object.entries(zip.files)) {
            if (entry.dir) {
                continue;
            }

            files.set(name, entry);
        }

        log(`Arquivos encontrados: ${files.size}`);

        return {
            zip,
            files
        };
    }

    function basename(file) {
        return file.split("/").pop();
    }

    function findFile(files, filename) {
        /*
         * Primeiro tenta exatamente.
         */
        if (files.has(filename)) {
            return filename;
        }

        /*
         * Depois procura pelo nome independentemente
         * dos diretórios existentes dentro do ZIP.
         */
        for (const name of files.keys()) {
            if (basename(name) === filename) {
                return name;
            }
        }

        return null;
    }

    async function createBlobURL(entry, mime) {
        const data = await entry.async("blob");

        const blob = new Blob(
            [data],
            {
                type: mime || "application/octet-stream"
            }
        );

        const url = URL.createObjectURL(blob);

        blobUrls.set(url, true);

        return url;
    }

    function mimeType(filename) {
        const lower = filename.toLowerCase();

        if (lower.endsWith(".js")) {
            return "text/javascript";
        }

        if (lower.endsWith(".wasm")) {
            return "application/wasm";
        }

        if (lower.endsWith(".json")) {
            return "application/json";
        }

        if (lower.endsWith(".css")) {
            return "text/css";
        }

        if (lower.endsWith(".html")) {
            return "text/html";
        }

        if (lower.endsWith(".svg")) {
            return "image/svg+xml";
        }

        if (lower.endsWith(".png")) {
            return "image/png";
        }

        if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
            return "image/jpeg";
        }

        if (lower.endsWith(".wasm")) {
            return "application/wasm";
        }

        return "application/octet-stream";
    }

    async function createFileMap(files) {
        const result = new Map();

        log("Criando Blob URLs...");

        for (const [name, entry] of files.entries()) {
            const url = await createBlobURL(
                entry,
                mimeType(name)
            );

            result.set(name, url);
        }

        return result;
    }

    function findURL(fileMap, filename) {
        if (fileMap.has(filename)) {
            return fileMap.get(filename);
        }

        for (const [name, url] of fileMap.entries()) {
            if (basename(name) === filename) {
                return url;
            }
        }

        return null;
    }

    async function loadRuffleJS(files, fileMap) {
        /*
         * O arquivo original do pacote.
         */
        const rufflePath = findFile(files, "ruffle.js");

        if (!rufflePath) {
            throw new Error(
                "ruffle.js não foi encontrado dentro do pacote."
            );
        }

        const ruffleURL = fileMap.get(rufflePath);

        if (!ruffleURL) {
            throw new Error(
                "Não consegui criar a URL do ruffle.js."
            );
        }

        log("Carregando:", rufflePath);

        /*
         * Antes de carregar, disponibilizamos informações
         * para o Ruffle loader.
         *
         * Alguns builds podem procurar seus recursos
         * relativamente ao próprio script.
         */
        window.RuffleLoader = {
            nightly: window.RuffleLoader?.nightly,
            files: fileMap,
            getFile: function (filename) {
                return findURL(fileMap, filename);
            }
        };

        /*
         * Carrega o ruffle.js original.
         */
        await new Promise((resolve, reject) => {
            const script = document.createElement("script");

            script.src = ruffleURL;

            script.onload = resolve;

            script.onerror = function () {
                reject(
                    new Error(
                        "Falha ao carregar o ruffle.js original."
                    )
                );
            };

            document.head.appendChild(script);
        });

        log("Ruffle carregado.");
    }

    async function main() {
        /*
         * Evita inicializar duas vezes.
         */
        if (window.__RUFFLE_NIGHTLY_LOADER_RUNNING__) {
            return;
        }

        window.__RUFFLE_NIGHTLY_LOADER_RUNNING__ = true;

        try {
            const release = await getLatestNightly();

            const asset = findWebPackage(release);

            log("Release:", release.tag_name);
            log("Pacote:", asset.name);

            const arrayBuffer =
                await downloadPackage(
                    asset.browser_download_url
                );

            const extracted =
                await extractZip(arrayBuffer);

            const fileMap =
                await createFileMap(
                    extracted.files
                );

            window.RuffleLoader = {
                nightly: release.tag_name,
                release: release,
                asset: asset.name,
                files: fileMap,

                getFile(filename) {
                    return findURL(
                        fileMap,
                        filename
                    );
                }
            };

            await loadRuffleJS(
                extracted.files,
                fileMap
            );

            log(
                "Ruffle Nightly inicializado:",
                release.tag_name
            );
        } catch (err) {
            error(
                "Não foi possível carregar o Ruffle Nightly.",
                err
            );
        }
    }

    /*
     * Começa imediatamente.
     */
    main();
})();
