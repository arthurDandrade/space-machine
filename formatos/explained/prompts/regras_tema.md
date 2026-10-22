<!-- Sugestão de regras do tema para um canal novo (painel › Canais › Sugerir com o Claude). A pessoa revisa antes de salvar. -->
Você prepara as regras do TEMA de um canal do YouTube no formato "___ Explained": vídeos narrados, sem apresentador, feitos de cards com fotos e vídeos curtos de bancos livres (Pexels, Pixabay, Wikimedia Commons, Internet Archive) e fotos da web. O formato já tem regras próprias (layout, ritmo, qualidade da imagem, sem marca d'água). Você escreve só o que é do ASSUNTO do canal, para evitar os erros típicos dele.

Pense no que dá errado ao buscar e escolher imagens desse tema: assuntos vizinhos que aparecem nas buscas e não servem (ex.: num canal de futebol americano, "football" traz soccer), homônimos, épocas misturadas, o que quase nunca existe em vídeo livre e precisa ser foto.

Devolva (em português, curto e concreto; buscas em inglês):
- escolha: 2–5 regras para quem escolhe a imagem/vídeo olhando a folha de candidatos (o que recusar, sinais visuais do assunto certo).
- storyboard: 2–5 regras para quem planeja as cenas (o que pedir como foto em vez de vídeo, como escrever as buscas).
- genericas: 3 buscas genéricas em inglês do tema, para quando nada mais servir.
- genericas_hist: 3 buscas em inglês de fotos antigas do tema (lista vazia se o tema não tem história visual).
- proibidos: termos em minúsculas que, na página/título de origem de um asset, indicam assunto vizinho errado (lista vazia se não houver um vizinho claro).
- permitido_se: expressão regular (minúsculas) que, se aparecer também na origem, libera o termo proibido ("" se não precisar).
- trocas: trocas automáticas nas buscas, como {"padrao": "\\bfootball\\b", "por": "american football", "exceto": "american|\\bnfl\\b|soccer"} (regex em minúsculas; lista vazia se o tema não tem palavra ambígua).
