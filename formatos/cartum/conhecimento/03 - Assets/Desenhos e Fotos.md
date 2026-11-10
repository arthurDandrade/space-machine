# Desenhos e fotos do cartum

## Desenho (tipo `recorte`)
- Gerado no Google Flow por uma sessão do Claude (fonte `flow_recorte`; passo a passo no `CLAUDE.md`), 3 opções por pedido, 1024×1024, em fundo MAGENTA liso. O estilo vem da ficha (`formato.json › ilustracao.estilo_recorte`): traço preto grosso e uniforme, cor chapada, sem sombra.
- O magenta é uma cor-chave: o `finalizar.tirar_fundo_liso` tira tudo o que tem a cor da borda da imagem, em qualquer lugar, e desmistura a borda para não sobrar contorno rosado. Assim somem também os vãos fechados e o branco de dentro do desenho (camisa, papel, olho) fica.
- Por que não fundo branco (2026-11-09): com branco só dá para tirar o que está ligado à borda da imagem (senão a camisa branca some junto), e o vão fechado ficava branco — o poço do 1º teste saiu com um retângulo branco entre as traves. No mesmo poço em fundo magenta, as 3 opções saíram limpas.
- O pedido não pode ter nada magenta ou rosa-choque: sumiria com o fundo.
- Um assunto por pedido, corpo inteiro, sem cenário e sem texto. Texto é do editor (`acima`, `legenda`, `balao`).
- O que volta leva `elenco` e é gerado uma vez por vídeo. Poses do mesmo personagem repetem a ficha física no pedido.
- Nunca pessoa real nem acontecimento real.

## Foto real (tipo `foto` / `historica`)
- De banco livre, pela busca de sempre. Sai pequena (até 520 px de altura) com a borda esfumada, então precisa ser reconhecível pequena: o rosto, a ruína inteira, o objeto isolado.
- Sempre com o nome em `acima`.

## Mapa
- Gerado pelo `gerar_mapa.py` (`"mapa": {...}` no card): o país com o ponto marcado.
