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
