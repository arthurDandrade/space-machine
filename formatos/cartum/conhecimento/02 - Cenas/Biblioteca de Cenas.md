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

## O que soma sem custar desenho
`acima` e `legenda` (nome, data, número), `balao` (fala do personagem), `seta` (do card anterior para este), `x` (negação), `circulo` (destaque), `textos` no estado (data abaixo do nome do tópico) e `troca` (outra pose no mesmo lugar). O `sticker` é um desenho pequeno no canto do card: custa um asset, mas ícone repetido leva `elenco` e é gerado uma vez só.

## Tamanhos
- Área dos cards: de x 70 a 1850 e de y 190 a 1040. Com `acima`, `balao` ou `sticker`, o card encolhe para caber o que vai em cima.
- Foto real: no máximo 520 px de altura, borda esfumada.
- `"opcoes": {"tamanho": "grande"}` dá uma coluna 1,5× mais larga; `"pequeno"`, 0,6×.
