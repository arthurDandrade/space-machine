@echo off
rem Space Machine pelo Prompt de Comando: repassa tudo para o spacemachine.ps1 (veja os comandos lá).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0spacemachine.ps1" %*
