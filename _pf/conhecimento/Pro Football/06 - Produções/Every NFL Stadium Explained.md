---
tags: [pro-football, producao]
criado: 2026-10-09
pasta: /Users/arthur/Canais/ProFootball/producoes/videos/every-nfl-stadium-explained/
---

# Every NFL Stadium Explained

Voltar: [[00 - Pro Football (Índice)]] · Log: [[Log de Aprendizados]]

30 estádios, um bloco por tópico em `blocos/NN/`. Primeiro vídeo com a **narração gerada pela API do DarkPlanner**, voz Clark, **tópico por tópico** (`buscador_assets/scripts/gerar_narracao.py blocos/NN`). Roteiro do Arthur em `roteiro_original.txt`; dividido em `roteiro_completo.txt` e `blocos/NN/roteiro.txt`.

Combinado em 2026-10-09: fazer só o tópico 1 primeiro, para o Arthur sentir como o sistema está rodando.

| Bloco | Tópico | Duração | Status |
|---|---|---|---|
| 01 | Soldier Field | 76 s | ✅ prévia aprovada no QA (0 falhas) em 2026-10-11 → `edicao/bloco 1.mp4` · 25 assets (9 vídeos escolhidos pelo Estúdio) · Arthur conferir: 01-03-c (Soldier ou Wrigley?), 01-04-b (anos 90?), 01-02-c (colunas de longe, drone), 01-10-e (640×360) |
| 02 | Lambeau Field | 85 s | ✅ prévia aprovada no QA (0 falhas) em 2026-10-11 → `edicao/bloco 2.mp4` · 1º bloco feito do começo ao fim pelo Estúdio (`python -m estudio rodar`) · narração `s2.1-pro-free` (API do Fish Audio sem crédito) · 28 assets, **todos imagens** (sem YouTube, nenhum vídeo de banco livre serviu; 4 vídeos viraram foto) · conferir: as fotos marcadas na `revisao.html` |
| 03 | Arrowhead Stadium | — | roteiro pronto |
| 04 | Caesars Superdome | — | roteiro pronto |
| 05 | Hard Rock Stadium | — | roteiro pronto |
| 06 | EverBank Stadium | — | roteiro pronto |
| 07 | Bank of America Stadium | — | roteiro pronto |
| 08 | Northwest Stadium | — | roteiro pronto |
| 09 | Raymond James Stadium | — | roteiro pronto |
| 10 | M&T Bank Stadium | — | roteiro pronto |
| 11 | Huntington Bank Field | — | roteiro pronto |
| 12 | Nissan Stadium | — | roteiro pronto |
| 13 | Paycor Stadium | — | roteiro pronto |
| 14 | Acrisure Stadium | — | roteiro pronto |
| 15 | Empower Field at Mile High | — | roteiro pronto |
| 16 | Ford Field | — | roteiro pronto |
| 17 | Gillette Stadium | — | roteiro pronto |
| 18 | Lumen Field | — | roteiro pronto |
| 19 | Reliant Stadium | — | roteiro pronto |
| 20 | Lincoln Financial Field | — | roteiro pronto |
| 21 | State Farm Stadium | — | roteiro pronto |
| 22 | Lucas Oil Stadium | — | roteiro pronto |
| 23 | AT&T Stadium | — | roteiro pronto |
| 24 | MetLife Stadium | — | roteiro pronto |
| 25 | Levi's Stadium | — | roteiro pronto |
| 26 | U.S. Bank Stadium | — | roteiro pronto |
| 27 | Mercedes-Benz Stadium | — | roteiro pronto |
| 28 | Allegiant Stadium | — | roteiro pronto |
| 29 | SoFi Stadium | — | roteiro pronto |
| 30 | Highmark Stadium | — | roteiro pronto |

## Para retomar (sessão nova)
- Pelo painel do Estúdio (http://localhost:8765 › Every NFL Stadium Explained): abrir o próximo bloco (03) e clicar em **Rodar**. Ele faz narração → transcrição → storyboard → busca → escolha → After + QA → `edicao/bloco N.mp4`.
- Ou pelo Terminal: `cd /Users/arthur/Canais/Estudio && .venv/bin/python -m estudio rodar /Users/arthur/Canais/ProFootball/producoes/videos/every-nfl-stadium-explained/blocos/03`.
- Sem YouTube (removido em 2026-10-11): vídeo só de banco livre, e o que não existe vira foto automaticamente.
- Narração: a API do Fish Audio está sem crédito. Antes de rodar, pôr `s2.1-pro-free` no campo Modelo do menu APIs (ou colocar crédito).
