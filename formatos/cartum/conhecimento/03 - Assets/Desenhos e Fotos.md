# Desenhos e fotos do cartum

## Desenho (tipo `recorte`)
- Gerado no Google Flow por uma sessão do Claude (fonte `flow_recorte`; passo a passo no `CLAUDE.md`), 3 opções por pedido, 1024×1024, em fundo branco liso. O estilo vem da ficha (`formato.json › ilustracao.estilo_recorte`): traço preto grosso e uniforme, cor chapada, sem sombra.
- O fundo sai pelo contorno (`ilustracao.recorte = fundo_liso`): some o que tem a cor da borda da imagem E está ligado à borda. Por isso o branco de dentro do desenho (camisa, papel, olho) fica, e por isso o contorno precisa ser FECHADO: traço aberto deixa o fundo vazar para dentro. Medido em 2026-11-09 num explorador de manga branca: mais limpo que o rembg, que comeu parte do caderno branco.
- Um assunto por pedido, corpo inteiro, sem cenário e sem texto. Texto é do editor (`acima`, `legenda`, `balao`).
- O que volta leva `elenco` e é gerado uma vez por vídeo. Poses do mesmo personagem repetem a ficha física no pedido.
- Nunca pessoa real nem acontecimento real.

## Foto real (tipo `foto` / `historica`)
- De banco livre, pela busca de sempre. Sai pequena (até 520 px de altura) com a borda esfumada, então precisa ser reconhecível pequena: o rosto, a ruína inteira, o objeto isolado.
- Sempre com o nome em `acima`.

## Mapa
- Gerado pelo `gerar_mapa.py` (`"mapa": {...}` no card): o país com o ponto marcado.
