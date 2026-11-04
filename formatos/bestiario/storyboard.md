# Regras do storyboard (formato bestiário, animação 2D)

Lidas pelo orquestrador (`rodar._sistema_storyboard`), junto com as regras do tema do canal. O `storyboard.py` mede as que dá. Medidas de referência: 5 vídeos do Depth Theory (conhecimento/01 - Formato/Canal de Referência Depth Theory.md).

## O visual em uma frase
Animação 2D vetorial: um fundo desenhado (mar, noite, grade técnica ou um cenário gerado) e, por cima, a criatura recortada nadando e oscilando, com gráficos de explicação entrando na hora da palavra. Algo novo a cada 4–6 s (10–15 por minuto). Filmagem real só para o animal/lugar/caso real (~10–20% do tempo).

## Os 10 tipos de cena no cenas.json
Todo estado pode ter `"opcoes": {"fundo": "mar"|"noite"|"grade"|"escuro"}` (sem isso, continua o fundo de antes; o primeiro é o fundo padrão do formato). Para um cenário gerado, ponha no estado um card a mais com `"tipo": "ilustracao", "opcoes": {"fundo": true}` (ex.: "dark pine forest at night, empty clearing in the middle"). Dentro de `"opcoes"`, todo objeto com `"gatilho"` entra na palavra dita.

- **C1 criatura em cena**: `"cards": [{"gatilho": "...", "tipo": "recorte", "elenco": "kraken", "descricao": ..., "buscas": [...], "opcoes": {"movimento": "nada"|"entra"|"sobe"|"close"|"parado", "lado": "esquerda"|"centro"|"direita", "espelhar": false, "voce": true, "sonar": true, "rotulo": {"texto": "Hunts by sound", "gatilho": "..."}, "carimbo": {"texto": "Predator", "gatilho": "..."}}, "legenda": ["frase-chave", "gatilho"]}]`. A base do formato. `movimento`: "nada" atravessa devagar para onde olha; "entra" chega de fora da tela; "sobe" sobe do fundo; "close" grande, cortado pela tela; "parado" só oscila. `voce` põe o "você" (o mergulhador/viajante) do outro lado; `sonar` abre ondas a partir dele. `legenda` = frase-chave em vermelho sublinhada embaixo ("IT KNOWS WHERE YOU ARE").
- **Câmera contínua (o mais importante da edição deles):** estados C1 SEGUIDOS com a MESMA criatura (mesmo `elenco`/arquivo) não trocam de imagem — a criatura fica na tela e a câmera muda de enquadramento a cada estado: `"opcoes": {"camera": "inteiro"|"medio"|"close"|"detalhe"}` no estado, ou `{"camera": {"zoom": 2.6, "ponto": [0.6, 0.45]}}` (o ponto é a fração da imagem, 0–1, que vai para o meio da tela; a cabeça fica do lado para onde ela olha). Use em sequência: plano aberto → médio → close no detalhe de que a narração fala (a cabeça, o olho, os dentes). Medido no Depth Theory: o mesmo desenho fica 10–15 s na tela com 3–4 enquadramentos.
- Mais opções do card no C1: `"movimento": "atravessa"` (cruza a tela de fora a fora, como as orcas passando), `"contraluz": true` (foco de luz atrás, a criatura ou o "você" vira silhueta), `"vulto": {"gatilho": "..."}` (a criatura enorme, escura e desfocada passa rápido na frente da câmera), `"so_vulto": true` (só o vulto, a criatura ainda não aparece), `"marcadores": [{"texto": "Sharks: rare", "gatilho": "...", "icone": "check"|"x"}]` (rótulos com ✓/✗ empilhados no canto de baixo à esquerda), `"nome": {"texto": "Kraken", "gatilho": "..."}` (o nome em maiúsculas brancas embaixo, quando ela é apresentada), `"circulo": {"ponto": [0.58, 0.47], "raio": 60, "gatilho": "..."}` (círculo tracejado em volta do detalhe de que a narração fala; o ponto é a fração da imagem). R1 (filmagem real) enche a tela; `"moldura": true` vira foto impressa. O "você" sozinho em cena é um card `{"arquivo": "../../../../identidade/personagem.png"}`.
- **E1 escala**: a criatura inteira de lado + régua que se desenha embaixo + o tamanho: `"rotulos": [["~40 M", "forty"], ["= 6 city buses", "buses"]]` (o 2º em vermelho). `"escala": {"tamanho_m": 40}` no card põe uma pessoa de 1,8 m na proporção.
- **N1 comparação em ícones**: card `"tipo": "recorte"` com o ÍCONE (um elefante, um barco, um homem) e `"opcoes": {"quantidade": 6.5}` no estado: os ícones entram um a um (o último pela metade). `"textos": [["= 40 tonnes", "..."]]` (vermelho, em cima) e `"rotulos": [["6–7 elephants", "..."]]` (embaixo).
- **N2 número grande**: `"textos": [["236 dB", "236"]]`, `"rotulos": [["measured underwater", "..."]]`, e opcional `"opcoes": {"barra": 0.95, "titulo": {"texto": "Loudest animal on Earth", "gatilho": "..."}}`.
- **L1 suas opções**: `"opcoes": {"titulo": {"texto": "Your options", "gatilho": "..."}, "itens": [{"texto": "Swim away", "gatilho": "swim"}, ...], "riscar": [{"item": 1, "gatilho": "..."}], "veredito": {"texto": "...", "gatilho": "..."}}`. O "what would you actually do?": cada item entra quando é dito e é riscado quando a narração derruba.
- **D1 documento**: papel claro um pouco torto com `"opcoes": {"fonte": {"texto": "Olaus Magnus · 1555", "gatilho": ...}, "titulo": {"texto": "A History of the Northern Peoples", "gatilho": ...}}` e, opcional, um card `"tipo": "gravura"` (a gravura antiga dentro do papel). Para fonte antiga, artigo científico, relato registrado.
- **T1 linha do tempo**: `"opcoes": {"titulo": {...}, "pontos": [{"rotulo": "1555", "texto": "Olaus Magnus", "gatilho": "..."}, {"rotulo": "1752", "texto": "Pontoppidan", "gatilho": "...", "destaque": true}]}`. 2–4 pontos.
- **R1 filmagem real**: card `"tipo": "video"|"foto"|"historica"`; enche a tela, como no Depth Theory; `"opcoes": {"moldura": true}` vira uma foto impressa torta (para foto antiga, documento). `"legenda": [...]` vira um rótulo embaixo.
- **F1 frase**: `"textos": [["If it decided you were a problem…", "If"]]`; `["texto", "gatilho", "vermelho"]` = vermelha sublinhada ("WHAT DOES IT EAT?"). 2–8 palavras.
- **S1 lado a lado**: dois cards com `"acima": ["Legend", "gatilho"]` / `"acima": ["Reality", "gatilho"]` (ou "You" × "Kraken").
- Título do capítulo: `"titulo": {"tipo": "recorte", "elenco": "kraken", "descricao": ..., "buscas": [...]}`: o nome grande à esquerda e a criatura do elenco nadando à direita. Cold open: `"sem_titulo": true`.

## Do roteiro às cenas
O roteiro é uma história contínua (conhecimento/01 - Formato/Estrutura do Roteiro.md); cada bloco é um capítulo SEM nome falado (o editor põe o marcador de capítulo na tela sozinho). Cada batida do molde tem a sua cena:
| Batida do roteiro | Cena |
|---|---|
| "Picture this. You're…" (cold open) | C1 do "você" (contraluz, câmera fechando) + marcadores ✓ da crença ("Sharks: rare ✓") |
| "Then you feel it." / a quebra | vulto passando (`so_vulto`) ou F1 vermelha |
| "So let's talk about why you'd never want to meet one." | C1 da criatura chegando + `nome` |
| A pergunta-gancho do capítulo ("Which raises an obvious question. What does it eat?") | F1 vermelha com a pergunta |
| "First, the size." + comparação | E1 (régua) e/ou N1 (ícones) — a criatura fica, os gráficos somam |
| Anatomia, poderes, sentidos | C1 em câmera contínua: inteiro → médio → close/detalhe no que é dito, com `circulo`, `rotulo`, `carimbo` |
| Fonte antiga, artigo, relato com data | D1 (com a gravura) ou T1 (vários anos) |
| Número que choca | N2 |
| "What would you actually do? … You could…" | L1 com os itens riscados e o veredito |
| A virada (o animal real, a explicação) | S1 lenda × realidade, R1 filmagem real em tela cheia |
| Fecho que volta à abertura | o mesmo C1 do cold open (o mesmo "você", o mesmo lugar) |

## Regras (o `storyboard.py` confere as que dá para medir)
1. **Algo novo a cada 4–6 s**: troque de cena quando a ideia muda; gráfico (L1, N2, T1, F1, D1) e câmera nova na mesma criatura contam como mudança. Prefira mover a câmera a trocar de imagem enquanto a narração fala da mesma criatura.
2. **≥ 5 tipos de cena por bloco**, cada um no máximo 4 vezes. C1 é a base; todo número que importa vira E1/N1/N2; toda fonte antiga vira D1 ou T1; o "what would you do" é L1.
3. **Frase solta (F1) até 15% do tempo.** O texto vive dentro dos gráficos e nos rótulos (2–6 palavras, no idioma da narração, curto; buscas e pedidos de imagem em inglês).
4. **Cada asset ≥ 1,8 s na tela.**
5. **A MESMA criatura em todo o vídeo: o elenco.** Todo card da criatura principal leva `"elenco": "kraken"` (o mesmo nome em todos os blocos): a 1ª vez ela é gerada e escolhida, e dali em diante o sistema usa o MESMO arquivo, sem gerar de novo — então escreva a ficha completa (descrição, buscas) em todo card com elenco, porque você não sabe qual bloco roda primeiro. Pose diferente (de frente, boca aberta, close do olho) é outro nome de elenco ("kraken-boca-aberta"), com a mesma ficha da criatura no pedido. O "você" e os ícones repetidos (elefante, barco) também podem ser elenco.
6. **Recorte é gerado** (criatura, ícone, objeto): pedido em inglês com "side view facing right" (o editor espelha quando ela nada para a esquerda), corpo inteiro, nada em volta. Máx. 6 pedidos novos por bloco (cada um gera 3 opções pagas).
7. **Nunca imagem gerada de pessoa real ou de acontecimento real.** Pessoa real, retrato antigo, navio com nome: gravura ou foto histórica (R1/D1). O "você" e pessoas genéricas sem rosto podem.
8. **O real é foto/vídeo (R1)**: o animal que inspirou a lenda, o lugar, o fóssil, o objeto de museu. Vídeo só do que existe aos montes em banco livre.
9. **Gatilho = palavra como está na transcrição** (o Whisper erra: use a palavra errada no gatilho e o texto certo na tela).
10. **YouTube não é fonte** (2026-10-11). Franquia nenhuma (Harry Potter, Witcher, D&D...): só folclore, fontes antigas e ciência.
