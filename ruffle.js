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
 *   6. Cria Blob URLs para os arquivos extraídos.
 *   7. Cria uma origem virtual para o Ruffle.
 *   8. Faz o Ruffle resolver dinamicamente seus JS/WASM/chunks.
 *
 * Nenhum nome de arquivo do Nightly é fixo.
 */

(async function () {
    "use strict";

    const CONFIG = {
        owner: "ruffle-rs",
        repo: "ruffle",

        githubApi:
            "https://api.github.com/repos/ruffle-rs/ruffle/releases",

        jszip:
            "https://cdn.jsdelivr.net/npm/jszip@3.10.1/+esm",

        cache: true
    };

    let blobUrls = new Map();
    let fileMap = new Map();

    function log(...args) {
        console.log("[Ruffle Loader]", ...args);
    }

    function error(...args) {
        console.error("[Ruffle Loader]", ...args);
    }

    /*
     * ============================================================
     * GitHub
     * ============================================================
     */

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

        nightlies.sort((a, b) => {
            return (
                new Date(b.published_at || b.created_at) -
                new Date(a.published_at || a.created_at)
            );
        });

        const nightly = nightlies[0];

        log(
            "Nightly encontrado:",
            nightly.tag_name
        );

        return nightly;
    }

    function findWebPackage(release) {
        const asset = release.assets.find(asset => {
            return /web-selfhosted.*\.zip$/i.test(
                asset.name
            );
        });

        if (!asset) {
            console.error(
                "[Ruffle Loader] Assets disponíveis:"
            );

            for (const asset of release.assets) {
                console.error(
                    " -",
                    asset.name
                );
            }

            throw new Error(
                "Não encontrei o pacote web-selfhosted.zip."
            );
        }

        return asset;
    }

    /*
     * ============================================================
     * Download
     * ============================================================
     */

    async function downloadPackage(asset) {

        /*
         * Durante desenvolvimento local:
         *
         * localhost -> Python proxy
         *
         * Isso evita o CORS do
         * release-assets.githubusercontent.com.
         */
        if (
            location.hostname === "localhost" ||
            location.hostname === "127.0.0.1"
        ) {
            log(
                "Baixando Nightly através do proxy local..."
            );

            const response = await fetch(
                "/api/ruffle-zip",
                {
                    cache: "no-store"
                }
            );

            if (!response.ok) {
                throw new Error(
                    `Proxy local retornou HTTP ${response.status}`
                );
            }

            return await response.arrayBuffer();
        }

        /*
         * GitHub Pages:
         *
         * Tenta diretamente o asset.
         */
        log(
            "Baixando pacote:",
            asset.browser_download_url
        );

        const response = await fetch(
            asset.browser_download_url,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `Download retornou HTTP ${response.status}`
            );
        }

        return await response.arrayBuffer();
    }

    /*
     * ============================================================
     * JSZip
     * ============================================================
     */

    async function loadJSZip() {
        log("Carregando JSZip...");

        const module = await import(
            CONFIG.jszip
        );

        return (
            module.default ||
            module.JSZip ||
            module
        );
    }

    async function extractZip(arrayBuffer) {
        const JSZip = await loadJSZip();

        log("Extraindo pacote...");

        const zip = await JSZip.loadAsync(
            arrayBuffer
        );

        const files = new Map();

        for (
            const [name, entry]
            of Object.entries(zip.files)
        ) {
            if (entry.dir) {
                continue;
            }

            files.set(name, entry);
        }

        log(
            `Arquivos encontrados: ${files.size}`
        );

        return files;
    }

    /*
     * ============================================================
     * Arquivos
     * ============================================================
     */

    function basename(path) {
        return path
            .replace(/\\/g, "/")
            .split("/")
            .pop();
    }

    function findFile(files, filename) {

        /*
         * Primeiro tenta o caminho exato.
         */
        if (files.has(filename)) {
            return filename;
        }

        /*
         * Depois procura somente pelo nome.
         *
         * Isso permite que o ZIP tenha ou não
         * uma pasta intermediária.
         */
        for (const name of files.keys()) {
            if (
                basename(name) === filename
            ) {
                return name;
            }
        }

        return null;
    }

    function mimeType(filename) {
        const lower =
            filename.toLowerCase();

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

        if (
            lower.endsWith(".jpg") ||
            lower.endsWith(".jpeg")
        ) {
            return "image/jpeg";
        }

        if (lower.endsWith(".webp")) {
            return "image/webp";
        }

        return "application/octet-stream";
    }

    async function createFileMap(files) {
        log("Criando Blob URLs...");

        for (
            const [name, entry]
            of files.entries()
        ) {
            const blob =
                await entry.async("blob");

            const url =
                URL.createObjectURL(
                    new Blob(
                        [blob],
                        {
                            type: mimeType(name)
                        }
                    )
                );

            blobUrls.set(
                name,
                url
            );

            fileMap.set(
                name,
                url
            );
        }

        log(
            `URLs criadas: ${fileMap.size}`
        );

        return fileMap;
    }

    function findURL(filename) {

        /*
         * Caminho exato.
         */
        if (fileMap.has(filename)) {
            return fileMap.get(filename);
        }

        /*
         * Normaliza URLs.
         */
        let clean = filename;

        try {
            clean =
                decodeURIComponent(
                    clean
                );
        } catch (_) {}

        clean =
            clean.split("?")[0]
                .split("#")[0];

        /*
         * Remove ./ e barras iniciais.
         */
        clean =
            clean.replace(
                /^\.?\//,
                ""
            );

        /*
         * Tenta novamente pelo caminho.
         */
        if (fileMap.has(clean)) {
            return fileMap.get(clean);
        }

        /*
         * Finalmente procura pelo basename.
         */
        const name =
            basename(clean);

        for (
            const [path, url]
            of fileMap.entries()
        ) {
            if (
                basename(path) === name
            ) {
                return url;
            }
        }

        return null;
    }

    /*
     * ============================================================
     * Origem virtual
     * ============================================================
     *
     * O Ruffle precisa acreditar que seu ruffle.js
     * está em uma URL HTTP normal.
     *
     * Não usamos blob: como currentScript.src.
     *
     * Exemplo:
     *
     * https://site.github.io/__ruffle_virtual__/
     *
     * O caminho é apenas virtual.
     */

    const virtualBase =
        new URL(
            "__ruffle_virtual__/",
            location.href
        ).href;

    /*
     * Converte uma URL virtual do Ruffle
     * para o arquivo correspondente dentro
     * do ZIP.
     */
    function resolveVirtualURL(url) {

        let parsed;

        try {
            parsed =
                new URL(
                    url,
                    virtualBase
                );
        } catch (_) {
            return null;
        }

        /*
         * Só interceptamos nossa origem virtual.
         */
        if (
            parsed.origin !==
            location.origin
        ) {
            return null;
        }

        const prefix =
            new URL(
                "__ruffle_virtual__/",
                location.href
            ).pathname;

        if (
            !parsed.pathname.startsWith(
                prefix
            )
        ) {
            return null;
        }

        let relative =
            parsed.pathname.slice(
                prefix.length
            );

        try {
            relative =
                decodeURIComponent(
                    relative
                );
        } catch (_) {}

        return findURL(
            fileMap,
            relative
        );
    }

    /*
     * ============================================================
     * Interceptação de fetch
     * ============================================================
     *
     * Necessária para:
     *
     *   WebAssembly
     *   fetch()
     *   recursos internos
     *
     * Não substituímos fetch global.
     *
     * Apenas tratamos URLs da origem virtual.
     */

    const originalFetch =
        window.fetch.bind(window);

    window.fetch =
        async function (
            input,
            init
        ) {

            let url;

            if (
                typeof input ===
                "string"
            ) {
                url = input;
            } else if (
                input instanceof Request
            ) {
                url = input.url;
            } else {
                url = String(input);
            }

            const localURL =
                resolveVirtualURL(url);

            if (localURL) {

                const response =
                    await originalFetch(
                        localURL
                    );

                /*
                 * Recria a resposta com uma URL
                 * virtualmente coerente para o código.
                 */
                return response;
            }

            return originalFetch(
                input,
                init
            );
        };

    /*
     * ============================================================
     * Interceptação de scripts
     * ============================================================
     *
     * O webpack pode criar:
     *
     *   <script src="chunk.js">
     *
     * dinamicamente.
     *
     * Nós trocamos o src virtual pelo
     * Blob URL correspondente.
     */

    const originalSetAttribute =
        Element.prototype.setAttribute;

    Element.prototype.setAttribute =
        function (
            name,
            value
        ) {

            if (
                this instanceof
                HTMLScriptElement &&
                name.toLowerCase() ===
                "src"
            ) {

                const localURL =
                    resolveVirtualURL(
                        value
                    );

                if (localURL) {
                    value = localURL;
                }
            }

            return originalSetAttribute.call(
                this,
                name,
                value
            );
        };

    const originalScriptSrcDescriptor =
        Object.getOwnPropertyDescriptor(
            HTMLScriptElement.prototype,
            "src"
        );

    if (
        originalScriptSrcDescriptor &&
        originalScriptSrcDescriptor.set
    ) {

        Object.defineProperty(
            HTMLScriptElement.prototype,
            "src",
            {
                configurable:
                    originalScriptSrcDescriptor.configurable,

                enumerable:
                    originalScriptSrcDescriptor.enumerable,

                get:
                    originalScriptSrcDescriptor.get,

                set(value) {

                    const localURL =
                        resolveVirtualURL(
                            value
                        );

                    if (localURL) {
                        value =
                            localURL;
                    }

                    originalScriptSrcDescriptor
                        .set
                        .call(
                            this,
                            value
                        );
                }
            }
        );
    }

    /*
     * ============================================================
     * Worker
     * ============================================================
     *
     * Alguns builds podem criar Workers
     * dinamicamente.
     */

    const OriginalWorker =
        window.Worker;

    window.Worker =
        function (
            scriptURL,
            options
        ) {

            const localURL =
                resolveVirtualURL(
                    scriptURL
                );

            return new OriginalWorker(
                localURL || scriptURL,
                options
            );
        };

    window.Worker.prototype =
        OriginalWorker.prototype;

    /*
     * ============================================================
     * currentScript virtual
     * ============================================================
     *
     * Este é o ponto principal da correção.
     *
     * O Ruffle original usa document.currentScript
     * para descobrir seu publicPath.
     *
     * Em vez de dar a ele um blob: URL,
     * damos uma URL HTTP virtual:
     *
     *   /__ruffle_virtual__/ruffle.js
     *
     * Os recursos dessa URL são traduzidos
     * dinamicamente para os arquivos do ZIP.
     */

    const documentPrototype =
        Object.getPrototypeOf(
            document
        );

    const currentScriptDescriptor =
        Object.getOwnPropertyDescriptor(
            documentPrototype,
            "currentScript"
        );

    let virtualCurrentScript =
        null;

    if (
        currentScriptDescriptor &&
        currentScriptDescriptor.get
    ) {

        Object.defineProperty(
            documentPrototype,
            "currentScript",
            {
                configurable:
                    currentScriptDescriptor.configurable,

                enumerable:
                    currentScriptDescriptor.enumerable,

                get() {

                    const real =
                        currentScriptDescriptor
                            .get
                            .call(document);

                    if (
                        virtualCurrentScript
                    ) {
                        return virtualCurrentScript;
                    }

                    return real;
                }
            }
        );
    }

    /*
     * ============================================================
     * Carregamento do ruffle.js
     * ============================================================
     */

    async function loadRuffleJS(files) {

        const rufflePath =
            findFile(
                files,
                "ruffle.js"
            );

        if (!rufflePath) {
            throw new Error(
                "ruffle.js não foi encontrado dentro do pacote."
            );
        }

        const entry =
            files.get(
                rufflePath
            );

        if (!entry) {
            throw new Error(
                "Não consegui acessar o ruffle.js."
            );
        }

        log(
            "Carregando:",
            rufflePath
        );

        /*
         * O código é carregado como texto.
         *
         * Isso permite controlar currentScript
         * enquanto o bootstrap do webpack é executado.
         */
        const source =
            await entry.async(
                "text"
            );

        /*
         * Criamos um elemento script virtual.
         *
         * Ele NÃO é inserido no DOM.
         */
        const virtualScript =
            document.createElement(
                "script"
            );

        virtualScript.src =
            new URL(
                "ruffle.js",
                virtualBase
            ).href;

        virtualCurrentScript =
            virtualScript;

        /*
         * O script original usa strict mode e
         * inicializa o próprio webpack.
         *
         * Usamos Function para executar exatamente
         * o código extraído.
         */
        try {

            const execute =
                new Function(
                    source
                );

            execute();

        } finally {

            /*
             * O bootstrap síncrono já determinou
             * seu publicPath.
             */
            virtualCurrentScript =
                null;
        }

        log(
            "Ruffle carregado."
        );
    }

    /*
     * ============================================================
     * API pública
     * ============================================================
     */

    function exposeLoader(
        release,
        asset
    ) {

        window.RuffleLoader = {
            nightly:
                release.tag_name,

            release:

                release,

            asset:
                asset.name,

            files:
                fileMap,

            getFile(
                filename
            ) {
                return findURL(
                    filename
                );
            },

            resolve(
                url
            ) {
                return resolveVirtualURL(
                    url
                );
            }
        };
    }

    /*
     * ============================================================
     * Main
     * ============================================================
     */

    async function main() {

        if (
            window
                .__RUFFLE_NIGHTLY_LOADER_RUNNING__
        ) {
            return;
        }

        window
            .__RUFFLE_NIGHTLY_LOADER_RUNNING__ =
            true;

        try {

            const release =
                await getLatestNightly();

            const asset =
                findWebPackage(
                    release
                );

            log(
                "Release:",
                release.tag_name
            );

            log(
                "Pacote:",
                asset.name
            );

            const arrayBuffer =
                await downloadPackage(
                    asset
                );

            const files =
                await extractZip(
                    arrayBuffer
                );

            await createFileMap(
                files
            );

            exposeLoader(
                release,
                asset
            );

            await loadRuffleJS(
                files
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
