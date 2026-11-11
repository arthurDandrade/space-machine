# Vídeos de referência do cartum

Medido em 2026-11-09 em 4 vídeos de um mesmo canal de listas em desenho (os arquivos ficam em `<dados>/referencias/cartum/`, nunca no repo): líderes de seita, torturadores, estruturas antigas e documentários. Só os arquivos foram medidos; nada foi buscado no YouTube.

## Números
| Vídeo | Duração | Palavras | Palavras/min | Cortes fortes (mediana) |
|---|---|---|---|---|
| Líderes de seita | 26 min | 4.148 | 157 | a cada 4,5 s |
| Torturadores | 22 min | 3.499 | 157 | a cada 6,8 s |
| Estruturas antigas | 25 min | 3.728 | 151 | a cada 6,3 s |
| Documentários | 19 min | 2.731 | 143 | a cada 10,8 s |

- **Elemento novo na tela a cada 1,6–1,8 s** (mediana, medido nos 10 primeiros minutos de dois vídeos: ~300 entradas em 10 min). "Corte forte" é a tela inteira trocando.
- **Entrada em corte seco**: o elemento aparece inteiro de um quadro para o outro, sem fusão, sem deslizar e sem zoom.
- 1920×1080; 24 a 30 quadros por segundo conforme o vídeo.

## Roteiro
- Sem introdução: a 1ª palavra narrada é o nome do 1º tópico. Sem despedida nem pedido de inscrição: acaba na última frase do último tópico.
- ~24 tópicos de ~170 palavras no vídeo de pessoas; a 1ª frase de cada tópico começa pelo nome dele.
- Dois moldes: pessoa (origem → poder → o que fez → virada → morte com data e idade → o que ficou) e lugar/obra (o que é → de onde vem → como é → o que não se explica → fecho seco).

## Tela (em 1920×1080)
- Fundo liso `#BFE9FF` o vídeo inteiro.
- Nome do tópico centrado no topo (letra de mão, ~80 px, centro em y≈45); data ou número logo abaixo (~50 px, y≈112).
- Miniatura do tópico no canto de cima à direita (~140×130 px, centro em 1838×72) nos vídeos de pessoas; o de estruturas não tem.
- Desenhos de traço preto grosso e cor chapada, recortados, espalhados pela tela e às vezes um por cima do outro (o personagem na frente do mapa).
- Foto real pequena com a borda esfumada e o nome em cima, quase sempre na 1ª tela do tópico.
- Recorrentes: mapa com o lugar marcado, ícones, seta vermelha, X vermelho, círculo vermelho, balão de fala, número ou data em texto, pixelado no que é violento.
- **Abertura**: uma grade com todos os tópicos (desenho + nome, 7 colunas × 4 linhas) fica 0,8 s, aproxima em 0,5 s para os primeiros e corta para o 1º tópico aos 2 s, já com a narração. Entre tópicos a grade volta por ~0,7 s e aproxima no seguinte.
- No vídeo de estruturas um mascote (um explorador de colete e chapéu) reage em quase toda tela: pensa, aponta, anota, dá de ombros.

## O que o Space Machine faz diferente (2026-11-09)
- O layout é automático (colunas na ordem dos cards), não desenhado à mão tela a tela.
- A grade de abertura (2026-11-09): cada tópico abre com a grade de todos (0,8 s parada no 1º, 0,5 s nos outros); em 0,6 s a câmera aproxima no tópico que vai começar, os outros se afastam e somem, e o desenho e o nome dele crescem até o cartão do tópico — as mesmas camadas, sem corte. Na 1ª versão a grade cortava para o cartão e o desenho pulava de tamanho e de lugar. Conferido com 2 tópicos (o teste de futebol) e com uma grade fictícia de 22. Na referência a grade aproxima, para 1 s e corta direto para a 1ª tela, sem cartão; aqui o cartão fica enquanto a 1ª frase é dita.
- Pessoa real nunca é desenhada (regra do Space Machine): entra como foto, e o desenho ao lado é genérico.
- Sem pixelado: o que precisaria dele não é desenhado.

## Primeiro teste de ponta a ponta (2026-11-09)
Um tópico ("Derinkuyu", 42 s, narração provisória pela voz do macOS) no canal `cartum-teste`, pelo orquestrador:
- Storyboard aprovado em 2 voltas: 6 telas, 19 cards, 4 variações (R1, P2, P3, P4), um asset a cada ~2 s; nenhuma tela com um desenho só.
- 14 desenhos pedidos ao Flow (42 imagens, ~12 min de sessão, 0 créditos) e 1 foto real do Commons. O mascote e o corte da cidade, com `elenco`, voltaram em 3 telas sem gerar de novo.
- Escolha: 15 assets em 61 s; 5 trocas automáticas na conferência (recorte ou cena errada), todas resolvidas com outra das 3 opções.
- Render: prévia 960×540 em 12 s; 1920×1080 a 30 qps em 42 s (1× a duração). QA aprovado na 1ª versão.
- O recorte por fundo liso saiu limpo nos 14, inclusive manga e camisa brancas.
- Extrapolando para um vídeo de 20 tópicos: ~280 desenhos, ~4 h de sessão no Flow. O que mais corta isso é o elenco (mascote e ícones repetidos).

## Segundo teste (2026-11-09): futebol americano, voz do Fish Audio, fundo magenta
Dois tópicos ("The Quarterback" e "The Long Snapper", 55 s no total) no canal `cartum-football-teste`:
- Narração pelo Fish Audio (`s2.1-pro-free`): 29 s e 26 s para ~105 e ~90 palavras (~210 palavras/min, mais rápido que os ~155 da referência).
- 24 desenhos no Flow (72 imagens, ~25 min de sessão, 0 créditos) e 2 fotos reais. Com o fundo magenta, nenhum recorte ficou com resto de fundo, inclusive grade do capacete, alça do cronômetro e vãos entre pernas.
- Os dois tópicos passaram no QA na 2ª versão, depois de uma correção automática cada.
- Ajustes de layout que o teste pediu: com círculo em volta do card, o nome e a legenda vão para fora dele (o traço passava por cima do texto); o adesivo fica abaixo do cabeçalho (encostava na miniatura do canto).
- O que continua aparecendo: o mesmo personagem muda de rosto e de proporção entre poses (o quarterback de 4 telas são 4 desenhos diferentes). Falta a imagem de referência no pedido do Flow.

## Terceiro teste (2026-11-09): personagem com referência e grade de abertura
Os mesmos dois tópicos de futebol, refazendo só os desenhos de quem aparece em mais de uma pose:
- 4 personagens (quarterback, treinador, long snapper, punter): 4 fichas + 10 poses no Flow, ~14 min de sessão. Com a ficha anexada como referência, as poses saem com o mesmo rosto, corpo, roupa e cores.
- A referência fica presa à caixa do Flow entre uma geração e outra, então o custo a mais é uma geração (a ficha) por personagem.
- A etapa de escolha pediu "outra busca" para 2 desenhos gerados e isso criou 6 pedidos soltos, sem personagem, que seguraram o outro tópico. Corrigido: o prompt de escolha não pede nova busca para desenho, e a busca só para pelo Flow se o PRÓPRIO bloco ficou com asset sem candidato.
- Mancha rosa entre as pernas do treinador: o magenta do fundo veio um pouco irregular, o teste de "borda lisa" reprovou e o recorte caiu no rembg. Corrigido medindo "o quanto é da cor-chave" (min(R, B) − G), que não muda com a claridade: os 18 recortes dos dois tópicos passaram, nenhum pelo rembg.
- Grade de abertura: com 2 tópicos a aproximação é pequena (1,15×); com 24 chega a 2,6×, como na referência.

## Quarto teste (2026-11-10): vídeo inteiro de 10 tópicos
"Every NFL Team That Disappeared" no canal `cartum-football-teste`: 10 times, 1.563 palavras, 10 min 30 s, 1920×1080 a 30 qps.
- Narração pelo Fish Audio a 0,85 de velocidade: ~150 palavras/min, como na referência (a 1,0 dava ~210).
- Storyboard: 9 tópicos aprovados em 2 voltas, 1 com um aviso aceito. Por tópico: 9 a 10 telas e 14 a 19 assets.
- Flow: 109 pedidos (11 fichas de personagem, 37 poses, 61 desenhos avulsos), 327 imagens, ~74 min de sessão, 0 créditos, nenhuma recusa. Um jogador-símbolo por time (a mesma ficha, cores diferentes) e o treinador mascote com a referência do teste anterior. O elenco do vídeo fechou em 44 desenhos reaproveitados entre os tópicos.
- Escolha + render + QA + entrega: ~2 min por tópico (os 10 em ~20 min, um por vez), ~240 mil tokens equivalentes por tópico.
- Vídeo final (`final --render`, a 1ª vez do cartum): 10 min 30 s de render para 10 min 30 s de vídeo. O gerador roda de novo em cada tópico e a grade de abertura sai com os 10 times.
- **Tela vazia**: 8 dos 10 tópicos reprovaram no QA na 1ª versão por 0,6 a 2 s só de fundo (o gatilho do 1º card da tela vinha no meio da frase) e por rótulo com menos de 0,7 s. A correção automática resolvia, ao custo de um render e uma chamada a mais por tópico. Corrigido no gerador: o card que entra primeiro entra junto com a tela, e rótulo, legenda e balão são adiantados para ficar 1 s.
- **Duas datas no mesmo estado** ficavam uma por cima da outra ("1944" e "1945"). Corrigido: uma sai quando a outra entra.
- **Id repetido**: numa volta de correção do storyboard, um card novo ganhou o id de um card que vinha depois; os dois dividiram a pasta de candidatos, a escolha recebeu o desenho errado e o tópico parou. Corrigido no `compilar_cenas.py` (ids escritos ficam reservados; id repetido troca).
- O que continua aparecendo:
  - Mapa pequeno com os nomes da cidade e do estado um por cima do outro ("CLEVELAND/CANTON/OHIO"), e com cara de foto, fora do traço do formato.
  - Foto histórica de gente pouco conhecida: a escolha marcou "conferir" em várias (dono de time, jogador numa foto de time). O nome que aparece em cima da foto precisa de conferência humana antes de publicar.
  - Na grade, o nome do tópico que vai abrir fica numa linha só (menor) enquanto os outros quebram em duas.

## Áudio picotado: o roteiro é que estava em frases soltas (2026-11-10)
Quem assistiu ao vídeo de 10 tópicos achou a narração picotada, "frase a frase". A narração é gerada num pedido só por tópico; o que picota é o texto:
- O roteiro do teste tinha 10,6 palavras por frase em média, 30% das frases com até 8 palavras e só 6% com 16 ou mais. Os 4 vídeos de referência têm de 15,0 a 20,4 em média, 1% a 18% de curtas e 43% a 72% com 16 ou mais.
- A voz (Fish Audio) para de 0,6 a 1,0 s em cada ponto final. Num tópico de 68 s eram 14 frases e 9 pausas de mais de 0,5 s.
- O mesmo tópico reescrito por ideias (8 frases, os fatos da mesma ideia na mesma frase): 6 pausas de mais de 0,5 s.
- A velocidade 0,85 também estica as pausas (até 1,0 s). Com o texto por ideias, 0,92 dá 159 palavras/min (0,85: 147; 1,0: 171; a referência tem 143 a 157) com pausas de até 0,8 s.
- No sistema: o `roteiro_modelo.md` pede frase por ideia (14 a 22 palavras, com exemplo do picotado e do fluido) e o agente de roteiro mede isso (`roteiro.medidas.frases` no `formato.json`: média de 14 a 22, no máximo 20% de frases curtas) e reescreve se sair fora.

## Quinto teste (2026-11-10): o mesmo vídeo com roteiro por ideias e logo real na grade
"Every NFL Team That Disappeared" refeito (o anterior ficou como `-v1`): 10 tópicos, 1.626 palavras, 9 min 58 s.
- Roteiro pelo agente, com os fatos do anterior: 99 frases no lugar de 145, 16,3 palavras por frase (antes 10,6), 2% de frases curtas (antes 30%). Passou na medida de frases na 1ª resposta.
- Narração a 0,92: 594 s, ~164 palavras/min. Pausas de mais de 0,5 s: 79 no vídeo (8,0 por minuto) contra 106 (10,1 por minuto) na versão picotada.
- Os 10 tópicos passaram no QA na 1ª versão (no teste anterior, 8 de 10 precisaram da correção automática): é o efeito de o 1º card entrar junto com a tela.
- **Logo real como símbolo do tópico** (`"titulo": {"tipo": "logo"}`): a busca (web) trouxe 5 boas de 10 (Akron, Oorang, Columbus, Dayton, Dallas). As outras 5 a escolha automática errou e foram trocadas à mão na revisão: logo numa faixa clara que ficou com o retângulo (Canton: corrigido no `limpar_logo`), foto de camisa (Duluth), recorte de página com texto (Pottsville), logo sobre foto (Providence) e uma folha com 6 logos de épocas diferentes (Vikings). Para Duluth e Pottsville o melhor candidato era um emblema bordado dentro de uma página: foi recortado à mão. Time dos anos 1920 quase nunca teve logo oficial: o que existe é emblema de época ou logo retrô de site de estatística, e precisa de conferência humana.
- **O Flow recusou a fila nova** (81 pedidos) com "atividade incomum", horas depois da fila de 108. O vídeo saiu com o que já existia: 49 pedidos atendidos com o desenho de um pedido equivalente do cache, 10 poses atendidas com a ficha do personagem (pose neutra) e 23 cards sem equivalente tirados do `cenas.json` (o storyboard inteiro ficou em `cenas_completo.json`; a lista, em `pendente_flow.json` do vídeo). A conferência marcou "cena errada" nas poses neutras (pediu correndo, veio parado), como era de esperar.
- Defeito novo achado na revisão: com o 1º card entrando junto com a tela, na 1ª tela do tópico ele aparecia por cima do cartão do título durante os 0,35 s em que o cartão encolhe. Corrigido: a 1ª tela espera o cartão encolher.

## O cartum passou para o vídeo inteiro (2026-11-10)
Pedido de quem usa: nada de bloco a bloco; o vídeo inteiro evita retrabalho de desenhos, de storyboard e da grade.
- O que o bloco a bloco custava: cada tópico pedia os desenhos dele sem ver os outros (109 pedidos novos na 1ª versão do vídeo de 10 tópicos; 81 novos + 34 reaproveitados na 2ª), o mesmo objeto pedido com palavras um pouco diferentes virava outra geração, e a grade só ficava completa no vídeo final (`regerar_no_final`).
- Como ficou: `producao.fluxo = "video"`. Narração por capítulo; storyboard do vídeo todo numa conversa — a fase 1 é o ELENCO (personagens com ficha, poses que se repetem, objetos e ícones que voltam), a fase 2 um capítulo por resposta; a 1ª aparição de um desenho traz o pedido e as outras só `{"elenco": "<nome>"}`; uma fila só no Flow; a grade lê os títulos de todos os capítulos do mesmo projeto.
- As regras de distribuição de variações do explained ficam desligadas no cartum (a variação é só quantos desenhos a tela tem); o que o `storyboard.py --video` mede a mais é quantos desenhos o vídeo manda gerar (meta inicial: ≤ 8 por minuto).
- Teste da montagem pelo fluxo novo, com os 10 capítulos já prontos juntados num projeto só: 10 capítulos renderizados, QA aprovado nos 10, MP4 de 9 min 54 s. A montagem levou 24 min (render de 4 capítulos por vez + QA de cada um): mais lento que o vídeo final do bloco a bloco (~10 min); falta medir onde o tempo vai.

## Sexto teste (2026-11-10): o mesmo vídeo de 10 tópicos pelo fluxo do vídeo inteiro
"Every NFL Team That Disappeared", mesma narração (9 min 54 s), com o `<vídeo>/elenco/` do vídeo anterior copiado (52 desenhos e logos).
- Storyboard do vídeo todo: 514 s, aprovado na 1ª medição. O plano definiu 12 personagens e 66 nomes de elenco. 84 telas, 221 cards e 281 textos/marcações (bloco a bloco: 85 telas, 263 cards, 345): ~16% menos cards, ainda ~50 elementos novos por minuto (a referência tem ~35).
- **Desenhos a gerar: 35 no vídeo (3,5 por minuto)**, contra 109 e 81 pedidos novos nas duas versões bloco a bloco. Desses, 19 foram atendidos com um desenho equivalente que já estava no cache do Flow e 15 foram gerados: 9 + 6 em dois lotes com 15 min de pausa, ~20 s entre pedidos, nenhuma recusa (11 h depois do aviso de atividade incomum).
- Escolha de 50 assets em 180 s; montagem dos 10 capítulos + QA em 390 s, QA aprovado nos 10 de primeira; entrega em 9 s. Do fim da narração ao MP4: menos de 1 h, a maior parte esperando o ritmo do Flow.
- A grade abre cada capítulo com as 10 logos sem gerar nada de novo no final.
- O que continua aparecendo: foto ou logo real errada escolhida pela busca (a "foto" de Ralph Hay é um selo do time; o card do Chicago Bears é uma folha com seis logos de épocas diferentes), e os mapas pequenos com nomes sobrepostos.
- Falta: um elenco do CANAL (as poses do mascote e os ícones servem a todos os vídeos; hoje o reaproveitamento entre vídeos é copiar a pasta `elenco/` à mão).

## Nova comparação com as 4 referências (2026-11-10): o que estava igual e o que foi acertado
Medido com o mesmo detector nas referências e no nosso vídeo de 10 tópicos (mudança de quadro a 10 qps; áudio em janelas de 50 ms):

| Medida | Referências | Nosso antes | Nosso depois |
|---|---|---|---|
| Mudanças visuais por minuto | 32 a 35 | 39 | 41 |
| Tempo em trechos ≥ 3 s sem mudar | 21% a 28% | 19% | 10% |
| Entrada dos elementos | corte seco (1 quadro), sem efeito sonoro | igual | igual |
| Volume integrado | −17,6 e −18,9 LUFS | −29,1 LUFS | −18,0 LUFS |
| Som nas pausas da fala (p5) | −42 a −52 dBFS | −99,6 dBFS (silêncio absoluto) | −50,4 dBFS |
| Do começo do tópico ao 1º conteúdo | ~2,3 s | 6,3 s em média | 2,4 s em média |

- **Volume**: a voz sintética chega baixa (o outro canal do sistema também: −26,6 LUFS) e o YouTube não aumenta vídeo baixo. A entrega do vídeo inteiro agora sobe a narração para `voz_lufs` (−16 no `config_padrao.json`; com o teto de 3 dB de limitador deu −18,0 aqui), com um ganho só, sem comprimir.
- **Pausas**: nas referências a pausa nunca é silêncio (em duas há uma música quase inaudível, com componente estéreo e picos tonais; nas outras duas, só o ar da gravação). Sem trilha no canal, entra um ruído marrom filtrado a −50 dBFS (`formato.json › audio.ambiente_dbfs`). Com `identidade/trilha.*`, a trilha faz esse papel.
- **Abertura do tópico**: na referência a grade inteira aparece ~0,25 s, a câmera aproxima no tópico, fica ~1,75 s e o conteúdo entra com a 1ª frase ainda sendo dita. O nosso cartão de título ficava parado a 1ª frase inteira. Agora a abertura dura ~2 s (grade 0,3 s + aproximação 0,5 s + cartão 1,2 s) e a 1ª frase tem a tela dela (`storyboard.titulo_min_s = 0`; o gerador segura os cards dessa tela até o cartão virar cabeçalho).
- **Mapa**: virou desenho (`mapa.estilo = "desenho"`): silhueta verde com contorno preto, a região em vermelho, pino com o nome e o rótulo embaixo, em PNG transparente. O mapa claro com fronteiras saía pequeno, esfumado como foto e com os nomes um por cima do outro.
- O que a comparação mostrou e NÃO foi feito:
  - **Composição**: a referência não põe tudo em colunas do mesmo tamanho. Tem um desenho grande com itens pequenos se acumulando em grade ao lado, balão de pensamento com um desenho dentro, miniatura circulada ligada por uma linha a um ponto do desenho grande, aproximação num desenho grande e depois afastamento, e o personagem maior, encostado na borda de baixo.
  - **Cabeçalho**: o nome do tópico na referência é bem menor que o nosso (a olho, umas 3 vezes) e não há miniatura no canto nesse vídeo.
  - **Traço**: a referência parece desenho à mão (linha fina e torta, bonecos brancos de cabeça redonda vestidos conforme a época, cada desenho com um pedaço de cenário); o nosso parece ilustração vetorial pronta. É escolha de identidade, não defeito.

## Composição, 1ª leva (2026-11-11): lista, pensamento com desenho, número com seta e plano médio
As quatro composições entraram no gerador (`gerar.py`: `caixas(..., "L1")`, `Montador.pensamento`, `Montador.aponta`, `"plano": "meio"`) e nas regras do storyboard; nenhuma pede desenho novo.
- No vídeo de 10 tópicos, uma correção pontual por capítulo (o storyboard reescreveu de 2 a 4 cenas de cada um, só com o elenco que já existia) pôs composição nova em 36 das 75 telas: 10 listas, 19 personagens em plano médio, 11 números com seta e 4 balões de pensamento com desenho. Nenhum pedido ao Flow.
- Ajustes que o 1º render pediu: item de lista com 2 ou 3 itens saía pequeno demais numa grade de 2 colunas (agora até 3 itens ficam numa fileira só, com célula de até 520 px de altura); o número com seta ficava por cima do nome do card e do adesivo (agora o número fica colado no desenho, o nome por cima dele e o adesivo vai para o outro canto).
- Falta a 2ª leva: a miniatura circulada ligada por uma linha a um ponto do desenho grande, e a aproximação num desenho grande seguida do desenho inteiro. As duas dependem de desenhos novos (um detalhe em miniatura; um desenho grande e cheio de detalhe).

## Composição, 2ª leva (2026-11-11): miniatura circulada e aproximação
- Medido na referência: a aproximação fica ~1,5 s parada no detalhe e abre para o desenho inteiro em 3 quadros (0,12 s); é o único movimento de câmera dentro de um tópico.
- No gerador: `Montador.detalhe` (o `sticker` num círculo vermelho, com o número ao lado e uma seta curva até o ponto do desenho grande) e `"opcoes": {"zoom": {...}}` no 1º card (o desenho abre ampliado 2×, sem passar por cima do nome do tópico, e os outros cards, a data e os rótulos só entram quando ele abre).
- No vídeo de 10 tópicos: 7 aproximações e 7 miniaturas, em 7 capítulos. Em 3 capítulos (07, 08 e 10) a correção do storyboard mudou a fala de uma tela, não compilou e o capítulo ficou como estava. Cada aproximação pediu um desenho novo, grande e detalhado, em 16:9: 7 pedidos num lote só do Flow, nenhuma recusa.
- A miniatura não precisou de desenho novo: usou o elenco.

## Troca de voz com o vídeo pronto (2026-11-11): Fish Audio → Dark Planner
- Pedido: refazer o vídeo de 10 tópicos só com a voz nova. Trocou-se `canal.json › narracao` para `{"provedor": "darkplanner", "velocidade": 0.93}` e rodou-se `rodar <vídeo> --de narracao`: nenhum desenho, busca ou escolha refeitos. Na velocidade 1,0 a voz dava 166 palavras por minuto; em 0,93, 159 (as referências ficam em ~160). Os 10 capítulos levaram 22 min para gerar (um trabalho por capítulo; a conta tem limite de 50 gerações por dia). O vídeo foi de 9,9 para 10,1 min.
- A transcrição da voz nova escreve algumas palavras de outro jeito: 19 diferenças em 1.611 palavras ("Orang" → "Oaring", "Hogg's Road" → "Hoggsrod", "Air Dale" → "Airedale", "pro team" → "protein", "3rd" → "3"). O compilador não achava mais os gatilhos e as falas, e a etapa `juntar` parava. Agora o `juntar` guarda as palavras de antes (`_work/palavras_antes.json`) e, se o storyboard não compilar com a voz nova, `video.realinhar` alinha as duas transcrições capítulo a capítulo e troca no `cenas.json` só os gatilhos e as falas (27 trocas neste vídeo); o texto da tela não muda.
- Uma troca só vale se a forma antiga sumiu do capítulo. O acerto feito à mão antes disso trocou "team" por "protein" em todas as falas do capítulo; compilou (o compilador acha a fala pelo começo dela), mas deixou falas erradas no storyboard. O realinhamento automático deu os mesmos tempos de edição, com as falas certas.
- Volume: a voz do Dark Planner chega em −26,5 LUFS com picos soltos em −3,8 dBFS (só 0,01% das amostras passam de −8). O ganho parava em 5,3 dB para não pedir mais de 3 dB do limitador naquele pico, e o vídeo saía em −21,2 LUFS (a versão com Fish saía em −18; as referências, −17 a −19). O ganho passou a aceitar também o teto "pico da fala em 0 dBFS" (`render_video.pico_do_corpo`): 8 dB, −18,6 LUFS, com o limitador agindo em ~2% do tempo.

## A aproximação saía torta (2026-11-11, visto por quem usa no vídeo de 10 tópicos)
- O que estava errado, nos 7 capítulos com aproximação: o desenho ampliado era centrado no ponto pedido (`onde`) e depois empurrado para baixo do nome do tópico. Com o ponto num canto ("esquerda", "base"), um terço da tela ficava vazio e o resto do desenho saía cortado pela direita e por baixo. E, ao abrir, o desenho mais detalhado do vídeo virava uma miniatura: ~630 px de largura numa tela de 4 cards.
- Agora: ampliado, o desenho enche a tela de lado a lado (1,1× a largura dela), do cabeçalho até a borda de baixo, e nenhuma borda dele aparece no meio da tela; `onde` só escolhe o lado, dentro da folga. Depois de abrir, ele fica com 2,6 colunas (era 1,8) e, na lista, com metade da tela (era 42%): 770 a 1.020 px de largura.
- O desenho vem do Flow com ~1.100 a 1.300 px de largura e é ampliado 1,6 a 2,1×: com a interpolação linear do compositor o traço ficava mole. A camada da aproximação passou a ser ampliada com bicúbica (`"nitido"` na camada; as outras camadas e os outros formatos não mudam).
- Regra nova no storyboard: na tela da aproximação, no máximo 2 cards além do desenho grande.
- Um dos desenhos (o salão de carros) veio com a espessura da parede pintada de rosa, reflexo do fundo magenta do pedido; não é sobra do recorte (a cor é sólida, 206/150/180). Foi neutralizada à mão naquele arquivo. Se voltar a acontecer, vale tratar no recorte.

