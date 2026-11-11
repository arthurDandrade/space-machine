# Modelos de thumbnail do cartum

Desde 2026-11-11 o sistema faz a thumbnail: na página do vídeo (aba Publicação) você escolhe um modelo e ele monta. Os modelos ficam em `formatos/cartum/thumbs/modelos.json`; quem decide o que entra é o Claude (`prompts/thumbnail.md`); quem desenha é o `motor/thumb/compor_thumb.py`; quem junta tudo é o `space_machine/thumb.py`.

## O que foi medido na referência (2026-11-11)
25 thumbs de um canal do mesmo tipo de vídeo (lista de tópicos de futebol; 11,7 mil inscritos, vídeos de até 1,6 milhão de views), vistas pela API oficial do YouTube (3 unidades de cota: o canal, a lista de envios e os números dos vídeos; só as imagens que a resposta aponta, guardadas em `<dados>/referencias/cartum/thumbs/`).

- Todas sobre branco, sem rosto de apresentador e sem o título do vídeo. A thumbnail mostra OS ITENS da lista, cada um com 1 a 3 palavras em maiúsculas embaixo, numa letra de quadrinho.
- As mais vistas são as grades de fotos reais, 3 × 2 ou 4 × 2, com borda preta: 1,61 M, 1,01 M, 976 mil, 433 mil e 390 mil views.
- Grade de círculos com um desenho em cada (céu e grama atrás): 1,52 M, 235 mil, 59 mil, 43 mil.
- Grade de logos reais com uma palavra forte embaixo ("FASCIST", "ANTIFA"): 197 mil e 122 mil.
- Dois desenhos grandes com um título em cima de cada (preto e vermelho): 821 mil, 757 mil, 328 mil, 294 mil, 180 mil, 46 mil, 32 mil.
- Título numa faixa e uma foto cheia: 1,36 M (um vídeo só).
- As legendas dão o fato mais estranho do item sem contar o final ("KICKED TO DEATH", "FAKE SPONSOR"), ou o sobrenome quando a pessoa é conhecida.

## Os modelos
| id | o que é | o que entra |
|---|---|---|
| `grade_fotos` | 6 fotos reais, 3 × 2, borda preta | foto, histórica |
| `grade_fotos_8` | 8 fotos reais, 4 × 2 | foto, histórica |
| `grade_logos` | 8 logos reais, 4 × 2, sem quadro | logo |
| `grade_circulos` | 8 círculos com desenho (céu e grama) ou foto | recorte, foto, histórica |
| `dupla` | 2 desenhos grandes, título em cima de cada | recorte, logo |
| `faixa_foto` | título numa faixa + 1 foto cheia | foto, histórica |

Medidas do desenho (1280 × 720): margem de 12 px; legenda em Chalkboard SE Bold, 34 px com 3 colunas e 30 px com 4; borda de 3 px no quadro e 4 px no círculo; título em Impact, com o que vai entre asteriscos em vermelho (#E3120B). Desenhado no dobro e reduzido. PNG; acima de 2 MB (o limite do YouTube) sai JPG.

## O que é diferente da referência, de propósito
A referência usa caricaturas de jogadores reais nos círculos e nas duplas. O sistema NUNCA gera desenho de pessoa real: pessoa real entra por foto real, e o desenho é genérico (o objeto ou o símbolo do caso, um jogador genérico com o uniforme da época). Vale no prompt do plano e no estilo do pedido ao Flow.

## De onde vêm as imagens
1. Do que o vídeo já tem: o elenco (desenhos, logos e fotos de `<vídeo>/elenco/`) e os assets escolhidos na produção. O tipo de cada imagem do elenco vem do `cenas.json` (o arquivo não diz se é logo, foto ou desenho).
2. O que falta passa pela mesma busca e pela mesma escolha da produção, numa pasta `<vídeo>/thumb/<modelo>/` com a cara da de um bloco: foto e logo reais nas fontes do formato, com a regra de imagem certa ou nenhuma; desenho, na fila do Google Flow.
3. O plano pede 2 ou 3 itens de reserva: se uma imagem não for achada, a grade fecha com o seguinte.

## Teste no vídeo de 10 tópicos (2026-11-11)
- `grade_logos`, `grade_circulos`, `dupla`, `faixa_foto`: 4 a 8 s cada, só com o que o vídeo já tinha.
- `grade_fotos`: 1 min 34 s; 5 fotos do vídeo e 1 buscada (o time de 1925 do Pottsville).
- `grade_circulos` com um desenho novo pedido na observação (um troféu rachado): parou em "esperando o Flow" com 1 pedido; gerado no Flow, continuou e fechou em 9 s.
- Ajustes que o teste pediu: foto de corpo inteiro sem rosto achado era cortada pelo meio e decapitava (agora o corte fica perto do topo); retrato fechado cortava o cabelo (o detector marca das sobrancelhas ao queixo); pedido de desenho só com a descrição era descartado.
- A observação de quem produz muda o plano ("use só desenhos", "um dos círculos tem que ser...").
