# Desenhos e fotos do cartum

## Desenho (tipo `recorte`)
- Gerado no Google Flow por uma sessão do Claude (fonte `flow_recorte`; passo a passo no `CLAUDE.md`), 3 opções por pedido, 1024×1024, em fundo MAGENTA liso. O estilo vem da ficha (`formato.json › ilustracao.estilo_recorte`): traço preto grosso e uniforme, cor chapada, sem sombra.
- O magenta é uma cor-chave: o `finalizar.tirar_fundo_liso` tira tudo o que tem a cor da borda da imagem, em qualquer lugar, e desmistura a borda para não sobrar contorno rosado. Assim somem também os vãos fechados e o branco de dentro do desenho (camisa, papel, olho) fica.
- Por que não fundo branco (2026-11-09): com branco só dá para tirar o que está ligado à borda da imagem (senão a camisa branca some junto), e o vão fechado ficava branco — o poço do 1º teste saiu com um retângulo branco entre as traves. No mesmo poço em fundo magenta, as 3 opções saíram limpas.
- O pedido não pode ter nada magenta ou rosa-choque: sumiria com o fundo.
- Um assunto por pedido, corpo inteiro, sem cenário e sem texto. Texto é do editor (`acima`, `legenda`, `balao`).
- **Personagem** (quem aparece em mais de uma pose): o pedido começa por `@nome{ficha física}` e depois vem só a pose. O sistema guarda a ficha em `<dados>/cache/flow/personagens/<canal>/<nome>/`, a sessão gera primeiro o boneco parado de frente, escolhe uma opção como referência e gera cada pose com ela anexada no Flow. Medido em 2026-11-09: sem a referência, as 4 telas do quarterback eram 4 bonecos diferentes; com ela, capacete, proporção, chuteira e cores se mantêm. A 1ª ficha de um nome fica valendo para o canal inteiro (o mascote é o mesmo em todos os vídeos).
- O que volta IGUAL (mesma pose) leva também `elenco` e é gerado uma vez por vídeo.
- Pessoa real e acontecimento real: foto real primeiro. Desenho só quando nenhuma foto serve, com `real:` no começo do pedido (caricatura reconhecível); nunca no lugar de uma foto que existe (regra de 2026-11-11).

## Foto real (tipo `foto` / `historica`)
- De banco livre, pela busca de sempre. Sai pequena (até 520 px de altura) com a borda esfumada, então precisa ser reconhecível pequena: o rosto, a ruína inteira, o objeto isolado.
- Sempre com o nome em `acima`.

## Mapa
- Gerado pelo `gerar_mapa.py` (`"mapa": {...}` no card): o país com o ponto marcado.

## Ritmo das gerações no Flow (2026-11-10)
- O que aconteceu: 147 pedidos (~440 imagens) em 24 h, 108 deles seguidos, um a cada ~40 s. Passaram na hora; nove horas depois o 1º pedido de uma fila nova voltou com "Notamos uma atividade incomum".
- Regra de quem usa: maneirar, nunca a fila toda de uma vez. O sistema solta a fila em lotes de 10 com 15 min de pausa (`python -m space_machine flow --lote`) e ~20 s entre um pedido e o outro. Os números são um começo cauteloso, não um limite medido do Google: se o aviso voltar, pare e aumente a pausa.
- O que mais reduz pedidos é o storyboard do vídeo inteiro com elenco (um desenho pedido uma vez e repetido pelo nome).

## Foto e logo reais: a certa ou nenhuma (2026-11-10)
- O erro: no vídeo de 10 tópicos entraram um selo de time no lugar do retrato do dono, uma montagem no lugar de uma pessoa, um passe assinado, uma figurinha e uma folha com seis logos, todos com o nome certo escrito em cima. A escolha tinha visto o problema em quase todos e anotado em "conferir", mas ficava com a menos ruim, e ninguém olhava a anotação.
- 1ª fonte: a imagem do artigo da Wikipedia de quem a busca nomeia (fonte `wikipedia`). O título do candidato é o título do artigo, então a identidade vem conferida. Artigo sem imagem, ou com imagem pequena demais, não vira candidato.
- Quem escolhe declara a identidade num campo da resposta ("certa" ou "duvida"); dúvida vira card fora. Só a regra em prosa não bastou: com "se não for claramente, pule" no prompt, 3 de 15 ainda passaram.
- Um segundo olhar independente vê a imagem escolhida com o título da fonte e reprova se não for o que o card diz (pegou uma foto de Jim Thorpe rotulada como outra pessoa, que a escolha tinha declarado "certa"). Ele não reprova pelo contexto da frase ("com o time tal"): na 1ª versão reprovou uma foto comprovada do Thorpe por não provar o uniforme.
- Quando a imagem escolhida é a do artigo da Wikipedia cujo título é o próprio assunto do card (a descrição começa por ele), a identidade vale como provada e o segundo olhar nem é chamado: ele tinha reprovado o retrato do artigo de Ernie Nevers por "não ter o nome escrito na foto". Artigo de quem só é citado na descrição (o time, no card do dono do time) não prova nada.
- Card sem imagem certa sai da tela e fica em `_estudio/sem_imagem.json`. No vídeo de teste, de 20 imagens reais, 15 ficaram certas e 5 saíram (quatro donos de time dos anos 1920 e 1950, sem retrato confiável, e a logo de um time extinto). A imagem reprovada que tinha nome de elenco sai também das outras telas que repetiam o nome, e o arquivo dela sai de `<vídeo>/elenco/` (na 1ª versão a foto reprovada voltava nas outras telas).
- Imagem real com `elenco` fica guardada em `<vídeo>/elenco/` na 1ª escolha e passa a valer para o vídeo todo: para escolher de novo é preciso tirar o arquivo de lá. E o elenco copiado de outro vídeo traz as fotos reais dele sem conferência: copie os desenhos, não as fotos.
- O que ainda depende de gente: imagem certa que o sistema tirou por falta de prova (dá para pôr à mão) e a licença das imagens da Wikipedia, que pode não ser livre.

