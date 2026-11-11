# Desenhos e fotos do cartum

## Desenho (tipo `recorte`)
- Gerado no Google Flow por uma sessão do Claude (fonte `flow_recorte`; passo a passo no `CLAUDE.md`), 3 opções por pedido, 1024×1024, em fundo MAGENTA liso. O estilo vem da ficha (`formato.json › ilustracao.estilo_recorte`): traço preto grosso e uniforme, cor chapada, sem sombra.
- O magenta é uma cor-chave: o `finalizar.tirar_fundo_liso` tira tudo o que tem a cor da borda da imagem, em qualquer lugar, e desmistura a borda para não sobrar contorno rosado. Assim somem também os vãos fechados e o branco de dentro do desenho (camisa, papel, olho) fica.
- Por que não fundo branco (2026-11-09): com branco só dá para tirar o que está ligado à borda da imagem (senão a camisa branca some junto), e o vão fechado ficava branco — o poço do 1º teste saiu com um retângulo branco entre as traves. No mesmo poço em fundo magenta, as 3 opções saíram limpas.
- O pedido não pode ter nada magenta ou rosa-choque: sumiria com o fundo.
- Um assunto por pedido, corpo inteiro, sem cenário e sem texto. Texto é do editor (`acima`, `legenda`, `balao`).
- **Personagem** (quem aparece em mais de uma pose): o pedido começa por `@nome{ficha física}` e depois vem só a pose. O sistema guarda a ficha em `<dados>/cache/flow/personagens/<canal>/<nome>/`, a sessão gera primeiro o boneco parado de frente, escolhe uma opção como referência e gera cada pose com ela anexada no Flow. Medido em 2026-11-09: sem a referência, as 4 telas do quarterback eram 4 bonecos diferentes; com ela, capacete, proporção, chuteira e cores se mantêm. A 1ª ficha de um nome fica valendo para o canal inteiro (o mascote é o mesmo em todos os vídeos).
- O que volta IGUAL (mesma pose) leva também `elenco` e é gerado uma vez por vídeo.
- Nunca pessoa real nem acontecimento real.

## Foto real (tipo `foto` / `historica`)
- De banco livre, pela busca de sempre. Sai pequena (até 520 px de altura) com a borda esfumada, então precisa ser reconhecível pequena: o rosto, a ruína inteira, o objeto isolado.
- Sempre com o nome em `acima`.

## Mapa
- Gerado pelo `gerar_mapa.py` (`"mapa": {...}` no card): o país com o ponto marcado.

## Ritmo das gerações no Flow (2026-11-10)
- O que aconteceu: 147 pedidos (~440 imagens) em 24 h, 108 deles seguidos, um a cada ~40 s. Passaram na hora; nove horas depois o 1º pedido de uma fila nova voltou com "Notamos uma atividade incomum".
- Regra de quem usa: maneirar, nunca a fila toda de uma vez. O sistema solta a fila em lotes de 10 com 15 min de pausa (`python -m space_machine flow --lote`) e ~20 s entre um pedido e o outro. Os números são um começo cauteloso, não um limite medido do Google: se o aviso voltar, pare e aumente a pausa.
- O que mais reduz pedidos é o storyboard do vídeo inteiro com elenco (um desenho pedido uma vez e repetido pelo nome).

