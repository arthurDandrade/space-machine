---
tags: [pro-football, cenas, planejamento]
---

# Da Narração às Cenas

Voltar: [[00 - Pro Football (Índice)]] · Relacionado: [[Tipos de Cena]] · [[Como Buscar Assets]]

Como transformar roteiro + narração em cenas, e cada cena numa lista de assets para buscar. Atualizada em 2026-10-05 com o repertório completo da [[Biblioteca de Cenas]] (v1–v8). É o passo "Planejar" do [[Como Buscar Assets|fluxo de assets]].

## Texto × imagem (medido nas referências) ⭐
- **Nem toda cena tem texto.** Só ~30% das cenas com imagem têm algum texto; a imagem fala sozinha.
- Texto **sobre imagem** só para: **nome, número, preço, data ou termo-chave** ("$200–$2,500", "1965", "gamier", "31 yards"). Nunca frases da narração.
- Frases abstratas vão para cenas de **texto solo** (A) — é assim que a narração fica "coberta": imagem e texto se alternam, não se sobrepõem.
- **Cada asset fica no mínimo ~1,8 s na tela.** Cenas de imagem podem (e devem) durar 5–15 s quando o vídeo é bom. Não picotar a cena para acompanhar cada palavra.
- O `compilar_cenas.py` avisa quando mais de 45% das cenas de imagem têm texto ou quando um asset fica menos de 1,8 s.

## Storyboard (subagente `storyboard`, desde 2026-10-06)
O planejamento de cada bloco agora é feito pelo subagente `storyboard` (`.claude/agents/storyboard.md`), que entrega `storyboard_<NN>.md`: cena por cena, tempo na narração, tipo de cena (das **60 variações**) e o que cada asset mostra. O script `buscador_assets/scripts/storyboard.py` mede e avisa: **≥ 8 variações**, **card único ≤ 35%** e nunca 3 seguidos, **≥ 40% de cenas que evoluem**, texto solo 12–35%, cada asset/troca ≥ 1,8 s, 15–25 assets/min.
Motivo: em [[Who Makes the NFL Possible]] 76% das cenas ficaram em B/C1/A, só 15 dos 60 tipos foram usados e 19 layouts prontos nunca apareceram (G1–G3, mapas M3/M6/M7, recortes E2/E3, D4/D5, C4, B11).

## Regras
1. **Cada item começa com o título** (E1): o nome falado sozinho + um recorte do item. Dura só ~1–1,5 s nas referências.
2. **Corte em cenas pela troca de ideia.** Cada asset fica em média **~4 s** na tela (v5–v8), **nunca menos de 1,8 s**. Cena de vídeo bom pode durar 5–15 s. Não picotar para acompanhar cada palavra.
3. **Pense em sequências, não em cenas paradas** (família F): uma frase de 4–8 s com 2–4 gatilhos vira **uma cena com vários estados** (1 card → par → troca → texto), sem palco vazio.
4. **Todo nome próprio, lugar, data, número, time, objeto concreto ou ação visível vira asset**, com `gatilho` = a palavra exata da narração.
5. **Frases abstratas viram texto solo** (A1, ou A4 se a frase for longa e der para quebrar em trechos), sem asset: ~28–32% do tempo.
6. **Densidade-alvo: 20–25 assets por minuto** (sequências consomem 2–5 assets cada).
7. **Nunca o mesmo asset duas vezes.** Para repetir um jogador, outra foto/outro momento.
8. **Variedade:** não repetir o mesmo código 3 vezes seguidas nem encadear 4 cards únicos (B). O QA avisa.
9. Trabalhe **um item por vez** (planejar o vídeo inteiro de uma vez fica superficial).

## Que layout usar para cada situação ⭐
Repertório completo, com medidas e sintaxe do `cenas.json`, na [[Biblioteca de Cenas]] (tabela "Como escrever no cenas.json"). Todos os códigos abaixo existem no editor.

| A narração… | Layout | Observação |
|---|---|---|
| frase abstrata curta | **A1** | 2–6 palavras |
| frase abstrata longa | **A4** (trechos encadeados) ou **A3** (2 linhas) | A4: 2–5 palavras por trecho, um gatilho em cada |
| termo + definição ("QB = quarterback") | **A2** (frase que se completa) | |
| mostra um lance/vídeo | **B1** paisagem / **B2** vertical | vídeo vertical com cortes internos (short já editado) conta como 1 asset |
| processo em etapas (snap → scramble → throw) | **B6** (troca no mesmo quadro) | |
| cita uma pessoa pelo nome | **B10** (card no centro desliza e o nome entra) ou **B4** (card + nome ao lado) | para nome acima use par (C4) — ver B8 |
| pessoa + 1 número/data | **B4** / **B5** (rótulo que troca) | B5 para 2–4 rótulos em sequência |
| lista de qualidades/itens sobre a mesma imagem | **B9** (lista que acumula) | palavras se empilham |
| termo/número em destaque sobre a imagem | **B7** (palavra no card) ou `"sobre"` | só nome/número/data/termo |
| algo importante "por cima" do que já está na tela | **B11** (foco por cima) | estado logo depois do que fica desfocado |
| duas coisas lado a lado / dois ângulos | **C1** | pares cortados em retrato |
| pessoa fixa + lances trocando | **C8** (âncora fixa) | `troca` em um card só |
| algo que "chega" sobre outro (manchete, logo) | **C2** (cascata) | |
| comparação rotulada ("Man" × "Zone") | **C4** | `acima` em cada card |
| "vários iguais" (prêmios, edições) | **C9** (pilha) | cards [trás, frente] |
| pessoa + o que criou/conquistou | **C6** / **D3** | |
| lista de 3 (com uma palavra para cada) | **D1** (trio) ou **F1** (cresce 1→2→3) | |
| 1 principal + 2 de apoio | **D5** (sanduíche) ou **D2** (1 grande + pequenos) | D5: o principal é o 3º card, fica no meio |
| lista de 3–4 que vai se acumulando | **D6** (baralho) ou **D4** (esteira) | |
| objeto/equipamento solto | **E2** / **E3** (recorte + card/texto), **D7** (recorte + par) | |
| jogada desenhada / diagrama | **E6** (diagrama recortado + card) | |
| time/país ligado ao lance | **E4** (sticker no canto) ou **E5** (bandeira/logo ao lado) | |
| cidade/estado/país | **M2** (mapa gerado com região destacada) ou **C5** (foto + mapa) | `"mapa": {...}` gera sozinho |
| dois lugares | **M4** (par de mapas) | |
| mudança no mapa (antes × depois) | **M3** (mapa que troca com dissolve) | |
| jogo internacional / "do outro lado do mundo" | **M5** (card + globo rolando) | |
| estado dentro do país (silhueta) | **M6** (silhueta + mapa) | |
| lugar + escudo/bandeira | **M7** (bandeira dentro do mapa) ou **F9** (foto + bandeira + mapa) | |
| biografia: pessoa → onde → quando | **F8** (retrato + mapa + nome→data) / **F3** | |
| regra, citação, texto oficial | **G1** (caixa de citação com grifo) | texto real, nunca inventado |
| ranking, estatística com vários valores | **G2** (tabela) / **G3** (gráfico) | dados reais + `fonte` |

## Que tipo de asset para cada coisa
| O que a narração cita | Tipo de asset | Layouts típicos |
|---|---|---|
| Jogador, técnico, pessoa | `foto` (retrato, uniforme e época certos) | B10, B4, C4, C6, F8 |
| Time, liga, evento (Super Bowl) | `logo` | LOGOS, E4, E5, M7 |
| Cidade, estado, estádio como lugar | **mapa gerado** (`"mapa"`) + `foto` do lugar | M2, C5, F9 |
| **Jogada, lance, passe, corrida, jogo** | **`video`** (meta: 40–50% dos cards); lance real → campo `"lance"` | B1, B2, B6, C1, C8 |
| Gesto técnico (arremesso, passada) | `video` genérico em câmera lenta | B1, C1 |
| Equipamento, troféu, objeto | `recorte` ou `foto` | E2, E3, D7 |
| País | `bandeira` (ou `"mapa"` com `globo`) | E5, M5, M7 |
| Antes de ~1980 | `historica` | C2 (gravura por cima), B1 |
| Regra, documento | texto real para `"citacao"` | G1 |
| Estatística com vários valores | dados reais para `"tabela"`/`"grafico"` | G2, G3 |
| Data, número único | texto (rótulo/sobre card) | B4, B5, B7, A1 |

## Exemplo real (teste "Adapting the Pass")
| Fala | Layout | Assets |
|---|---|---|
| "When pressure forces a quarterback to move," | B1 + `sobre` | vídeo: Mahomes fugindo da pressão (gatilho *pressure*) |
| "the available passing lanes change." | A1 | — |
| "Patrick Mahomes can adjust his position and throwing motion" | C1 | foto Mahomes (*Patrick Mahomes*) + vídeo câmera lenta do arremesso (*throwing*) |
| "Against Baltimore in December 2018," | LOGOS + texto abaixo | logo Ravens (*Baltimore*) + "December 2018" |
| "Mahomes completed a no-look pass to DeMarcus Robinson." | C1 com `acima` (C4) | vídeo do no-look (*no-look*) + foto Robinson (*DeMarcus*) |

Com o repertório novo, a mesma frase poderia virar: "Patrick Mahomes…" → **B10** (retrato desliza, "Patrick Mahomes" entra); "Against Baltimore in December 2018" → **E5** (vídeo do jogo + logo dos Ravens ao lado) com B7 "December 2018".

## Formato do planejamento (`cenas.json`)
O planejamento agora é escrito em `cenas.json` (formato completo no topo de `buscador_assets/scripts/compilar_cenas.py` e na skill `buscar-assets`):
- cada **cena** tem um ou mais **estados** (a cena evolui — família F da [[Biblioteca de Cenas]]);
- cada estado tem `layout` (código da biblioteca), `fala` (as primeiras palavras do trecho) e `cards`/`textos`/`rotulos`;
- cada card descreve o asset a buscar (`tipo`, `descricao`, `buscas`) e a palavra em que entra (`gatilho`), ou reaproveita um asset (`reusar`) / uma alternativa já baixada (`arquivo`).
O `compilar_cenas.py` transforma isso no plano de busca e no plano de edição.
