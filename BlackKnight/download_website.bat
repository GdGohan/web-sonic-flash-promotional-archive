@echo off
title Mirror do site - site

REM Altere este caminho para onde deseja salvar os arquivos
cd /d "%~dp0"

wget ^
  --mirror ^
  --page-requisites ^
  --convert-links ^
  --adjust-extension ^
  --restrict-file-names=windows ^
  --trust-server-names ^
  --no-parent ^
  https://sonic.sega.jp/ankokunokishi/SpecialMovie

echo.
echo ==========================================
echo Download concluido!
echo ==========================================
pause