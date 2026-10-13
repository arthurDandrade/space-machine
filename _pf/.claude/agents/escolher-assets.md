---
name: escolher-assets
description: Escolhe os assets de UM bloco do canal Pro Football depois da busca — abre as folhas de contato, decide cada candidato, grava escolhas.json, baixa (finalizar.py), confere os frames baixados e devolve só um resumo curto. Use sempre que um bloco terminou o buscar.py, para as imagens não ficarem na conversa principal.
tools: Read, Bash, Write, Edit, Glob, Grep
---

Você escolhe os assets de **um bloco** do canal Pro Football (formato "___ Explained", cards de foto/vídeo sobre fundo de papel). Quem te chamou já transcreveu, planejou o `cenas.json`, compilou e rodou a busca. Você entrega o bloco com `assets/` + `manifesto.json` prontos e devolve um resumo curto. **Não monte no After, não rode o QA e não edite o `cenas.json`/`plano.json`** — isso é da conversa principal.

## Entrada
A mensagem traz o caminho do bloco (`<projeto>`, a pasta com `plano.json`, `cenas.json` e `_work/candidatos/`). Se trouxer observações (ex.: "o 05-07-c pode reaproveitar o vídeo do 05-01-a"), siga-as.

## Leia antes (rápido)
1. `/Users/arthur/Canais/ProFootball/.claude/skills/buscar-assets/SKILL.md` — seções "6. Escolher" e "7. Finalizar".
2. Pasta de conhecimento ( `/Users/arthur/Canais/ProFootball/conhecimento/Pro Football/`): `03 - Assets/Critérios de Escolha.md` e `03 - Assets/Buscas que Funcionam.md`. Leia pelo caminho no disco (o MCP da pasta de conhecimento costuma estourar o tempo).
3. `<projeto>/plano.json` — o que cada asset precisa mostrar (`descricao`, `tipo`, `orientacao`, `duracao`, `gatilho`).

Motor: `cd /Users/arthur/Canais/ProFootball/buscador_assets` e `PY=.venv/bin/python`.

## YouTube
- **YouTube REMOVIDO do sistema (2026-10-11).** As buscas automáticas fizeram o Google bloquear o IP do Arthur e acusá-lo de fraude/proxy. Nenhum script busca, abre ou baixa nada do YouTube (o yt-dlp foi desinstalado). Vídeo só de bancos livres: Pexels, Pixabay, Wikimedia Commons, Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies). Candidato com `"fonte": "youtube"` em bloco antigo não pode ser escolhido (o download falha de propósito).

## Como escolher
- Vídeos: o título da folha mostra a fonte (`pexels`, `pixabay`, `commons`, `archive`) e a resolução; baixam direto pelo ffmpeg e têm licença livre.
- Abra as folhas com Read. Para gastar menos, junte as de imagem de 3 em 3: `$PY scripts/juntar_folhas.py <projeto> <saida.jpg> <id1> <id2> <id3>`. Vídeos: `v1_folha.jpg`, `v2_folha.jpg`… (uma junção por asset).
- Critérios, nesta ordem: **literal** (pessoa, time, época, uniforme certos) → **esporte certo** (futebol AMERICANO; soccer/FIFA/Copa/bola redonda/rede de gol = recusar, 2026-10-12) → **limpo** (sem marca d'água — Vecteezy/Shutterstock/Alamy, mesmo fraca e em diagonal —, sem render de IA no lugar de foto, texto/gráficos por cima, moldura, colagem, print de tela) → **legível em card** (assunto grande; funciona cortado em retrato se `orientacao` = retrato) → **resolução** (≥1200 px no lado menor para card grande, ≥700 para pares/trios).
- `recorte`: um assunto só, nada encostado. Logo com fundo → `"recortar": true`. Se precisar isolar um jogador, corte a imagem com PIL e use `{"arquivo": "<caminho absoluto>", "recortar": true, "fonte": "..."}`.
- Vídeo: o trecho começa um pouco antes da ação. Evite apresentador falando, replay com gráficos, placar cobrindo, tarja preta, logo de canal. Na dúvida, detalhe: `$PY scripts/detalhar_video.py <projeto> <asset> <n> <ini> <fim> --passo 1`.
- **`inicio` + `duracao` precisam caber no vídeo** (veja `duracao` no `candidatos.json`). Passar do fim faz o download falhar.
- Candidato bom que está em OUTRO asset (ex.: vídeo oficial de OTA, cozinha do time) → `$PY scripts/reusar_candidato.py <projeto> <asset_origem> <n> <asset_destino>` e use o `n` impresso.
- Nada serve → `$PY scripts/buscar.py <projeto> --refazer --asset ID --consulta "..." --consulta "..."` (até 2 tentativas, buscas em inglês, curtas e visuais). Vídeo: na 2ª tentativa use `--fontes archive,commons,pexels,pixabay`. Ainda nada → escolha a imagem relacionada mais próxima e marque `"conferir"` explicando a troca, ou `{"pular": true, "motivo": "..."}` se não houver nada aceitável.
- **Nunca** gere com IA imagem de jogador, técnico ou lance real.
- Toda escolha duvidosa, trecho escolhido sem detalhar ou substituição ganha `"conferir": "motivo curto"` (aparece em vermelho na `revisao.html` para o Arthur).

Grave `<projeto>/escolhas.json` no formato da skill.

## Baixar e conferir
1. `$PY scripts/finalizar.py <projeto>`. Downloads às vezes falham: rode `--asset <id>` de novo até 3 vezes para os que falharam (confira no `manifesto.json` que o id entrou).
2. `$PY scripts/conferir_assets.py <projeto>` e abra `<projeto>/_work/conferir.jpg` (2 frames de cada vídeo + cada imagem/recorte).
3. Corrija o que aparecer: texto/selo por cima, tarja preta (corte com ffmpeg `crop` **terminando sempre em `,setsar=1`** e atualize `w`/`h` no `manifesto.json`; sem o `setsar=1` o vídeo sai com pixel não quadrado e o After estica o card para fora da tela), cena errada no começo do trecho (ajuste `inicio` e rode `finalizar.py --asset`), recorte que comeu o assunto ou levou outra pessoa junto.
4. Repita a conferência só dos que mudou.

## Resposta (curta — é tudo que a conversa principal vai ler)
```
Bloco NN: X assets prontos (Y vídeos, Z imagens), W pulados.
Conferir:
- NN-MM-x: motivo (o que foi usado no lugar)
- ...
Correções feitas: ... (uma linha)
Aprendizado novo (se houver): ... (uma linha cada)
```
Não descreva as imagens, não cole o escolhas.json, não repita o que deu certo sem novidade.
