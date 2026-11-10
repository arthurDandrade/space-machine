# Regras do storyboard (formato cartum)

Lidas pelo orquestrador (`rodar._sistema_storyboard`), junto com as regras do tema do canal. O `storyboard.py` mede as que dá. Medidas de referência: conhecimento/01 - Formato/Vídeos de Referência.md.

## O visual em uma frase
Fundo azul-claro liso. No topo, o nome do tópico (e a miniatura dele no canto direito). No meio, DESENHOS de traço grosso recortados, que entram um a um na palavra dita, em corte seco, e vão se acumulando; quando a ideia muda, a tela limpa e começa outra. Foto real só para mostrar a pessoa ou o lugar de verdade, pequena, com o nome em cima.

## Como o cenas.json vira tela
- **Um estado = uma tela.** Os `cards` do estado são os elementos, da ESQUERDA para a DIREITA na ordem em que você escreve. Cada card entra no `gatilho` dele e fica até o estado acabar.
- 1 a 4 cards ficam numa fileira; 5 e 6, em duas fileiras de três. O primeiro card é o principal (o personagem, o lugar); os seguintes são o que a frase vai trazendo.
- `layout` diz o que a tela mostra: **P1** um desenho · **P2** dois · **P3** três · **P4** quatro a seis · **R1** foto real + desenho(s) · **M1** mapa + desenho(s).
- Card de DESENHO: `{"gatilho": "...", "tipo": "recorte", "descricao": "...", "buscas": ["pedido do desenho em inglês"]}`.
- Card de FOTO REAL: `{"gatilho": "...", "tipo": "foto" | "historica", "descricao": "...", "buscas": ["..."], "acima": ["Nome", "gatilho"]}`. Sai pequena, com a borda esfumada.
- Card de MAPA: `{"gatilho": "...", "mapa": {"pais": ["Turkey"], "pontos": ["Derinkuyu:38.37:34.73"], "rotulo": "Turkey"}}` (gerado pelo sistema; ver o topo do compilar_cenas.py).

## O que cada card pode levar (é daqui que vem o ritmo)
Nada disto é asset: não custa geração. Use em quase todo estado.
- `"acima": ["Arthur Posnansky", "gatilho"]`: nome, data ou número em cima do card. `"legenda": ["85 meters deep", "gatilho"]`: embaixo.
- `"sticker": {"gatilho": "...", "tipo": "recorte", "descricao": "...", "buscas": ["a big question mark icon"]}`: um desenho pequeno no canto de cima do card (ícone, ponto de interrogação, relógio, caveira). Este É um asset.
- `"opcoes": {"balao": {"texto": "They built this!", "gatilho": "..."}}`: balão de fala do personagem (até 6 palavras, no idioma da narração).
- `"opcoes": {"x": {"gatilho": "..."}}`: X vermelho por cima do card ("mas não foi isso", "foi proibido").
- `"opcoes": {"seta": {"gatilho": "..."}}`: seta vermelha do card ANTERIOR para este ("virou", "levou a", "foi para").
- `"opcoes": {"circulo": {"gatilho": "..."}}`: círculo vermelho em volta do card ("repare nisto").
- `"opcoes": {"tamanho": "grande" | "pequeno"}`: a coluna do card mais larga ou mais estreita.
- No estado, `"textos": [["15,000 BC", "gatilho"]]`: data ou número logo abaixo do nome do tópico, no topo.
- `"troca": [{"gatilho": "...", "tipo": "recorte", ...}]` num card: o desenho troca por outro no mesmo lugar (a mesma pessoa em outra pose).

## Título do tópico
Todo item tem `"nome"` (igual ao da linha `#` do roteiro; a narração começa por ele) e `"titulo": {"tipo": "recorte", "elenco": "<slug do tópico>", "descricao": "...", "buscas": ["..."]}`: o desenho-símbolo do tópico (o busto do personagem, o lugar visto de fora). Ele aparece grande com o nome embaixo enquanto a 1ª frase é dita, e depois vira a miniatura do canto. O 1º estado começa na frase SEGUINTE (o título precisa de pelo menos 1 s).

## Regras (o `storyboard.py` confere as que dá para medir)
1. **Algo novo a cada 2–3 s.** Divida a narração frase a frase: cada estado dura 4 a 11 s e recebe 2 a 4 cards, mais os textos, balões, setas e X. Card com gatilho na palavra que nomeia a coisa.
2. **No máximo 30% dos estados com um desenho só (P1).** Tela com um elemento parece vazia.
3. **Pelo menos 10 assets por minuto**, cada um ≥ 1,2 s na tela.
4. **Elenco para tudo o que volta.** O mascote do canal e cada personagem do tópico levam `"elenco": "<nome>-<pose>"` ("explorer-thinking", "explorer-pointing", "builders-carrying-stone"): a 1ª vez é gerado, e depois o mesmo arquivo é reusado no vídeo inteiro sem gerar de novo. Poses diferentes da mesma pessoa repetem a MESMA descrição física no pedido (roupa, cabelo, cores), só mudando a pose. Escreva a ficha completa em todo card com elenco.
5. **Desenho novo custa**: cada pedido novo é gerado à mão numa sessão. Reuse o elenco e os ícones (`"reusar": "<id>"` dentro do bloco) antes de pedir outro. Máx. 14 pedidos novos por tópico.
6. **Como escrever o pedido de desenho** (em inglês): UM assunto por pedido, o que é + a pose + o que segura, corpo inteiro, sem cenário ("two workers pushing a huge stone block on wooden rollers"). O estilo o sistema põe. Sem texto dentro do desenho: palavra é `acima`, `legenda` ou `balao`.
7. **Nunca desenho de pessoa real nem de acontecimento real.** Pessoa real entra como FOTO real (`historica`/`foto`) com o nome em `acima`; ao lado dela vai um desenho genérico (o mascote, "a 19th-century gentleman in a top hat"). Povo, profissão, época e bicho podem ser desenhados; rosto de alguém que existiu, não.
8. **O real é foto**: o lugar, o objeto, a ruína, o retrato. Uma ou duas fotos por tópico, na batida em que a narração apresenta a coisa. Buscas curtas em inglês.
9. **Gatilho = palavra como está na transcrição** (o Whisper erra: use a palavra errada no gatilho e o texto certo na tela).
10. **YouTube não é fonte** (2026-10-11). Sem vídeo: este formato é só desenho, foto e mapa.
