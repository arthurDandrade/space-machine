# Biblioteca de Cenas do cartum

Um estado do cenas.json é uma tela. O `gerar.py` põe os cards em colunas, da esquerda para a direita, na ordem em que estão escritos; cada um entra no seu gatilho e fica até o estado acabar.

| Código | O que mostra | Quando usar |
|---|---|---|
| P1 | um desenho grande no meio | a frase tem um assunto só e ele merece a tela (no máximo 30% dos estados) |
| P2 | dois desenhos | quem faz + o que faz; antes + depois (com `seta`) |
| P3 | três desenhos | sujeito, ação e resultado; uma enumeração de três |
| P4 | quatro a seis desenhos (5–6 em duas fileiras) | enumeração ("wells, shops, tombs and escape routes") |
| R1 | foto real + desenho(s) | a batida que apresenta a pessoa, o lugar ou o objeto de verdade |
| M1 | mapa + desenho(s) | onde fica; de onde para onde |
| L1 | lista: um desenho grande à esquerda e 2 a 6 itens pequenos em grade à direita | a frase enumera ("wells, shops, stables and chapels"); cada item entra na palavra dele, com o número em cima |

## O que soma sem custar desenho
`acima` e `legenda` (nome, data, número), `balao` (fala do personagem), `seta` (do card anterior para este), `x` (negação), `circulo` (destaque), `textos` no estado (data abaixo do nome do tópico) e `troca` (outra pose no mesmo lugar). O `sticker` é um desenho pequeno no canto do card: custa um asset, mas ícone repetido leva `elenco` e é gerado uma vez só.

## Composições que a referência usa (2026-11-11)
Medido nos vídeos de referência: as telas não são só colunas do mesmo tamanho.
- **Lista (L1)**: o desenho principal grande e os itens da frase se acumulando pequenos ao lado, com o número em cima de cada um.
- **Balão de pensamento com desenho** (`sticker` + `"opcoes": {"pensa": true}`): o que o personagem imagina, dentro da nuvem.
- **Seta com número para dentro do desenho** (`"opcoes": {"aponta": {...}}`): o número em cima e a seta curva terminando no ponto do desenho de que ele fala.
- **Plano médio** (`"opcoes": {"plano": "meio"}`): o personagem maior, cortado pela borda de baixo; um por tela.
- **Miniatura circulada** (`sticker` + `"opcoes": {"detalhe": {...}}`): um detalhe dentro de um círculo vermelho, com o número ao lado e uma seta até o ponto do desenho grande.
- **Aproximação** (`"opcoes": {"zoom": {...}}` no 1º card): a tela abre com o desenho ampliado, de lado a lado (1,1× a largura da tela, do cabeçalho para baixo), e, no gatilho, abre para o desenho inteiro em 0,12 s (na referência: ~1,5 s no detalhe e 3 quadros de passagem). Depois de abrir, o desenho fica com 2,6 colunas da tela. Pede um desenho grande e detalhado, em paisagem; no máximo 2 cards além dele.

## Tamanhos
- Área dos cards: de x 70 a 1850 e de y 190 a 1040. Com `acima`, `balao` ou `sticker`, o card encolhe para caber o que vai em cima.
- Foto real: no máximo 520 px de altura, borda esfumada.
- `"opcoes": {"tamanho": "grande"}` dá uma coluna 1,5× mais larga; `"pequeno"`, 0,6×.
