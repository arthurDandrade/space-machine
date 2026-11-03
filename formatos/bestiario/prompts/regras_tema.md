<!-- Sugestão de regras do tema para um canal novo (painel › Canais › Sugerir com o Claude). A pessoa revisa antes de salvar. -->
Você prepara as regras do TEMA de um canal do YouTube no formato bestiário: vídeos narrados em segunda pessoa, sem apresentador, um assunto por vídeo, com gravuras antigas do Wikimedia Commons, ilustrações GERADAS em traço claro sobre preto (nunca de pessoa real ou acontecimento real) e fotos/vídeos reais de bancos livres (Pexels, Pixabay, Wikimedia Commons, Internet Archive) em preto e branco. O formato já tem regras próprias (layout, ritmo, estilo das ilustrações, sem marca d'água). Você escreve só o que é do ASSUNTO do canal, para evitar os erros típicos dele.

Pense no que dá errado ao buscar e escolher imagens desse tema: franquias que usam as mesmas criaturas (filmes, jogos, livros com dono: Harry Potter, Witcher, Dungeons & Dragons, Pokémon, Marvel), arte digital moderna no lugar de gravura antiga, homônimos (Hydra = animal e empresa; Kraken = time e cerveja), o que quase nunca existe em vídeo livre e precisa ser ilustração.

Devolva (em português, curto e concreto; buscas em inglês):
- escolha: 2–5 regras para quem escolhe a imagem/vídeo olhando a folha de candidatos (o que recusar, sinais visuais do assunto certo).
- storyboard: 2–5 regras para quem planeja as cenas (o que pedir como gravura, o que como ilustração, como escrever as buscas).
- genericas: 3 buscas genéricas em inglês do tema, para quando nada mais servir (gravuras antigas genéricas: "sea monster engraving", "medieval bestiary illustration").
- genericas_hist: 3 buscas em inglês de gravuras/fotos antigas do tema.
- proibidos: termos em minúsculas que, na página/título de origem de um asset, indicam assunto errado (franquias, marcas homônimas).
- permitido_se: expressão regular (minúsculas) que, se aparecer também na origem, libera o termo proibido ("" se não precisar).
- trocas: trocas automáticas nas buscas, como {"padrao": "\\bkraken\\b", "por": "kraken sea monster", "exceto": "monster|engraving|woodcut|squid"} (regex em minúsculas; lista vazia se o tema não tem palavra ambígua).
