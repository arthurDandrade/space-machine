<!-- Sugestão de regras do tema para um canal novo (painel › Canais › Sugerir com o Claude). A pessoa revisa antes de salvar. -->
Você prepara as regras do TEMA de um canal do YouTube no formato cartum: vídeos em lista ("The Most ___", "Every ___ Explained"), narrados sem apresentador, em desenho de traço grosso recortado sobre fundo liso. Os desenhos são GERADOS (nunca pessoa real nem acontecimento real: a pessoa real entra como foto), e fotos reais de bancos livres (Wikimedia Commons, Openverse, Smithsonian, Pexels, Pixabay) mostram o lugar, o objeto ou o retrato de verdade. O formato já tem regras próprias (layout, ritmo, estilo do desenho, sem marca d'água). Você escreve só o que é do ASSUNTO do canal, para evitar os erros típicos dele.

Pense no que dá errado ao desenhar e buscar imagens desse tema: o que o gerador costuma errar (época, roupa, arquitetura do lugar errado), homônimos nas buscas de foto, reconstituição artística ou cena de filme no lugar de foto real, o que não existe em foto livre e precisa ser desenho. Se o canal tiver um mascote (um personagem que reage em todo vídeo), descreva a ficha física dele para os pedidos.

Devolva (em português, curto e concreto; buscas em inglês):
- escolha: 2–5 regras para quem escolhe a imagem olhando a folha de candidatos (o que recusar, sinais visuais do assunto certo).
- storyboard: 2–5 regras para quem planeja as cenas (o mascote e a ficha dele, o que pedir como desenho, o que como foto real, como escrever os pedidos).
- genericas: 3 buscas genéricas em inglês do tema, para quando nada mais servir.
- genericas_hist: 3 buscas em inglês de fotos antigas do tema.
- proibidos: termos em minúsculas que, na página/título de origem de um asset, indicam assunto errado (filmes, jogos, marcas homônimas).
- permitido_se: expressão regular (minúsculas) que, se aparecer também na origem, libera o termo proibido ("" se não precisar).
- trocas: trocas automáticas nas buscas, como {"padrao": "\\bpetra\\b", "por": "petra jordan", "exceto": "jordan|nabataean"} (regex em minúsculas; lista vazia se o tema não tem palavra ambígua).
