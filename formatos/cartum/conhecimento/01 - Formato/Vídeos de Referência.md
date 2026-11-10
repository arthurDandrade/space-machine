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
