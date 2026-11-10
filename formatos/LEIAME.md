# Formatos de vídeo

Um **formato** é o jeito de fazer o vídeo: o que aparece na tela, como a narração vira cenas, como o
After monta e o que o QA cobra. Vale igual para todos os canais daquele formato.

Não confundir com o **tema**, que é o assunto de um canal (futebol americano, astronomia…) e fica em
`canal.json › regras`. Cada canal diz o formato dele em `canal.json › formato`; quem não tem o campo
continua no `explained`, que era o único formato até 2026-10-22.

## O que tem numa pasta de formato

Quem manda é o `formato.json`: o código genérico não conhece nenhum formato pelo nome, só lê a ficha.

```
formatos/<nome>/
  formato.json          a ficha: o nome que a pessoa vê, o resumo e onde está cada coisa
  prompts/*.md          um por etapa que chama o Claude: storyboard, escolher_imagem, escolher_video,
                        confirmar_trecho, conferir_asset, qa, regras_tema, descricao_youtube
  storyboard.md         as regras do storyboard (o storyboard.py mede as que dá)
  exemplo_cenas.json    um cenas.json pronto, só para o Claude ver a estrutura
  biblioteca_cenas.json as variações de cena, a orientação do asset de cada uma e as metas medidas
  montar_modelo2.jsx    o modelo do After: recebe o DADOS e monta a composição
  medidas_qa.json       a linha de base do QA (gerada por motor/edicao_ae/qa/linha_base.py)
  conhecimento/         as notas do formato; as que a ficha listar vão no prompt do storyboard
```

Chaves opcionais da ficha (o `bestiario` usa todas):
- `edicao.gerador`: o script Python que monta o `montar_NN_v2.jsx` (sem ele, o `motor/edicao_ae/gerar_ae2.py`, que é
  do layout do explained). Formato com gerador próprio ainda não faz Reels.
- `edicao.regerar_no_final`: true = o vídeo final roda o gerador de cada bloco de novo antes de desenhar (cartum: a grade
  de abertura mostra o símbolo de todos os tópicos, e um bloco feito cedo ainda não tinha os dos outros).
- `qa.checagens`: o que o `qa_bloco.py` confere — `render` (detector de cards sobre papel), `tela_vazia` (fundo
  escuro: tela preta > 0,5 s), `vazio_layout` (fundo desenhado: só o fundo na tela > 0,5 s, pelo layout_NN.json), `layout` (texto por cima de imagem + texto rápido), `layout_tempo` (só texto rápido),
  `origem`. Sem a lista: `render`, `layout`, `origem`.
- `busca`: por cima do `motor/busca/config.json`; `fontes_por_tipo` e `lado_menor_minimo` entram tipo a tipo (dá
  para criar tipos de asset novos, como `gravura` e `ilustracao`).
- `ilustracao`: modelo, estilo e quantidade das imagens GERADAS pelo Gemini (`motor/busca/scripts/ilustrar.py`, fonte
  `gemini` da busca). O canal pode trocar qualquer campo em `canal.json › ilustracao`.
  As fontes `flow` e `flow_recorte` fazem o mesmo pelo Google Flow, na conta de quem usa e sem chave: a busca põe o
  pedido numa fila, a etapa para, e uma sessão do Claude gera no navegador do app e guarda
  (`motor/busca/scripts/flow.py`; o passo a passo está no `CLAUDE.md`).
- `roteiro`: `medidas` (o que o agente de roteiro confere: `cold_open`, `capitulos` e `palavras` como [mín, máx]; sem ela,
  as do bestiário; o canal troca em `canal.json › roteiro › medidas`, para vídeos mais curtos ou mais longos), `capitulo_falado` (`"na_frase"` = o nome é o começo da 1ª frase do tópico e o bloco tem título, como
  no cartum; false = o capítulo não é narrado: o `gestao.criar_video` não põe a linha "Nome." e o
  bloco não tem card de título, como no bestiário) e `modelo` (o modelo de roteiro do formato, copiado para os prompts
  do canal quando ele é criado).
- Na `biblioteca_cenas.json`: `metas.max_repeticoes` (quantas vezes um tipo de cena volta no bloco; padrão 1) e
  `texto_do_layout` (tipos de cena cujo texto é parte do desenho e não conta no limite de texto sobre imagem).

A ficha do `explained` serve de exemplo. Os caminhos saem dela, então os nomes dos arquivos são seus:
o que o código exige é que a chave exista. Falta um arquivo, o erro diz qual e onde ele deveria estar.

## Para criar um formato

1. Copie `formatos/explained/` para `formatos/<nome novo>/` e mude o `nome` e o `resumo` da ficha.
2. Reescreva os prompts, o `storyboard.md` e as notas de `conhecimento/` para o seu formato.
3. Troque a `biblioteca_cenas.json` pelas cenas que ele usa e as metas que você quer medir.
4. Faça o modelo do After dele. O `gerar_ae2.py` de hoje calcula o layout do explained (cards sobre
   papel, com as animações e o zoom calibrados): um formato com outro visual provavelmente precisa do
   próprio gerador, e a ficha pode apontar para ele.
5. As medidas do QA saem dos vídeos de referência em `<dados>/referencias/<formato>/` (direito autoral:
   nunca no repo), pelo `motor/edicao_ae/qa/linha_base.py`.

O formato aparece sozinho no painel assim que a pasta tiver `formato.json`.
