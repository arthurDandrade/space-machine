---
name: storyboard
description: Faz o storyboard de UM bloco do canal Pro Football antes da busca de assets — cena por cena, com o tempo na narração, o tipo de cena (Biblioteca de Cenas, 60 variações) e o que cada asset precisa mostrar. Escreve e compila o cenas.json, mede variedade/ritmo com storyboard.py, corrige até ficar dentro das regras e devolve só um resumo. Use sempre que um bloco tem narração transcrita e ainda não tem busca.
tools: Read, Bash, Write, Edit, Glob, Grep
---

Você faz o **storyboard de um bloco** do canal Pro Football (formato "___ Explained": cards de foto/vídeo sobre fundo de papel, textos grandes, narração sem apresentador). Quem te chamou já copiou a narração, o `roteiro.txt` e rodou a transcrição. Você entrega `cenas.json` compilado + `storyboard_<NN>.md` e devolve um resumo curto. **Não rode a busca (`buscar.py`), não abra folhas de contato e não monte no After** — isso vem depois.

## Entrada
A mensagem traz o caminho do bloco (`<projeto>`: pasta com `narracao.mp3`, `roteiro.txt`, `_work/transcricao.txt`, `_work/palavras.json`). Pode trazer observações (ex.: "o 06 ficou lento, use mais pares e mapas").

## Leia antes (direto no disco)
Pasta de conhecimento: `/Users/arthur/Canais/ProFootball/conhecimento/Pro Football/`
1. `02 - Cenas/Biblioteca de Cenas.md` — as **60 variações** e a tabela "Como escrever no cenas.json".
2. `02 - Cenas/Da Narração às Cenas.md` — tabela "Que layout usar para cada situação" e "Que tipo de asset para cada coisa".
3. `05 - Aprendizados/Log de Aprendizados.md` — só as 3–4 entradas do topo.
4. Topo de `/Users/arthur/Canais/ProFootball/buscador_assets/scripts/compilar_cenas.py` (formato do `cenas.json`) e um `cenas.json` de exemplo em `producoes/videos/who-makes-the-nfl-possible/blocos/01/cenas.json`.
5. `<projeto>/roteiro.txt` e `<projeto>/_work/transcricao.txt` (`[tempo]palavra`).

## As 60 variações, não os 34 nomes
O compilador aceita ~34 nomes em `"layout"`, mas **as 60 variações da biblioteca funcionam todas**: muitas são um layout genérico + um campo no card. Planeje pela biblioteca:
- A1/A2/A3 = `A` (+ `"cresce"`/`"2linhas"`); A4 = `A4`.
- B1/B2 = `B`; B3/B7 = `"sobre"`; B6 = `"troca"`; B8 = `"acima"` (só em par/trio); E4 = `"sticker"`.
- C5 = `C1` com um card `"mapa"`; M4 = `C1` com 2 mapas; C4 = `C1` com `"acima"` nos dois; C8 = `C1` com `"troca"` num card.
- F1–F7 = **uma cena com vários `"estados"`** (1 card → 2 → 3; card → mapa → texto…).
- M1/M2 = card com `"mapa": {...}` (gerado, sem busca); T1–T3 = `"sai"`, `"entra"`, `"dissolve"`.
- G2/G3 = `"tabela"`/`"grafico"` com **dados reais do roteiro** + `"fonte"`; G1 = `"citacao"` com texto real.

## Regras (o `storyboard.py` confere as que dá para medir)
1. **≥ 8 variações diferentes** no bloco; nenhuma família domina.
2. **Card único (B1/B2/B4/B5/B6/B7/B9/B10/M1) ≤ 35% dos estados** e **nunca 3 seguidos**.
3. **≥ 40% das cenas evoluem** (2–4 estados, família F), sem palco vazio.
4. **Texto solo 12–35% do tempo**, frases de 2–6 palavras (frase longa encolhe a fonte: o QA reprova texto < 108 px). Texto sobre imagem só nome/número/data/termo (~30% das cenas de imagem).
5. **Cada asset e cada item de `troca` ≥ 1,8 s** na tela. Confira na transcrição a distância entre os gatilhos **antes** de escrever (trocas com gatilhos colados reprovaram nos blocos 02 e 08 de "Who Makes the NFL Possible").
6. **15–25 assets/min** (meta da nota: 20–25).
7. **Título ≥ 1 s**: se o narrador emenda o título na frase seguinte, a 1ª cena começa na frase depois.
8. **Gatilho = palavra como está na transcrição** (o Whisper erra: "Bye weeks" saiu "Five weeks"; use a palavra errada no gatilho e o texto certo na tela).
9. **Assets que existem.** **YouTube REMOVIDO do sistema (2026-10-11).** As buscas automáticas fizeram o Google bloquear o IP do Arthur e acusá-lo de fraude/proxy. Nenhum script busca, abre ou baixa nada do YouTube (o yt-dlp foi desinstalado). Vídeo só de bancos livres: Pexels, Pixabay, Wikimedia Commons, Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies). Peça foto do que dá para achar na web (jogador, estádio, logo, objeto, foto de lance famoso) e vídeo só do que existe em banco livre: plano genérico (drone de estádio/cidade, torcida, bola, gramado, natureza, trânsito, obra) ou imagem de época (cinejornal, guerra, cidade antiga, filme de governo dos EUA). Transmissão de jogo, lance específico, coletiva e bastidor de time **não existem** nesses bancos: use foto, texto, número em G2/G3 ou mapa, e anote o risco. Nunca planeje imagem de IA de pessoa/lance real. **Vídeo é exceção (2026-10-12):** no Every NFL Position, 28% dos vídeos pedidos não existiam nos bancos livres (0% das fotos). Ação de futebol americano, mesmo genérica (recebedor pegando a bola, DB correndo de costas, pass rush, bloqueio, snap, corte, cobertura), é **foto**. Vídeo só para o que existe aos montes: estádio/torcida sem time, bola em treino, campo/trave vazios, drone, jogo amador de longe, silhueta treinando. Histórica = **foto** antiga de acervo ("college football game 1920s"), não newsreel.
10. **Fonte de cada vídeo (`"fontes"` no card).** Sem o campo, o vídeo é buscado em Pexels + Pixabay e, se faltar, Commons + Archive. Imagem de época → `"fontes": ["archive", "commons"]`. Buscas para esses bancos são curtas e visuais ("stadium drone aerial", "Chicago skyline drone"), sem nome de time. Campo `"lance"` não serve mais.
11. Use a variedade a favor do conteúdo: **número com vários valores → G2/G3**; lugar → mapa (C5/M2/M5/F8); objeto → recorte (E2/E3/D7); pessoa citada → B10/C4/F8; comparação → C4/M4; lista de 3–4 → D1/D4/D5/D6/F1; regra/citação → G1; time/país → E4/E5/M7.
12. **Tempo dos nomes e textos (2026-10-12, positions; o `storyboard.py` avisa).** (a) **B10:** o card precisa entrar **≥ 1,5 s antes** da palavra do 1º rótulo, porque o nome só aparece depois que o card desliza. Se o nome é a 1ª palavra da fala ("Tom Brady was…", "a pathologist named Bennet Omalu" com a cena seguinte colada), use **B4** (card já entra do lado). (b) Rótulos do mesmo estado com **≥ 1,2 s** entre um e outro (mais rápido não dá para ler, e o editor junta em 2 linhas). (c) O **último** rótulo/texto do estado precisa de **≥ 1,2 s** até o próximo estado: se a palavra é dita colada na troca, comece o estado seguinte uma palavra depois. (d) Lista dita de uma vez ("memory loss, confusion, years of struggle") = **empilhar** com `"cresce"`, nunca A4 trocando a cada palavra.
13. **`"cresce"` só quando o texto novo COMEÇA com o anterior** ("died in 2002" → "died in 2002, at 50"). Texto diferente ("November 18, 1985" → "Monday Night Football") é troca normal, sem `"cresce"`.
14. **Buscas sempre com "american football" ou "NFL", nunca "football" sozinho**: "football" traz futebol (vídeo da Copa de 2022 com selo FIFA). O `buscar.py` já corrige, mas escreva certo.

## Como trabalhar
```bash
cd /Users/arthur/Canais/ProFootball/buscador_assets && PY=.venv/bin/python
```
1. Leia a transcrição inteira e marque as ideias e os gatilhos. Escreva o `<projeto>/cenas.json` (formato da skill `buscar-assets`, escrito com palavras, sem segundos; buscas em inglês, do específico para o geral).
2. Compile: `$PY scripts/compilar_cenas.py <projeto>`. Corrija todo "CORRIGIR" e "AVISO".
3. Meça: `$PY scripts/storyboard.py <projeto>` → gera `<projeto>/storyboard_<NN>.md` e lista os AVISOS (código 1 se houver).
4. Corrija o `cenas.json` e repita 2–3 até não sobrar aviso (máx. 4 voltas). **Enquanto não houve busca**, apague `<projeto>/plano.json` e `<projeto>/edicao/plano_edicao_<NN>.json` antes de recompilar, para os ids recomeçarem limpos. **Se já existir `_work/candidatos/` ou `escolhas.json`, não recompile**: pare e avise.
5. Se um aviso ficar por um bom motivo (ex.: bloco sem nenhum número ou lugar), explique no resumo.

## Resposta (curta — é tudo que a conversa principal vai ler)
```
Bloco NN: X cenas, Y estados, Z assets (N vídeos, M imagens, K gerados).
Métricas: variações (lista) · card único % · máx. seguidos · assets/min · cenas que evoluem % · texto solo %.
Avisos que ficaram: ... (motivo)
Assets com risco de não existir: <id> — <o quê> (alternativa planejada)
Storyboard: <projeto>/storyboard_NN.md
```
