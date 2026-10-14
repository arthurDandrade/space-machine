---
tags: [pro-football, cenas, biblioteca]
fonte: estudo de 858 cenas de v1–v4 (2026-10-02) + 906 cenas de v5–v8 (2026-10-05); folhas de 3 momentos por cena + detecção automática a 4 fps
---

# Biblioteca de Cenas

Voltar: [[00 - Pro Football (Índice)]] · Base: [[Tipos de Cena]] · Planejamento: [[Da Narração às Cenas]]

O "estoque" de composições que as referências usam. Cada variação tem um **código** (para usar no `plano.json`), **como monta**, **que assets pede** e um **exemplo de futebol americano**. Referências entre parênteses: `v1#14` = vídeo Ramen, cena 14 (folhas em `Videos Referencias/estudo_cenas/tiras/`).

**Vídeos:** v1 Ramen · v2 Chocolate Candy · v3 Luxury Food · v4 Sugars · **v5 Donut · v6 Italian Cuisine · v7 Military Food · v8 Coffee Dessert** (v5–v8 adicionados em 2026-10-05; arquivos em `Videos Referencias/`, cenas em `estudo_cenas/segs/`).

> [!info] Códigos ✅ vieram de v5–v8 (2026-10-05) e **todos já existem no editor** (`compilar_cenas.py` + `gerar_ae2.py`). As "alternativas" escritas em algumas linhas são do tempo em que ainda não existiam.

> [!important] A grande descoberta
> Nas referências a cena **não é uma imagem parada**: ela **evolui**. Em 5–20 s a composição muda 2–4 vezes (1 card → 2 cards → troca para outro card grande com texto), **sem passar pelo palco vazio** — os cards saem acelerando enquanto os novos já entram. Nosso 1º bloco tinha "uma composição por cena"; o certo é pensar em **sequências** (família F).

## Números gerais (detecção automática)
- Tempo de tela: **~32% só texto**, ~60% com 1 grupo de cards, ~7% com 2–3 cards separados, 16% com recorte (PNG) solto.
- Cards são **grandes**: altura típica 740–950 px (≈ 85% da tela), centralizados (centro x ≈ 960, y ≈ 545).
- Formato dos cards: **43% retrato, 43% paisagem, 13% quadrado**. Retrato quase sempre é vídeo vertical.
- Dois cards lado a lado: **mesma altura** (razão mediana 0,99), **gap pequeno: 15–50 px** (não 60), alinhados pelo centro; **10% sobrepostos**.
- **v5–v8 (2026-10-05):** só texto ~28% · 1 card 62% · 2 cards 8% · 3+ 3% · recorte solto 21%. Card único: altura mediana 850 px (0,79 da tela), **60% paisagem / 27% retrato**. Pares: **42% sobrepostos** (era 10% em v1–v4: cascata, sanduíche e pilha ficaram muito mais comuns); quando não sobrepõem, gap 8–20 px. Tempo de cada asset na tela: mediana 4 s.
- ⚠ O detector às vezes junta cards encostados, então a proporção de pares/trios está subestimada; nas folhas, pares aparecem em ~25–30% das cenas com imagem.

---

## A — Texto
| Código | Como monta | Assets | Exemplo NFL |
|---|---|---|---|
| **A1 Frase** | 2–6 palavras, 1 linha, centro (v1#7–9) | — | "the pocket collapses" |
| **A2 Frase que se completa** | a frase muda no lugar, ganhando palavras: "kinder" → "Kinder = Children" (v2#21), "Malt syrup" → "barley malt syrup" (v4#227) | — | "QB" → "QB = quarterback"; "Cover 2" → "Cover 2 zone". **No editor (2026-10-11):** texto com `"cresce"` que começa com a frase anterior (mesmo do estado anterior) mantém a anterior parada e põe só o resto na linha de baixo, sem salto de tamanho. Cadeia no mesmo estado (`["This is","This"], ["This is every NFL position","every","cresce"], ["…, explained","explained","cresce"]`) = **frase que cresce**: linhas empilham e o bloco sobe para ficar centrado. Frase única: **não** usar A4 (ele apaga a frase e parece outra cena) |
| **A3 Frase em 2 linhas** | frase longa quebrada, menor (v1#131) | — | "As defenses began / disguising coverages" |
| **A4 Frases encadeadas** ✅ | a narração vira 2–4 trechos de 2–5 palavras que **trocam no mesmo lugar a cada ~1–2 s** (v5#29–31 "so he stayed home" → "and shaped fried dough" → "into rounds resembling" → "cannonballs"; v7#31, v8#46, v6#100). **Medido a 30 fps:** a frase some de uma vez, ~0,17 s de palco vazio e a próxima entra em ~0,1 s (o "cinza" nas folhas é o frame dessa entrada, **não** um fade lento) | — | "he dropped back" → "felt the rush" → "and threw it away". **No editor:** `"layout": "A4"` + `"textos"` (um por trecho, gatilho em cada um) |

## B — Um card
| Código | Como monta | Assets | Exemplo NFL |
|---|---|---|---|
| **B1 Card grande** | paisagem, ~85% da altura, centro (v1#27, v3#29) | 1 foto/vídeo paisagem | estádio, lance aberto |
| **B2 Card vertical** | vídeo 9:16 estreito no centro (v2#12, v3#5) | 1 vídeo vertical | clipe vertical do jogador |
| **B3 Card + frases brancas** | frases trocam por cima do mesmo card (v1#12: "The place got huge" → "kicked off…" → "first big boom…") | 1 vídeo | replay do lance com "4th and 2" → "no timeouts" |
| **B4 Card + rótulo lateral** | card **menor (≈ 40% da largura)** de um lado, texto preto **grande, de preferência em 1 linha** do outro ("the aromatics"); rótulo pode ser 1 palavra grande ou bloco de 2–3 linhas menor ("a weak stock makes a weak bowl", v1#113) | 1 foto | foto + "Spencer Ware"; foto + "31 yards" |
| **B5 Rótulo em lista** | mesmo card, o rótulo **troca** item a item: "the bones" → "the aromatics" → "the salt" (v1#114) | 1 foto | QB lendo: "the safety" → "the linebacker" → "the corner" |
| **B6 Troca no lugar** | o **quadro fica**, o conteúdo troca por corte (2–4 vídeos verticais em sequência) (v3#134, v3#5, v4#229). ⚠️ Em v8 aparecem 5–7 cortes de 0,5–1,2 s no mesmo quadro (v8#19–23, #200–207), mas esses cortes **estão dentro do próprio vídeo** (short/reel já editado na origem): na edição é **um asset só**, e a regra dos 1,8 s não muda (Arthur, 2026-10-05). → Vale buscar vídeos verticais que já tenham cortes internos | 2–4 vídeos verticais | processo/sequência: snap → scramble → arremesso |
| **B7 Palavra no card** | palavra/termo em branco **centralizado, tamanho médio** (igual ao texto sobre o card), não rodapé miúdo ("casein", v3#134) | 1 vídeo | "snap", "read", "throw" |
| **B9 Lista que acumula** ✅ | como B4, mas as palavras **se empilham** em vez de trocar: "chinese" → +"malay" → +"indian" → +"eurasian"; até 4 linhas, texto preto ~50 px, centralizado na metade livre (v7#219, 997 s) | 1 foto | QB + "speed" / "vision" / "arm". Alternativa hoje: B5 |
| **B10 Card que abre espaço** ✅ | card entra **centralizado**, depois **desliza para um lado** e o nome aparece em fade no espaço aberto, colado ~10 px da borda do card; o rótulo pode trocar no lugar ("Hanoi, Vietnam" → "in 1946") (v8#164 "Anna Pavlova", v8#228, v8#133) | 1 retrato | retrato do técnico → desliza → "Andy Reid" → "since 2013". **No editor (2026-10-05):** `"layout": "B10"`, 1 card + `"rotulos"`; o card entra no centro e desliza ~0,45 s antes do 1º rótulo até a direita (740 px de altura, borda a 220 px da tela); rótulos trocam no lugar à esquerda. Em v8#133/#164 o card entra direto à direita: para isso usar B4. **(2026-10-11)** o 1º rótulo espera o fim do deslizamento: o card precisa entrar ≥ 1,5 s antes da palavra do rótulo. **(2026-10-12)** se o nome é a 1ª palavra da fala ("Tom Brady was…"), não dá tempo: usar **B4**. Rótulo com menos de 1,2 s na tela entra junto com o seguinte, em 2 linhas. O **último** rótulo/texto de um estado ganha ≥ 1,2 s: o estado seguinte espera até 0,8 s (vale para B9, B10, A…) |
| **B11 Foco por cima** ✅ | a composição que está na tela (par/trio) **desfoca e escurece um pouco, sem sair**; um card novo um pouco maior (~75% da altura) entra por cima vindo de cima/baixo, ou entra só um rótulo preto grande (v6#118 diploma sobre trio, v6#200, v6#45 "Bagna càuda") | 1 card ou só texto | lances desfocados + o contrato entrando por cima. **No editor:** um estado `"layout": "B11"` logo **depois** do estado que deve ficar atrás (na mesma cena): o anterior não sai, desfoca (~18 px na tela), fica com 80% de opacidade (textos dele somem) e sai junto com o B11. Card: retrato 860 px ou paisagem até 1300×760; sem cards, use `"textos"` para só o rótulo por cima |
| **B8 Rótulo acima** | texto preto **grande (≈ título)** logo acima do card, pode passar da largura do card: nome da pessoa (v2#80 "Harry Burnett Reese"); os cards ficam um pouco menores/mais baixos para dar espaço | 1 retrato | nome acima do retrato do técnico. **No editor:** campo `"acima"` no card. ✅ Funciona em **par/trio** (C1/C8 com `acima` viram C4: cards menores e mais baixos, nome com a largura do card). ⚠️ Em **card único** o card não encolhe e o nome sai cortado no topo: para pessoa + nome use **B10** ou **B4**. Não usar `acima` no D5 (bate no card do meio). **Em v6/v8**: rótulo **do tamanho do texto normal** (não de título), entra ~0,5 s depois do card e fica sobre **um só** card do par; continua por cima de cortes entre clipes verticais (v6#127 "Pisa", v6#166–167, v8#108, v7#99) |

## C — Dois cards
| Código | Como monta | Assets | Exemplo NFL |
|---|---|---|---|
| **C1 Lado a lado** | mesma altura, gap 15–50 px (v1#11, v1#62) | 2 (de preferência retrato) | dois ângulos do mesmo lance |
| **C2 Cascata (sobreposto)** | 2º card entra **por cima** do 1º cobrindo 20–30%, um pouco deslocado em y; texto atravessa os dois (v2#13 "World War II", v2#79, v3#122, v2#106) | 2 | foto do jogo + manchete de jornal; logo + foto |
| **C3 Par construído** | 1º card entra **já fora do centro** (no lugar final) e espera; o 2º chega na palavra (v1#3, v4#7) | 2 | "Mahomes… [card] …and Ware [card]" |
| **C4 Comparação rotulada** | rótulo **grande** acima de cada card/grupo: "White miso" / "Red miso" (v1#41–42) | 2 | "Man coverage" / "Zone coverage" |
| **C5 Lugar** | foto + mapa ao lado ou mapa entrando por cima; mapa pode trocar de destaque ou de escala (v1#117, v1#64, v4#129, v3#2) | foto + 1–2 mapas | "Against Baltimore" → mapa com Baltimore destacado |
| **C6 Pessoa + criação** | retrato + o produto/lugar ligado a ela (v2#3 Frank Mars + Snickers) | retrato + objeto | Andy Reid + playbook; jogador + troféu |
| **C7 Produtos lado a lado** | dois produtos/embalagens (v1#124, v1#125) | 2 fotos de produto | duas bolas/capacetes de épocas diferentes |
| **C8 Âncora fixa** ✅ | par em que **um card fica parado** e o outro troca de conteúdo (saindo e entrando outro asset, às vezes mudando de formato, v6#190); em trio, só o do meio troca. ⚠️ Parte dos casos contados pelos subagentes (cortes a cada 0,8–1,5 s, ex.: v8#79–82) pode ser **corte interno do vídeo** (ver B6), ou seja, um C1 comum com vídeo editado. Contagem: até ~12 cenas em v6 e ~6 em v8 (v6#19–21, v6#80–82, v6#190; trio: v8#181–183, v6#68–70) | 1 fixo + 2–4 que trocam | foto do jogador fixa + replay trocando de ângulo. **No editor:** `"layout": "C8"` (2 ou 3 cards em linha, como C1/D1) com `"troca": [...]` em **um** card só |
| **C9 Pilha** ✅ | o 2º card fica **atrás** do 1º, deslocado só ~8% para cima/direita, quase escondido: sensação de "várias unidades" (v7#17, v7#26) | 2 fotos parecidas | pilha de cards de jogadores / várias edições de um prêmio. **No editor:** `"layout": "C9"`, cards na ordem **[de trás, da frente]** (deslocamento de 8%). **Um gatilho para cada card** (2026-10-13): na mesma palavra os dois subiam juntos e pareciam um só; o editor atrasa o da frente 0,4 s se vierem juntos |

Variações de C2 vistas em v5–v8: card **paisagem menor, mais baixo e à direita** por cima de um retrato (v8#120); gravura/foto antiga com borda de papel cobrindo ~70% da foto moderna (v5#28, v5#74). C4 em trio com rótulo **só nas pontas**, entrando um de cada vez (v6#109 "Modena" / "Bologna").

## D — Três ou mais
| Código | Como monta | Assets | Exemplo NFL |
|---|---|---|---|
| **D1 Trio em linha** | entram 1 → 2 → 3, um por palavra (lista) (v1#16, v1#122, v4#221) | 3 | "speed, vision and arm strength" |
| **D2 1 grande + 2–3 pequenos** | card grande + coluna de pequenos empilhados (v1#115, v1#120) | 3–4 | lance + 3 fotos dos jogadores envolvidos |
| **D3 Moldura pessoa–objeto–pessoa** | objeto no centro, retratos dos dois lados (v2#96) | 3 | técnico – troféu – QB |
| **D5 Sanduíche** ✅ | 3 cards; o do **meio fica na frente**, ~5–8% mais alto, cobrindo 15–25% de cada vizinho; costuma entrar por último sobre um par (C1 → trio) (v8#4, v8#63, v8#86, v8#144) | 3, o principal no meio | lance no centro, jogador e estádio atrás. **No editor:** `"layout": "D5"`, cards na ordem **esquerda, direita, meio** (o meio é o último gatilho e fica por cima); laterais 700 px, meio 860 px, cobre 18% de cada lado (medido em v8#4); **não usar `acima`** (bate no card do meio). Variante vista em v8#144: meio menor e mais baixo |
| **D6 Baralho (cascata de 3–4)** ✅ | C2 com 3–4 cards: cada um entra por cima do anterior (um por palavra), cobrindo 15–50%, com desnível de ±20 px em y; o leque ocupa ~70–75% da largura (v5#39–41, v5#133, v7#81, v7#52, v7#131, v8#248 "London → New York → Sydney"). ~8 cenas em v7 | 3–4 | "Chiefs, Bills, Ravens…" com cards se sobrepondo. **No editor:** `"layout": "D6"`, 3–4 cards na ordem dos gatilhos; cortados em retrato/quadrado (paisagens encolhiam o leque para ~430 px), alturas 800→680, cada um cobre ~38% do anterior, desnível −30/+30/−10/+40 px |
| **D7 Recorte + par** ✅ | PNG estreito (~8% da largura, ex.: garrafa) na mesma altura de um par, como 1º item de um trio (v6#101) | 1 recorte + 2 cards | troféu recortado + 2 fotos |
| **D4 Esteira** | cards continuam chegando pela direita, em fila (v4#114). ⚠️ Nas referências o último fica parcialmente fora da tela, mas o Arthur prefere **todos dentro da tela** (2026-10-03): o editor encolhe a fila para caber. Variante com cards quadrados sobrepostos ~15% (v7#217) | 3–4 | "Chiefs, Bills, Ravens and Bengals…" |

## E — Recortes (PNG)
| Código | Como monta | Assets | Exemplo NFL |
|---|---|---|---|
| **E1 Título do item** | nome no topo + PNG grande. Dura só **0,8–1,5 s** (v5–v8: 9–11 por vídeo). Variantes: nome **digitado letra a letra** (~0,8 s) enquanto o PNG cresce de ~40% ao tamanho final (v7#1, v7#71); nome longo **encolhe para caber em 1 linha** (v8#131); PNG = travessa montada com os itens da seção (v6#1); cena que **termina** no título seguinte (v5#127) | 1 recorte | jogador recortado; nome do time digitado + capacete crescendo |
| **E2 Recorte + card** | PNG solto ao lado de um card (limão + molho, v1#133) | recorte + card | bola recortada + vídeo do passe |
| **E3 Recorte + texto** | PNG de um lado, bloco de texto pequeno do outro (v1#139) | 1 recorte | capacete + "Built for contact". **No editor (2026-10-12):** recorte à esquerda, `textos` no espaço à direita dele (antes ia para o centro, por cima do PNG) |
| **E4 Sticker no canto** | bandeira/logo PNG "colado" sobre o canto de um card (v4#116) | logo PNG + card | logo dos Ravens no canto do vídeo do jogo |
| **E5 Bandeira colada ao lado** ✅ | bandeira retangular **chapada, sem moldura**, ~45% da altura do card, entra pela direita e cobre 20–30% da borda direita, centrada em y; o card fica um pouco à esquerda (v5#2 Portugal, v5#68 Peru) | bandeira/logo PNG | logo grande do time encostado no vídeo do lance. Alternativa hoje: E4 |
| **E6 Diagrama recortado + card** ✅ | desenho técnico em traço (PNG sem fundo, com partes numeradas), ~45% da altura, solto à esquerda; foto real em card à direita (v6#162, cortes da vaca) | diagrama PNG + card | diagrama da jogada/formação + clipe do lance. Alternativa hoje: E2 |

## F — Sequências (evolução dentro da cena) ⭐
A família que mais faltava. Cada sequência é **uma cena de 4–20 s** com 2–4 estados; as trocas acontecem nas palavras-gatilho, com saída animada + entrada sobreposta (sem palco vazio).

| Código | Estados | Ref. | Exemplo NFL |
|---|---|---|---|
| **F1 Cresce** | 1 card → 2 → 3 | v1#16, v1#122 | "Kelce, Hill and Hardman" |
| **F2 Cresce e troca** | 1 → 2 → sai tudo → 1 card grande novo | v2#2 (Snickers → par → MARS) | jogador → par com o time → logo da franquia |
| **F3 Retrato → contexto** | retrato + nome → mapa entra por cima → retrato + objeto | v2#3 (Frank Mars) | QB + nome → mapa da cidade natal → QB + troféu |
| **F4 Card → card+mapa → card com texto** | v3#2 (trufa → + mapa Itália → card "expensive") | lance → + mapa → close com "$450M" |
| **F5 Rótulo → cards** | card + rótulo → rótulo substituído por 1–2 cards | v1#120, v1#134 | foto + "the read" → foto + 2 cards dos recebedores |
| **F6 Título que vira cena** | título do item → cards (sem palco vazio) | v4#116 | título → primeiro lance |
| **F7 Vertical em série** | B6 encadeado com mudança final para paisagem/flag | v4#249 | 3 clipes verticais → card com logo |
| **F8 Retrato → nome → data + mapa** ✅ | retrato com nome em branco → mapa entra pelo canto → o nome é trocado no lugar pela data | v5#167 ("Dominique Ansel" → mapa NYC → "may 2013"), v5#20 | retrato + "Patrick Mahomes" → mapa de Tyler, TX → "1995" |
| **F9 Lugar em camadas** ✅ | card + bandeira colada (E5) → mapa/satélite entra **por baixo** do card, com o nome do lugar em branco que some | v5#3 ("Island of Madeira") | lance + logo → mapa do estádio por baixo com "Arrowhead" |

## G — Documentos e dados
| Código | Como monta | Assets | Exemplo NFL |
|---|---|---|---|
| **G1 Caixa de citação** ✅ | **medido em 1080p (v5#19, v5#60):** card **centralizado** (retrato ~900 px / paisagem ~1270×866); caixa **escura** arredondada de 900–1050 × ~280 px começando a ~110 px da borda esquerda, cobrindo ~60% do card; texto branco ~30 px em 4–5 linhas, trecho **grifado em azul** por trás das palavras (estilo resumo do Google) e a fonte num selo cinza no fim | trecho de texto + card | trecho da regra da NFL com a frase-chave grifada. **No editor:** `"layout": "G1"`, 1 card com `"citacao": {"texto": "...", "grifo": "trecho exato", "fonte": "NFL Rulebook", "gatilho": "palavra"}`; a caixa é desenhada em PNG pelo gerador e desliza da esquerda. Texto da citação = **fonte real** (regra, Wikipedia), nunca inventado |
| **G2 Tabela/print como card** ✅ | print de tabela/documento em card retrato ~50% da altura, centro, sem texto por cima (v7#47) | screenshot | tabela de estatísticas, ranking de salários |
| **G3 Infográfico pronto** ✅ | gráfico/mapa temático já pronto usado como card (termômetro v8#186; mapa de clima com legenda v8#184) | imagem do infográfico | gráfico de EPA, mapa de calor de passes |

## M — Mapas
v6 e v8 usam mapa em ~9% das cenas (bem mais que v1–v4). C5 (foto + mapa) continua valendo; estas são as outras formas.

> [!tip] Gerador de mapas ✅ (2026-10-05)
> `buscador_assets/scripts/gerar_mapa.py` desenha o mapa com **fronteiras reais** (Natural Earth, em `buscador_assets/dados/`) e as cores do canal: água azul-clara, terra quase branca, região em **azul da marca** (ou `--cor laranja`, como nas referências) ou `--estilo contorno` (cinza + vermelho, v8#8), rótulo em Impact que desvia dos pontos de cidade. EUA em projeção cônica (48 estados); outros países com os vizinhos em volta.
> **No `cenas.json`:** card com `"mapa": {"eua": ["Missouri"], "pontos": ["Kansas City:39.10:-94.58"]}` ou `{"pais": ["United Kingdom"], "estilo": "contorno"}` (opções `rotulo`, `sem_rotulo`, `cor`, `formato` 4:3/16:9/1:1, `vista` "lon0,lat0,lon1,lat1"). O `compilar_cenas.py` gera o PNG em `assets/mapas/` e o card não entra na busca. Serve para M1, M2, M4 (2 cards de mapa) e C5.
> Estados/províncias só existem para EUA, Canadá, Brasil, Austrália, China, Índia, Indonésia, Rússia e África do Sul; países, para todos.

| Código | Como monta | Ref. | Exemplo NFL |
|---|---|---|---|
| **M1 Mapa sozinho** ✅ | mapa ocupa um card grande (B1); destaque com região em cor translúcida + **elipse vermelha** (satélite), legenda numerada ou mapa antigo | v8#43, v6#25, v6#5, v6#213 | mapa com a divisão AFC West destacada |
| **M2 Região contornada/preenchida** ✅ | mapa de ruas com área cinza e **contorno vermelho ~4 px**, ou mapa político claro com o país/estado em **laranja chapado**; ao lado da foto do lugar | v8#8, v8#192, v6#99, v6#121 | estado do Missouri em laranja ao lado do estádio |
| **M3 Mapa que troca no lugar** ✅ | mesmo quadro: mapa atual → mapa histórico (ou zoom de escala) | v6#75 | mapa das franquias hoje → em 1970 |
| **M4 Par de mapas** ✅ | dois mapas lado a lado (C1) | v8#44 | cidade de origem × cidade do time |
| **M5 Globo localizador** ✅ | globo PNG ortográfico com a região em verde (~30% da altura) entra **rolando** pela direita; o card desliza à esquerda e o globo encosta na borda dele | v7#181 | jogo internacional: globo com Londres/Munique |
| **M6 Silhueta voando** ✅ | silhueta cinza recortada do país com sub-região em vermelho entra por cima dos cards; depois entra um mapa político | v7#197 | silhueta dos EUA com o estado em vermelho |
| **M7 Bandeira no mapa** ✅ | bandeira pequena colada no topo de um card de mapa | v6#74 | logo do time sobre o mapa da cidade |

## T — Transições e movimentos
Detalhes de como os elementos entram/saem que aparecem em v5–v8 (o padrão continua sendo entrada ease-out / saída ease-in do [[Animação e Ritmo]]; não alterar o editor sem medir).

| Código | O que acontece | Ref. |
|---|---|---|
| **T1 Saída por baixo com borrão** ✅ | card desce e sai pela borda inferior com motion blur forte; o novo pode subir de baixo | v5#42, v5#48, v5#129→130 (~5×) |
| **T2 Entrada de fora da tela** ✅ | o 2º card desliza da borda direita (ou sobe do canto inferior) enquanto o 1º fica parado | v7#40, v7#56, v7#7, v5#132 |
| **T3 Dissolve dentro do card** ✅ | um card do par se dissolve em outro, sem saída animada | v8#119 |
| **T4 Troca de frase** | ❌ não é fade lento: medido a 30 fps, some de uma vez + ~0,17 s vazio + entrada de ~0,1 s (ver A4) | v5#29–31 |

## Como escrever no `cenas.json` (4ª leva, medidas em frame cheio)
| Código | No `cenas.json` | Medidas usadas (1080p) |
|---|---|---|
| **B9** | `"layout": "B9"`, 1 card + `"rotulos"` (um por palavra) | palavras **empilham a partir do alto do card** (não centralizadas), ~100 px, 147 px entre linhas (v7#219) |
| **D7** | `"layout": "D7"`, 1º card `"png": true` + 2 cards | recorte na **mesma altura** do par (700 px) |
| **E5** | `"layout": "E5"`, 1 card com `"lateral": {busca de bandeira/logo, "gatilho": ...}` | foto ~880 px **centralizada**; bandeira = 48% da altura do card, cobre 29% da borda direita, entra deslizando da direita (v5#2). Logo largo encolhe para não passar da margem |
| **E6** | `"layout": "E6"`, diagrama `"png": true` + card | igual ao E2 (v6#162) |
| **F8** | `"layout": "F8"`, cards [foto paisagem com `"sobre"`: [nome, data], mapa] | foto ~860 px; mapa = 77% da altura, cobre 53% da própria largura sobre a foto, topo 100 px abaixo (v5#167) |
| **F9** | `"layout": "F9"`, cards [foto com `"lateral"` (bandeira), mapa] | foto ~880 px centralizada; mapa (65% da altura) entra pela esquerda **por cima** da foto, cobrindo 37% dela (v5#3 — não por baixo, como dizia o 1º relatório) |
| **G2** | `"layout": "G2"`, card com `"tabela": {"titulo", "colunas", "linhas", "destaque", "fonte"}` | gerada por `gerar_tabela.py`; card até 1100×860 (v7#47 ≈ 1030×850). **Dados reais + fonte** |
| **G3** | `"layout": "G3"`, card com `"grafico": {"titulo", "itens": [[nome, valor]], "unidade", "destaque", "fonte"}` (ou um infográfico buscado) | barras horizontais azuis (destaque) / cinza; card até 1500×820 |
| **M3** | `"layout": "M3"`, card de mapa com `"dissolve": true` e `"troca"` (outro mapa; aceita `"mapa": {...}`) | troca por dissolução de 0,4 s (v6#75) |
| **M5** | `"layout": "M5"`, card paisagem com `"lateral": {"mapa": {"pais": [...], "globo": true}}` | card ~1190×790 centralizado; globo = **85% da altura do card** (~670 px, não 30%), cobre 33% da borda direita e entra **rolando** (v7#181) |
| **M6** | `"layout": "M6"`, 1º card `"mapa": {..., "silhueta": true}` + card de mapa | silhueta recortada (país cinza, região na cor) ao lado do mapa — é um E2 (v7#197) |
| **M7** | card de mapa com `"sticker": {busca de bandeira, "pos": "dentro"}` | bandeira pequena (13% da altura) dentro do mapa, no alto à direita (v6#74) |
| **T1** | `"sai": "baixo"` no card (já existia; cards centralizados já saem por baixo) | motion blur já ligado |
| **T2** | `"entra": "dir"` / `"esq"` / `"baixo"` no card (já existia) | |
| **T3** | `"dissolve": true` no card com `"troca"` | 0,4 s |

## Diferenças de estilo notadas em v5–v8 (não mudam nossa identidade)
- Os 4 vídeos usam **sans bold arredondada** (tipo Poppins) em caixa normal nos títulos e textos, não Impact. Nossa fonte segue a [[Identidade Visual]].
- O texto das legendas encadeadas é **menor** (~45 px de altura de caixa) que o nosso A1.
- v5 tem poucas sequências F: muitas cenas de 10–20 s num card só com zoom leve. v6/v8 compensam com C8 e B6.
- Não aparecem setas, círculos, contadores nem linhas do tempo; datas e números sempre como B7 branco sobre o card ("1952", "1,250 calories").

---

## Como isso muda o trabalho
**Planejamento** ([[Da Narração às Cenas]]):
- Planejar **sequências**: uma frase de 4–8 s com 2–4 gatilhos vira uma cena F, não várias cenas soltas.
- 12–20% texto (A) e **cada código uma vez só por bloco** (2026-10-13), usando todas as famílias.
- Densidade sobe: uma sequência consome 2–5 assets → **~20–25 assets por minuto**.

**Busca de assets** ([[Como Buscar Assets]]):
- Muito mais **vídeo vertical** (B2, B6) → buscar shorts/TikTok/reels do lance ou do jogador.
- **Retratos** de pessoas (B8, C6, D3), **mapas com destaque** (C5), **logos/escudos em PNG** para sticker (E4), **produtos/objetos recortados** (E2, E3, C7).

**Editor** ([[Edição no After Effects]]):
- **Implementados em 2026-10-05:** C8, D5, D6, B10 (teste aprovado em 2026-10-05; arquivos de teste apagados).
- **Implementados em 2026-10-05 (2ª leva):** A4, B11, G1.
- **Implementado em 2026-10-05 (3ª leva):** gerador de mapas (M1/M2/M4).
- **Implementados em 2026-10-05 (4ª leva):** B9, D7, E5, E6, F8, F9, G2, G3, M3, M5, M6, M7, T1–T3 → **toda a biblioteca v5–v8 está no editor** (teste aprovado em 2026-10-05; arquivos de teste apagados).
- Suportar: cascata (C2), rótulo que troca (B5), troca no lugar (B6), mini-legenda (B7), rótulo acima por card (C4), 1+N empilhados (D2), esteira (D4), sticker (E4), frase que se completa (A2) e as sequências F com saída/entrada sobrepostas.
- Gap entre cards: 15–50 px; cards grandes (≈ 85% da altura).
