---
tags: [pro-football, assets, buscas]
---

# Buscas que Funcionam

> **Vídeo é exceção (2026-10-12):** no Every NFL Position, 28% dos vídeos pedidos não existiam nos bancos livres (0% das fotos). Ação de futebol americano, mesmo genérica (recebedor pegando a bola, DB correndo de costas, pass rush, bloqueio, snap, corte, cobertura), é **foto**. Vídeo só para o que existe aos montes: estádio/torcida sem time, bola em treino, campo/trave vazios, drone, jogo amador de longe, silhueta treinando. Histórica = **foto** antiga de acervo ("college football game 1920s"), não newsreel. Fonte de histórica: Commons primeiro (livro escaneado em djvu agora é filtrado).


Voltar: [[00 - Pro Football (Índice)]] · Fluxo: [[Como Buscar Assets]]

Receitas de busca testadas. **Sempre em inglês.** 2–3 buscas por asset, da mais específica para a mais geral. Atualize esta nota a cada descoberta (e registre no [[Log de Aprendizados]]).

## Jogador (foto)
- `"<Nome> <Time> <ano/evento>"` → `"Nick Foles Eagles Super Bowl LII"`, depois `"Nick Foles Eagles quarterback"`.
- Time + ano garantem **uniforme e época certos**.
- No Commons, **nome entre aspas**: `"\"Spencer Ware\""` (sem aspas, "Spencer Ware" achou "Wickwire Spencer Steel").
- Jogador menos famoso: a web só tem fotos da Getty (bloqueadas) ou pequenas (~600 px). Se não achar, use **texto com o nome** sobre o vídeo do lance.

## Lance específico de um jogo (vídeo) ⭐
- **Melhor busca:** `"<Jogador> Highlights vs. <Adversário> <ano>"` → `"Patrick Mahomes Highlights vs. Ravens 2018"`. O canal oficial da NFL publica um vídeo por jogador por jogo, com todos os lances dele.
- Lance famoso com nome próprio tem vídeo dedicado de ~30 s: `"Philly Special play Super Bowl LII"`, `"Mahomes no look pass Demarcus Robinson"`.
- ❌ Buscas descritivas (`"sidearm pass Spencer Ware"`) trazem lances parecidos **de outros jogos**.

## Achar o momento exato do lance ⭐⭐ (desde 2026-10-03)
Buscar o vídeo certo é metade; a outra metade é **o segundo certo dentro dele**. Ferramenta: `buscador_assets/scripts/achar_lance.py`.
1. Play-by-play oficial da ESPN (grátis, sem chave): dá **quarto, relógio e descida** de cada jogada. Ex.: sidearm para o Ware = 2Q **1:06**, **1st & 10**; no-look para o Robinson = 2Q **1:30**, **2nd & 1**.
2. OCR do macOS lê o **placar da transmissão** em cada frame do vídeo de highlights.
3. Onde quarto + descida + relógio batem (relógio até 30 s acima do snap) = o lance. Ordena pelo relógio mais próximo.
- ⚠️ A faixa inferior dos vídeos da NFL ("J. ALLEN: 6 RUSH, 74 YDS, TD") é o placar de **outros jogos** — não identifica o lance.
- Resultado no bloco 01: o trecho que eu tinha escolhido "de olho" para o sidearm (131 s) estava **depois** do lance; o certo era 118,5 s. O no-look começava antes do snap só a partir de 1,5 s (eu tinha usado 3 s).

## Gesto técnico genérico (vídeo)
- `"NFL quarterback throwing slow motion"`, `"quarterback throw slow motion 4k"`.
- ❌ Termos de aula (`"overhand throw"`) trazem tutoriais amadores.

## Jogador em contexto (vídeo)
- `"<Jogador> escapes pressure"`, `"<Jogador> scramble"`, `"<Jogador> off platform throws"`, `"<Jogador> pocket passing highlights"`.
- Compilados ("Craziest Throws Compilation") servem, mas exigem achar o trecho.

## Entrevista / coletiva
- `"<Jogador> press conference"` — ⚠ "Patrick Mahomes press conference" trouxe **Patrick Estrela (Bob Esponja)**. Sempre conferir visualmente; considerar `"Patrick Mahomes Chiefs press conference podium"`.
- Para o jogador explicando um lance: `"<Jogador> explains <lance>"` → achou "Mahomes recreates no-look pass with Peter King (NBC Sports)".

## Logo
- `"<Time> logo"` — o sistema já pede PNG transparente na web. Logos da NFL quase não existem no Commons (são material não livre).
- Commons para logos/mapas/bandeiras: o sistema adiciona `intitle:logo|map|flag` automaticamente (sem isso, "Eagles logo" trazia fotos de torcida).

## Mapa
- `"<cidade> locator map"`; no Commons: `"Minnesota locator map"`, `"Map of USA highlighting Wisconsin"`.

## Estádio / contexto
- `"<Estádio> <evento>"`, `"<Estádio> drone 4k"`, `"NFL training camp b-roll"`.

## Treino / offseason / OTAs (vídeo) ⭐
- `"<ano> OTA Practice Highlights <Time>"`, `"<Time> OTAs Highlights"`, `"<Time> Mandatory Minicamp Highlights"` — vídeos oficiais dos times, limpos e sem narração; um só serve para vários cards (QB lançando, recepção, linha em posição, drills).
- Musculação/condicionamento: vídeos oficiais dos times ("Derrick Henry Hill Runs | Baltimore Ravens", "Week In The Life Of An NFL Strength Staff"). ⚠ Conferir sobreposições ("SUBSCRIBE", rótulos de exercício).
- ❌ Buscas genéricas ("NFL OTAs catch receiver", "offensive line drills OTAs") trazem vídeo de celular e treino universitário.

## Recorte (PNG)
- Descreva o objeto isolado: `"Vince Lombardi Trophy"`, `"Riddell football helmet side view"`, `"<Jogador> throwing"`.
