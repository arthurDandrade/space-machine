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
Todo item tem `"nome"` (igual ao da linha `#` do roteiro; a narração começa por ele) e `"titulo": {"tipo": "recorte", "elenco": "<slug do tópico>", "descricao": "...", "buscas": ["..."]}`: o desenho-símbolo do tópico (o personagem dele, com `@nome{ficha}` sem pose; ou o lugar visto de fora). Quando o tópico é uma marca, um time ou uma organização que tem LOGO de verdade e o canal pede (regras do tema), o símbolo é a logo real, buscada e nunca desenhada: `"titulo": {"tipo": "logo", "elenco": "logo-<slug do tópico>", "descricao": "...", "buscas": ["<nome> <ano ou liga> logo"]}`. Ele aparece grande com o nome embaixo enquanto a 1ª frase é dita, e depois vira a miniatura do canto. É ele também que aparece na grade de abertura com todos os tópicos. O 1º estado começa na frase SEGUINTE (o título precisa de pelo menos 1 s).

## Regras (o `storyboard.py` confere as que dá para medir)
1. **Algo novo a cada 2–3 s.** Divida a narração frase a frase: cada estado dura 4 a 11 s e recebe 2 a 4 cards, mais os textos, balões, setas e X. Card com gatilho na palavra que nomeia a coisa. O 1º card de cada tela entra junto com a tela, na 1ª palavra da fala (a tela nunca fica só com o fundo: se o gatilho dele vier depois, o sistema adianta). Rótulo, legenda e balão precisam de pelo menos 1 s na tela: não ponha o gatilho deles na última palavra da fala.
2. **No máximo 30% dos estados com um desenho só (P1).** Tela com um elemento parece vazia.
3. **Pelo menos 10 assets por minuto**, cada um ≥ 1,2 s na tela.
4. **Personagem: quem aparece em mais de uma pose.** O mascote do canal e cada pessoa ou bicho do tópico que volta em outra pose têm um NOME e uma FICHA física, e o pedido do desenho começa por eles: `"buscas": ["@quarterback{an American football quarterback in a plain blue jersey, white pants and a plain white helmet with a face mask} throwing the ball overhand, side view, full body"]`. O `@nome` é curto, em minúsculas e sem espaço; a ficha entre chaves diz SÓ a aparência (roupa, cabelo, cores, o que sempre carrega), sempre a mesma; depois da chave vem SÓ a pose. O sistema desenha a ficha uma vez e gera cada pose com ela como referência: é o que mantém o mesmo rosto e o mesmo corpo. Pedido só com `@nome{ficha}`, sem pose, é o próprio personagem parado de frente (bom para o título do tópico).
4b. **Elenco para a MESMA pose que volta.** Além do `@nome`, o card que repete exatamente o mesmo desenho em outra tela leva `"elenco": "<nome>-<pose>"` ("coach-pointing", "icon-question"): a 1ª vez é gerado, depois o mesmo arquivo é reusado no vídeo inteiro. No storyboard do vídeo inteiro, a 1ª aparição traz o card completo (tipo, descricao, buscas com a ficha) e as outras só `{"gatilho": "...", "elenco": "<nome>"}`; nunca escreva o mesmo pedido de novo com outras palavras (cada texto diferente é outra geração).
5. **Desenho novo custa**: cada pedido novo é gerado à mão numa sessão. Reuse o elenco (poses do mascote e dos personagens, objetos, ícones) antes de pedir outro. O sistema conta os desenhos a gerar no vídeo: no máximo 8 por minuto de narração.
6. **Como escrever o pedido de desenho** (em inglês): UM assunto por pedido, o que é + a pose + o que segura, corpo inteiro, sem cenário ("two workers pushing a huge stone block on wooden rollers"). O estilo o sistema põe. Sem texto dentro do desenho: palavra é `acima`, `legenda` ou `balao`.
7. **Nunca desenho de pessoa real nem de acontecimento real.** Pessoa real entra como FOTO real (`historica`/`foto`) com o nome em `acima`; ao lado dela vai um desenho genérico (o mascote, "a 19th-century gentleman in a top hat"). Povo, profissão, época e bicho podem ser desenhados; rosto de alguém que existiu, não.
8. **O real é foto**: o lugar, o objeto, a ruína, o retrato. Uma ou duas fotos por tópico, na batida em que a narração apresenta a coisa. Buscas curtas em inglês. A 1ª busca é o NOME da pessoa, do time ou do lugar como num título de enciclopédia ("Ralph Hay", "Cotton Bowl (stadium)", "Chicago Cardinals logo"): a 1ª fonte é a imagem do artigo da Wikipedia com esse nome. Se não houver imagem que seja comprovadamente aquilo, o sistema tira o card da tela (melhor sem a foto do que com a errada): não conte com a foto para a tela fazer sentido, e ponha sempre um desenho junto.
9. **Gatilho = palavra como está na transcrição** (o Whisper erra: use a palavra errada no gatilho e o texto certo na tela).
10. **YouTube não é fonte** (2026-10-11). Sem vídeo: este formato é só desenho, foto e mapa.
