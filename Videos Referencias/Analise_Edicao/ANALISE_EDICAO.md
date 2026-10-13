# Análise de Edição — formato "___ Explained" (cards sobre fundo de papel)

**Vídeos analisados (todos 1920×1080, 60 fps):**

| # | Vídeo | Duração | Itens | Cenas* | Palavras narradas | Ritmo da fala |
|---|---|---|---|---|---|---|
| v1 | Ramens Explained | 12:09 | 9 | 213 | 2.384 | ~197 ppm |
| v2 | Every Chocolate Candy Explained | 15:16 | ~11 | 181 | 2.917 | ~191 ppm |
| v3 | Luxury Food Explained | 16:03 | ~11 | 204 | 3.354 | ~209 ppm |
| v4 | All Sugars Explained | 18:33 | ~13 | 281 | 3.481 | ~188 ppm |

\*Cena = trecho entre dois momentos de "palco vazio" (fundo sem nenhum elemento).

**Método:** detecção de cortes (ffmpeg), análise numérica de 20 frames/s nos quatro vídeos (fundo vazio, duração das cenas, tipo de saída), faixas em 60 fps das animações de entrada, saída, texto e título, medição de posição e escala dos cards quadro a quadro, transcrição palavra a palavra (whisper) para cruzar fala × imagem, e análise do nível do áudio. Os frames de referência estão em `frames/`.

> Os quatro vídeos seguem **exatamente o mesmo sistema**: é um template. Tudo abaixo vale para os quatro, salvo indicação.

---

## 1. Conceito em uma frase

Um narrador lê uma lista de itens ("Shoyu ramen", "Snickers", "White sugar"…). A tela é um **fundo de papel cinza-claro fixo**. Sobre ele entram e saem **cards de foto/vídeo com cantos arredondados e sombra**, **PNGs recortados** e **frases em texto preto grande**, sempre sincronizados com a palavra que está sendo dita. Não há apresentador, música, efeitos sonoros, vinheta, intro ou outro.

---

## 2. Especificações globais

### 2.1 Fundo (constante no vídeo inteiro)
- Cinza muito claro, quase branco: centro ≈ `#F3F3F3` (243), bordas ≈ `#E5E5E5` (229).
- **Vinheta suave** escurecendo os cantos (~-15 níveis nos cantos).
- **Textura de papel** sutil (pintinhas/fibras cinza, baixo contraste) — veja `frames/06_layout_texto_solo.png`.
- O fundo **nunca se move nem dá zoom**; só os elementos por cima se movem.
- Observação: há uma faixa preta de 4 px no topo e na base do frame. Parece defeito de exportação; **não replicar**.

### 2.2 Card (o elemento principal)
Foto ou vídeo dentro de um retângulo com:
- **Cantos arredondados**: raio ≈ 5% do lado menor do card (≈ 28 px num card de 540 px de largura; ≈ 40–45 px num card grande de 900+ px).
- **Sem borda/contorno.**
- **Sombra projetada difusa**: preta, opacidade ~45–55%, desfoque grande (~25–35 px), deslocamento ~0 a 5 px para baixo, espalhada dos quatro lados (fica um halo escuro ao redor do card) — veja `frames/10_detalhe_canto_e_sombra.png`.
- Mantém a proporção original do asset: há cards em retrato (9:16 / 3:4, muito comuns para vídeos verticais), em paisagem (16:9 / 4:3) e quadrados.
- **O conteúdo pode ser vídeo** (b-roll de stock, muitas vezes vertical, rodando em loop/tempo real) **ou foto**. Mais ou menos metade é vídeo.
- Variante "card branco": imagem recortada sobre fundo branco dentro do card (logos como MARS, produto sobre branco).

### 2.3 PNG recortado (sem card)
- Objeto sem fundo (tigela, açucareiro, bandeira, garrafa, limão).
- Recebe a **mesma sombra difusa**, mas segue o contorno do objeto.
- Usado no **título de cada item** (sempre) e às vezes no meio das cenas (bandeiras, ingredientes, produtos).

### 2.4 Tipografia
- Uma única família: **sans-serif geométrica, peso ExtraBold/Black** (visualmente Gilroy ExtraBold; alternativas gratuitas quase idênticas: **Montserrat ExtraBold** ou Plus Jakarta Sans ExtraBold).
- Caixa de frase (não é TUDO MAIÚSCULO): "Shoyo means soy sauce", "around the 1400s".
- Sem contorno. Sem caixa de fundo.
- Três estilos de texto (detalhes na seção 4):
  1. **Texto solo**: preto `#000`, centralizado na tela, sombra muito sutil.
  2. **Texto sobre card**: branco, centralizado no card, sombra preta suave para dar leitura.
  3. **Rótulo**: preto, ao lado ou acima de um card/PNG.

### 2.5 Áudio
- **Só narração** (voz masculina, ritmo rápido de ~190–210 palavras/min, provavelmente TTS).
- **Sem música de fundo e sem efeitos sonoros**: nas pausas o áudio cai para -55 a -70 dB (silêncio digital). Nenhum whoosh nas transições.
- Pausas naturais de 0,2–0,5 s entre frases; ~0,4 s de silêncio entre um item e outro.

---

## 3. Estrutura macro do vídeo

```
[ITEM 1 título] → cenas do item 1 (~1:20–1:30) → [ITEM 2 título] → cenas … → [ITEM N] → cenas → TELA VAZIA ~8–10 s (fim)
```

- **Sem gancho/intro/abertura**: o frame 0 já é o título do primeiro item. A primeira palavra do vídeo é o nome do primeiro item.
- **Sem encerramento falado nem CTA visual**: a última frase de conteúdo termina, a cena sai e ficam **~8–10 s de fundo vazio e silêncio** (espaço para a tela final do YouTube).
- Cada item dura em média 1:15–1:30 (12–20 cenas por item).
- Dentro do item, o roteiro segue quase sempre: definição → origem/história (datas, lugares, pessoas) → como é feito/ingredientes → sabor/textura → curiosidade/cultura → status atual.

### 3.1 Título do item (abre cada item) — `frames/05_layout_titulo_item.png` e `frames/01_titulo_item_pop_60fps.jpg`
- **Layout:** nome do item no topo central (texto preto, grande: altura das maiúsculas ≈ 120–130 px, topo do texto em y ≈ 75 px, largura ≈ 55–60% da tela) + **PNG recortado grande** do item no centro (≈ 900–1000 px de largura, centro em ≈ (960, 560)). O PNG pode encostar no texto ou passar por trás dele (a alga passa por baixo do "S").
- **Narração:** o narrador fala só o nome ("Shoyu Ramen."), faz uma pausa e depois começa a frase que repete o nome ("Shoyu ramen is basically…").
- **Animação de entrada (60 fps medido):**
  - Texto e PNG começam juntos, ~0,05 s depois do início do áudio do nome.
  - **PNG: scale pop** de ~0% → 100% em ~0,27 s (16 frames), ease-out forte (cresce rápido e desacelera; sem overshoot visível).
  - **Texto: fade de opacidade** 0 → 100% em ~0,17 s (10 frames), sem movimento.
- **Duração na tela:** só o tempo do nome falado + a pausa (≈ 1,2–1,6 s).
- **Saída:** **corte seco** para o fundo vazio (2–6 frames vazios) e a primeira cena do item entra.
- Variantes: em alguns itens há **subtítulos** de subtipo ("White miso" / "Red miso" acima de cada card) com o mesmo estilo de rótulo.

---

## 4. Catálogo de tipos de cena

Contagem aproximada no vídeo de Ramen (213 cenas; veja `frames/11_` e `frames/12_`):

| Tipo | % aprox. | Descrição | Quando usar |
|---|---|---|---|
| **A. Texto solo** | ~30% | Frase de 2–6 palavras em preto, centralizada, sem imagem | Frases abstratas, conectivos, opiniões, quando não há imagem literal ("but balanced", "That mix created what") |
| **B. 2 cards lado a lado** | ~25% | Dois cards (normalmente retratos) centralizados com gap de ~60 px | Comparações, dois aspectos, processo em 2 passos |
| **C. 1 card central** | ~15% | Um card grande centralizado | Imagem que ilustra a frase inteira |
| **D. Card + texto branco por cima** | ~10% (sobreposto a B/C) | Frase ou palavra-chave em branco no centro do card | Datas, números, frases curtas de ênfase ("around the 1400s", "first big boom in Tokyo") |
| **E. Card + rótulo preto ao lado** | ~8% | Card à esquerda (ou direita) e texto preto grande ao lado | **Nomes próprios, datas e números**: "Rairaiken", "until 1910", "Chef Koizumi", "Alkaline", "from 6 to 18 hours" |
| **F. 3 cards** | ~6% | 3 cards em linha, ou 1 grande + 2 pequenos empilhados | Listas de ingredientes, variações |
| **G. Rótulo acima do card** | ~4% | Texto preto pequeno logo acima de um card | Legenda curta ("in the traditional version", "color of the ocean in Hawaii") |
| **H. PNG recortado solto** | ~3% | Objeto sem fundo, às vezes em coluna (3 bandeiras) | Bandeiras de países, produto isolado |
| **I. Mapa** | ~2% | Card com mapa e região destacada em laranja/vermelho/verde | Sempre que se fala de um lugar (Tacoma, Piedmont, Hakata, Japão) |
| **J. Título de item** | 1 por item | Ver 3.1 | Início de cada item |

### 4.1 Regras de composição
- **Tudo é centralizado no grupo**: o conjunto de elementos fica centrado na tela (eixo x = 960; eixo y ≈ 520–540).
- O conjunto ocupa normalmente **55–85% da largura** e **65–85% da altura**. Margem mínima até a borda ≈ 80–130 px.
- **1 card**: largura de 900–1350 px (paisagem) ou altura de 800–880 px (retrato).
- **2 cards**: alturas parecidas (≈ 780–830 px), gap ≈ 50–70 px, juntos centralizados. Não precisam estar perfeitamente alinhados (diferenças de 5–10 px são normais — dá um ar orgânico).
- **3 cards**: menores (≈ 500–560 px de altura), gap ≈ 20–30 px.
- **Card + rótulo (E)**: card ocupa ~45% à esquerda; o texto preto fica centralizado verticalmente no espaço livre à direita (ou o inverso). Tamanho do texto ≈ 100–130 px de altura de maiúscula.
- **Sobreposição**: um card novo pode entrar **por cima** de um que já está na tela, cobrindo parte dele (mapa entrando sobre a foto de Frank Mars; card branco do Toblerone sobre o outro). Novos elementos sempre ficam numa camada acima.
- **Reposicionamento**: quando entra o 2º/3º card, os primeiros **não se reorganizam**; cada um já entra direto na posição final do layout completo. Por isso o 1º card de um par às vezes aparece descentralizado por um instante, esperando o 2º.

---

## 5. Sistema de animação (o coração do estilo)

Todo elemento tem 3 fases: **ENTRADA → FLUTUAÇÃO → SAÍDA**.

### 5.1 Entrada de card (medido em 60 fps — `frames/02_entrada_cards_60fps.jpg`)
- **Slide de fora da tela** até a posição final, vindo da **borda mais próxima** da posição final (card embaixo → vem de baixo; card à direita → vem da direita; card em cima → vem de cima). De baixo é o mais comum.
- O card começa **totalmente fora do quadro** (ou com só a borda aparecendo).
- **Duração do deslocamento principal: ~0,25–0,33 s (15–20 frames a 60 fps)**.
- **Easing: ease-out exponencial forte** (sai muito rápido e desacelera longamente). No After: keyframe de saída com influência ~90–100%, ou expressão `easeOut`/exponencial.
- **Opacidade** 0 → 100% durante os primeiros ~0,2 s.
- **Motion blur ligado** (o card fica borrado na direção do movimento nos primeiros frames). Além do motion blur, os primeiros 3–5 frames parecem ter um leve desfoque gaussiano que some.
- **Depois de chegar, o card continua deslizando bem devagar na mesma direção** (resto da curva ease-out, ~20–40 px no 1º segundo). Isso faz parecer que ele "flutua até parar".
- **Escalonamento entre cards da mesma cena:** cada card entra **na palavra que ele ilustra**, então o intervalo varia de ~0,2 s a vários segundos. No exemplo de abertura do Ramen: 2º card 0,45 s depois do 1º, 3º card ~0,2 s depois do 2º.

### 5.2 Entrada do PNG recortado
- Igual ao título: **scale pop de ~0% a 100% em ~0,25 s, ease-out** (ou slide como card quando está dentro de uma composição de cards).

### 5.3 Entrada de texto (medido em 60 fps — `frames/04a_` e `frames/04b_`)
- **Fade de opacidade 0 → 100% em ~0,17–0,2 s (10–12 frames)** + **desfoque que vai de ~8 px para 0** no mesmo tempo.
- **Sem movimento de posição e sem escala.**
- O texto aparece **inteiro de uma vez** (não é palavra por palavra, não é máquina de escrever).

### 5.4 Flutuação (enquanto a cena está na tela) — medido numericamente
- **A cena inteira faz um push-in lento e linear**: todos os elementos da cena escalam juntos **a partir do centro da tela** (não do centro de cada card). Nos 2 cards lado a lado, a borda interna de cada um fica parada no centro e as bordas externas se afastam.
- Velocidade medida: **+1,4% a +4,6% de escala por segundo**, linear, sem easing (típico ≈ +2,5%/s). Ex.: um card foi de 1203 → 1386 px em 3,3 s; o logo MARS foi de 1171 → 1269 px em 6 s.
- Na prática: **cada cena escala de 100% → ~108–115% ao longo da sua duração**, linear.
- Textos sobre o fundo também participam do push-in (de forma mais discreta).

### 5.5 Saída de cena — dois tipos (medido)

| Tipo de saída | v1 Ramen | v2 | v3 | v4 |
|---|---|---|---|---|
| **Corte seco** (tudo some em 1 frame) | 85% | 59% | 64% | 68% |
| **Saída animada** (cards voam para fora) | 15% | 41% | 36% | 32% |

**Corte seco** — sempre usado para:
- texto solo → próxima cena;
- título do item → 1ª cena do item;
- troca de frase de texto (a frase anterior some em 1 frame, ficam ~5 frames vazios e a próxima faz fade-in).

**Saída animada** (`frames/03a_` e `frames/03b_`) — usada principalmente em cenas com 2+ cards:
- Os cards **aceleram para fora da tela** (ease-in: começam devagar e saem muito rápido), cada um para a **borda mais próxima** — muitas vezes em direções opostas (o da esquerda cai/sai pela esquerda, o da direita sobe/sai pela direita).
- Duração ≈ **0,4–0,6 s**, com o terço final bem rápido e com **motion blur**.
- **A entrada da cena seguinte começa antes da saída terminar** (~0,1–0,25 s de sobreposição), por isso muitas vezes nem há frame vazio.

### 5.6 Palco vazio entre cenas
- Medido nos 4 vídeos: **mediana de 0,1–0,2 s** (6–12 frames a 60 fps), máximo ~0,3 s dentro do conteúdo.
- É só o tempo entre o corte e o novo elemento ficar visível. **Nunca há pausa longa de tela vazia**, exceto no fim do vídeo.

### 5.7 Elementos somando dentro da cena
- Dentro de uma cena, os elementos **se acumulam**: card 1 → card 2 → texto por cima → card 3. Nada sai no meio da cena; tudo sai junto na saída.
- O texto sobre card **troca de frase** sem tirar o card: a frase A some por corte, a frase B faz fade-in no mesmo lugar ("The place got huge" → "serving thousands of bowls" → "kicked off ramen's first big boom in Tokyo", tudo sobre a mesma foto).

---

## 6. Sincronia com a narração (regras de timing)

Medido cruzando transcrição palavra a palavra × frames:

1. **Cada elemento visual entra na palavra que ele ilustra literalmente**, com antecipação de **~0,05–0,3 s** (o elemento chega junto ou um pouquinho antes da palavra).
   - "created by **Mars** Inc." → logo MARS; "launched in **1930**" → "1930" aparece sobre o logo; "**Frank Mars**" → foto + rótulo; "out of **Tacoma**, Washington" → mapa entra por cima; "**Snickers** became his…" → card do produto.
2. **Texto solo = a própria narração em pedaços (legenda gigante)**: a frase falada é quebrada em **trechos de 2–6 palavras** (ou por unidade de sentido) e **cada trecho aparece quando sua primeira palavra começa** e fica até o início do próximo trecho. O texto é a transcrição literal do que se ouve (inclusive erros: "Shoyo", "Tokyos").
3. **Texto sobre card ou rótulo** = só a palavra-chave/trecho de destaque (datas, números, nomes, frases de efeito), também no momento exato em que é dita.
4. **Troca de cena acompanha a troca de ideia/frase** da narração. Duração das cenas (medida):
   - mediana **1,35–2,7 s**; 10% das cenas < 0,7 s; 10% > 7–12 s;
   - cenas longas (10–20 s, raramente até 38 s) acontecem quando há um único vídeo de b-roll longo — é exceção, não regra.
5. **Densidade de troca**: algo novo (card, texto ou troca de frase) a cada **~1–2 s**. A tela nunca fica parada mais de ~3 s sem novidade, exceto quando há um vídeo em movimento dentro do card.
6. **Alternância**: o editor alterna cenas de imagem e cenas de texto solo. Sequências típicas: `cards → cards → texto → texto → texto → cards → card+rótulo → texto…`. Raramente há mais de 4 cenas de texto solo seguidas.
7. **Título do item** fica na tela exatamente enquanto o nome é falado + a pausa; a primeira cena do item entra quando a frase seguinte começa.

---

## 7. Especificação do texto em detalhe

| Estilo | Cor | Tamanho | Posição | Extras |
|---|---|---|---|---|
| **Texto solo** | Preto #000 | **Ajustado para caber em ~1660 px de largura (≈86% da tela)**: frases curtas ficam enormes (altura das maiúsculas ~110 px), frases longas ficam menores (~60 px). Mínimo legível ≈ 55 px de maiúscula | Centro da tela (960, ~535), 1 linha | Sombra preta bem leve (opacidade ~15–20%, desfoque ~10 px) |
| **Texto sobre card** | Branco #FFF | Altura das maiúsculas ~70–110 px; cabe dentro da largura do card (às vezes ultrapassa um pouco, atravessando 2 cards) | Centro do card ou do grupo de cards | Sombra preta (~60–70%, desfoque ~8–12 px) para legibilidade |
| **Rótulo lateral** | Preto | Grande (maiúscula ~100–130 px) se for 1–2 palavras; 2 linhas centralizadas se for mais longo ("Yokohama's / Chinatown", "Subzero / temperatures") | Centralizado no espaço vazio ao lado do card, alinhado ao centro vertical do card | Mesma sombra leve do texto solo |
| **Rótulo acima do card** | Preto | Pequeno (maiúscula ~35–45 px) | Centralizado, logo acima da borda superior do card (~15 px de distância) | — |
| **Título do item** | Preto | Grande (maiúscula ~120–130 px) | Topo central (topo do texto em y≈75) | — |

- Sempre **1 linha** no texto solo (por isso o tamanho varia). Rótulos podem ter 2 linhas.
- Mantém maiúsculas/minúsculas como na frase; nomes próprios com maiúscula.
- Números ficam como números ("1930", "6 to 18 hours", "350 BC").

---

## 8. Valores de referência para o After Effects / DaVinci

### After Effects
- Composição 1920×1080, **60 fps** (30 fps também funciona, mas os originais são 60).
- **Motion blur** ativo na comp e nas camadas de card (shutter 180°).
- Card = camada de footage + **máscara/shape de retângulo arredondado** (ou "Roundness" via track matte) + **Drop Shadow** (Opacity 50%, Distance 3–5, Softness 60–70 a 1080p).
- Cada cena = uma pré-composição ou um grupo com um **Null pai no centro da tela (960, 540)** que recebe o push-in: `Scale` linear de 100% → 100% + 2,5% × duração(s) (limite ~115%).
- Entrada: `Position` de fora da tela → posição final em ~0,3 s com easing exponencial (velocidade de influência ~95% no keyframe final) + continuação lenta de ~20–40 px no próximo ~1 s; `Opacity` 0 → 100 em 0,2 s.
- Saída animada: `Position` → fora da tela em ~0,45 s, ease-in forte (influência ~90% no keyframe inicial).
- Texto: `Opacity` 0 → 100 e `Gaussian Blur` 8 → 0 em 10–12 frames (a 60 fps).
- PNG de título: `Scale` 0 → 100% em 16 frames, ease-out.

### DaVinci Resolve
- Mesmos valores, usando Fusion (Transform + Merge + Rectangle com Corner Radius + DropShadow + Motion Blur no Transform) ou, na página Edit, Dynamic Zoom/Transform com keyframes "Ease Out" + Edit > Retime/Motion blur via Fusion. Para um agente automatizar, **o After Effects via ExtendScript (.jsx) é bem mais controlável** do que o Resolve; no Resolve, a automação via API Python não controla bem keyframes de transformação, então seria preciso gerar comps do Fusion (.setting/.comp).

---

## 9. O que o agente precisa receber (para a próxima etapa)

Para reproduzir o formato, cada vídeo precisa de:
1. **Narração** (arquivo de áudio) + **roteiro** dividido por item.
2. Por item: **PNG recortado** do item (para o título).
3. Por trecho do roteiro: **assets** (fotos/vídeos/PNGs/mapas) com a **palavra-gatilho** de cada um.
4. Transcrição com tempo por palavra (o agente consegue gerar com whisper).

E vai decidir sozinho:
- quebra da narração em cenas e em trechos de texto solo de 2–6 palavras;
- qual tipo de cena usar (A–J) conforme o número de assets e se o trecho é nome/data/número;
- layout (posições/tamanhos) pelas regras da seção 4.1;
- timing pelas regras da seção 6;
- animações pela seção 5 (corte seco vs saída animada ~35%/65%).

---

## 10. Diferenças em relação ao "banco-de-edicao" (Simple Paint)

Para não misturar as regras: o formato Simple Paint usa **só corte seco, nada se move**. Este formato é o oposto em movimento: **slide-in com ease-out e motion blur, push-in contínuo, saídas animadas em ~35% das cenas e fade+blur nos textos**. O que se parece: elementos se somam dentro da cena, o elemento entra antes da palavra, o áudio é só narração.

---

## 11. Pontos de incerteza (para você confirmar)

- **Fonte exata**: Gilroy ExtraBold ou Montserrat ExtraBold (são quase iguais nesta resolução). Se você tiver o arquivo da fonte que pretende usar, melhor.
- **Valores de sombra** (opacidade/desfoque) estimados pelo olho e pela medição de pixels, com margem de ±10%.
- **Push-in**: a taxa varia por cena (1,4–4,6%/s); não está claro se o editor original usava "% por segundo" fixo ou "100→110% por cena". Proponho +2,5%/s com limite de 115%.
- **Escolha corte seco × saída animada**: não segue uma regra rígida; no Ramen quase tudo é corte seco. Proponho: texto e título sempre corte seco; cenas de card com saída animada em ~40% dos casos, de preferência quando a próxima cena também é de card.
- As 4 faixas pretas de 4 px: assumi que é defeito e não devem ser replicadas.
