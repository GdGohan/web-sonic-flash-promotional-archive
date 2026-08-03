#!/bin/bash

set -Eeuo pipefail

OWNER="GdGohan"
TOKEN="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"
REPO="web-sonic-flash-promotional-archive"
BRANCH="main"

LOCAL_DIR="./"
DEST_BASE="UnleashedEn"

# TOKEN deve estar definido no ambiente

# export TOKEN="seu_token"

if [ -z "${TOKEN:-}" ]; then
echo "ERRO: TOKEN não está definido."
echo
echo 'Use: export TOKEN="seu_token"'
exit 1
fi

command -v git >/dev/null || {
echo "ERRO: git não encontrado."
exit 1
}

[ -d "$LOCAL_DIR" ] || {
echo "ERRO: diretório local não encontrado: $LOCAL_DIR"
exit 1
}

# Diretório temporário

TMPDIR=$(mktemp -d)

cleanup() {
echo
echo "Removendo clone temporário..."
rm -rf "$TMPDIR"
}

trap cleanup EXIT

CLONE_DIR="$TMPDIR/repo"

# URL autenticada usando TOKEN

REMOTE_URL="https://x-access-token:${TOKEN}@github.com/${OWNER}/${REPO}.git"

echo "Clonando temporariamente o branch $BRANCH..."

git clone --branch "$BRANCH" --single-branch "$REMOTE_URL" "$CLONE_DIR"

cd "$CLONE_DIR"

# Evita que o token fique configurado permanentemente no repositório

git remote set-url origin "https://github.com/${OWNER}/${REPO}.git"

echo
echo "Clone temporário criado em:"
echo "$CLONE_DIR"

# ------------------------------------------------------------

# Função: faz um commit local

# ------------------------------------------------------------

commit_group() {
local SOURCE_DIR="$1"
local DEST_DIR="$2"
local MESSAGE="$3"

if [ ! -d "$SOURCE_DIR" ]; then
echo "(diretório não encontrado: $SOURCE_DIR, pulando)"
return 0
fi

echo
echo "Commit: $MESSAGE"
echo "Destino: $DEST_DIR"

mkdir -p "$DEST_DIR"

# Copia o conteúdo mantendo a estrutura

cp -a "$SOURCE_DIR"/. "$DEST_DIR"/

git add "$DEST_DIR"

# Verifica se realmente existem alterações

if git diff --cached --quiet; then
echo "(nenhuma alteração nova, pulando)"
return 0
fi

git commit -m "$MESSAGE"

echo
echo "Commit local criado com sucesso."
}

# ------------------------------------------------------------

# 1. Arquivos soltos na raiz de Night-of-the-Werehog

# ------------------------------------------------------------

ROOT_FILES=$(find "$OLDPWD/$LOCAL_DIR" -maxdepth 1 -type f -print -quit)

if [ -n "$ROOT_FILES" ]; then

mkdir -p "$DEST_BASE"

find "$OLDPWD/$LOCAL_DIR" -maxdepth 1 -type f -exec cp -f {} "$DEST_BASE"/ \;

git add "$DEST_BASE"

if ! git diff --cached --quiet; then
git commit -m "add root swf files"
echo "Commit da raiz criado."
else
echo "Nenhuma alteração nova na raiz."
fi

fi

# ------------------------------------------------------------

# 2. Cada subpasta vira um commit separado

# ------------------------------------------------------------

while IFS= read -r SUBDIR; do

SUBNAME=$(basename "$SUBDIR")

DEST_DIR="$DEST_BASE/$SUBNAME"

echo
echo "Processando pasta: $SUBNAME"

mkdir -p "$DEST_DIR"

cp -a "$SUBDIR"/. "$DEST_DIR"/

git add "$DEST_DIR"

if git diff --cached --quiet; then
echo "(nenhuma alteração nova em $SUBNAME, pulando)"
continue
fi

git commit -m "add $SUBNAME folder"

echo "Commit criado para $SUBNAME."

done < <(
find "$OLDPWD/$LOCAL_DIR" -mindepth 1 -maxdepth 1 -type d
)

# ------------------------------------------------------------

# Push final usando TOKEN

# ------------------------------------------------------------

echo
echo "Enviando commits para o GitHub..."

git push "https://x-access-token:${TOKEN}@github.com/${OWNER}/${REPO}.git" "$BRANCH"

echo
echo "Pronto! Todos os commits foram enviados com sucesso."
