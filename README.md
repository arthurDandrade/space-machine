# Space Machine

Produz vídeos no formato **"___ Explained"** para os seus canais do YouTube. É uma lista de tópicos narrada, sem apresentador, com cards de foto e vídeo sobre um fundo de papel, textos grandes e animação de entrada e saída.

Você cola o roteiro. O Space Machine faz o resto, bloco por bloco:
1. gera a narração;
2. transcreve;
3. planeja as cenas;
4. busca as imagens e os vídeos em bancos livres e na web;
5. escolhe os assets;
6. monta e renderiza no After Effects;
7. confere a qualidade.

O Claude só entra nas decisões: planejar as cenas, escolher os assets e corrigir o que o controle de qualidade reprovar.

## O que você precisa
- **Mac** com **Adobe After Effects** (o editor).
- **Assinatura do Claude** e o **Claude Code** instalado (`npm install -g @anthropic-ai/claude-code`).
- **Homebrew** (https://brew.sh).
- Chaves grátis de **Pixabay** ou **Pexels** (vídeos e fotos livres).
- **Fish Audio** ou **ElevenLabs** para a narração — você escolhe por canal em Canal › Chaves. Também dá para gravar a sua e pôr um `narracao.mp3` em cada bloco.
- Opcionais: Smithsonian (fotos históricas, grátis) e Serper (Google Imagens, pago, usado só como último recurso).

## Instalar
```bash
git clone <este repo> SpaceMachine && cd SpaceMachine
./instalar.sh
./spacemachine
```
O instalador:
- instala ffmpeg, whisper-cpp e uv;
- cria o Python (`.venv`);
- baixa o modelo de transcrição;
- pergunta onde fica a **pasta de dados** (padrão `~/SpaceMachine-dados`);
- cria o app **Space Machine** na área de trabalho (se você quiser): clicar abre o painel e, se ele não estiver ligado, liga em segundo plano. Para refazer: `./spacemachine atalho`.

O painel abre em http://localhost:8765, na escolha de canais. No topo ficam as três áreas do painel: **Início**
(seus canais), **Modelagem** (os canais que você quer usar de modelo) e **Configurações**. Em Configurações ›
**Primeiros passos** você vê o que ainda falta e como resolver.

## Atualizar
Quando sai uma versão nova, o painel avisa no topo e em Configurações › **Atualizar**: lá você vê o que mudou e clica em
**Atualizar o Space Machine**. Ele traz o código novo do GitHub, reinstala só o que mudou, remonta o painel e reinicia
(a página recarrega sozinha). A sua pasta de dados não é tocada: canais, produções, chaves e cache ficam todos lá.
No Terminal é `./spacemachine atualizar` (ou `--conferir`, só para olhar).

Ele não atualiza por cima de trabalho seu: se tiver bloco ou fila produzindo, se você mexeu no código ou se baixou o
ZIP em vez de clonar, o painel diz o que fazer em vez de atualizar.

No After Effects, ligue: Settings › Scripting & Expressions › **Allow Scripts to Write Files and Access Network**.

## Primeiro vídeo
O painel é seu, não de um canal: ele abre na escolha de canais e, ao escolher um, entra na produção daquele canal.
1. **Novo canal** (o último card da escolha de canais, ou o botão em Configurações › Canais): nome, tema, idioma da narração, cores, fonte, logo, banner e fundo.
2. **Regras do tema** (na barra lateral do canal): clique em **Sugerir com o Claude** e revise. São as regras que evitam os erros típicos do assunto. Exemplo: num canal de futebol americano, "football" traz soccer; num canal de culinária, "turkey" traz o país.
3. **Chaves** (na barra lateral do canal): o token do Claude (`claude setup-token` no Terminal) e as chaves do canal.
4. **Novo vídeo**: cole o roteiro. Cada tópico começa com uma linha `# Nome do tópico`, e a divisão em blocos aparece enquanto você digita. O texto antes do 1º tópico vira o cold open.
5. Na página do vídeo, clique em **Produzir**. Os blocos rodam até 3 por vez e aparecem prontos em `edicao/bloco N.mp4` (uma prévia em meia resolução, para conferir; o vídeo final sai do projeto do After de cada bloco, em resolução cheia). Para um bloco só, use o **Produzir** no card dele (ou **Continuar**, se ele parou no meio).
6. Quer um Reels de um bloco? Na página dele, **Fazer Reels** monta o bloco de novo na vertical (1080×1920) e salva em `reels/bloco N.mp4`. É só para os blocos que você escolher; o resto não muda.
7. Com os blocos prontos, **Juntar no After** monta `final/final.aep` com o projeto de cada bloco em sequência (e, se marcar, renderiza o MP4 final, num render só).
8. A **thumbnail** do vídeo vai na página dele (arraste, clique ou cole com ⌘V): ela vira a capa do vídeo no painel, e o painel avisa se passar dos 2 MB do YouTube ou não for 16:9.

Os prompts que você usa no canal (o de roteiro, o de títulos…) ficam na aba **Prompts**: cada um é um `.md` em `canais/<canal>/prompts/`, com copiar em um clique, editar/visualizar e importar os `.md` que você já tem.

Desistiu de um vídeo? A lixeira na página dele manda tudo para `producoes/_lixeira/`, e dá para restaurar em Vídeos › Lixeira.

A produção gera muita coisa que só serve até o bloco ser entregue: prévias (v1, v2, v3…), os candidatos baixados para a escolha, o Auto-Save do After. Ao entregar, a prévia aprovada vira o `edicao/bloco N.mp4` (é movida, não copiada) e o resto daquele bloco vai para o Lixo do Mac. Para o que já existia, **Configurações › Limpeza** mostra quanto cada vídeo ocupa à toa e manda para o Lixo (dá para pôr de volta até você esvaziar). Assets, narração, roteiro, projeto do After, blocos entregues e o vídeo final ficam sempre.

Um bloco que precisa de você para com o motivo escrito no painel, em **Esperando você** e no sino. Exemplos: asset que não existe, limite da assinatura, After travado num diálogo. Se o motivo for o limite da assinatura, a fila espera e continua sozinha quando ele libera. ⌘K busca qualquer vídeo, bloco ou tela.

## Onde fica cada coisa
**Código** (este repo, igual para todo mundo):
- `space_machine/`: orquestrador, servidor e API do painel, e os textos do painel (`textos/pt.json`).
- `painel/`: o painel (React). O instalador monta e o `./spacemachine` remonta quando ele muda.
- `motor/busca/`: busca, escolha, download, narração, transcrição, mapas e tabelas.
- `motor/edicao_ae/`: montagem no After Effects, render e controle de qualidade.
- `formatos/<formato>/`: tudo o que é do FORMATO do vídeo — as notas, as regras do storyboard, os prompts das
  etapas, a biblioteca de cenas, o modelo do After e as medidas do QA. Vale para todos os canais daquele
  formato. Cada canal diz o seu em `canal.json` (você escolhe ao criar o canal no painel). Hoje vem com o
  `explained`; veja `formatos/LEIAME.md` para criar outro.

**Dados** (a sua pasta, fora do git):
- `space_machine.json`: modelo e esforço do Claude por etapa, o app do After e a limpeza automática ao entregar.
- `.env`: token do Claude.
- `space_machine.sqlite`: consumo e gestão.
- `cache/`.
- `canais/<canal>/`:
  - `canal.json`: formato do vídeo, quem narra, identidade e regras do tema;
  - `.env`: chaves do canal;
  - `identidade/`;
  - `conhecimento/`: Log de Aprendizados do canal;
  - `producoes/<vídeo>/blocos/NN/`.

## Linha de comando
```bash
./spacemachine                          # painel (preso ao terminal)
./spacemachine abrir                    # abre o painel; se não estiver ligado, liga em segundo plano
./spacemachine atalho                   # cria o app Space Machine na área de trabalho
./spacemachine rodar <pasta do bloco>   # um bloco do roteiro até a prévia aprovada
./spacemachine fila <pasta do vídeo>    # todos os blocos, até 3 por vez
./spacemachine final <pasta do vídeo>   # junta os blocos entregues num projeto do After (--render: e o MP4)
./spacemachine atualizar                # traz a versão nova do GitHub (--conferir: só olha; --sim: sem perguntar)
./spacemachine limpar                   # o que pode ir para o Lixo (--aplicar: manda; --cache: e o cache da busca)
./spacemachine checar                   # testa o Claude (login, versão, modelos)
./spacemachine consumo                  # tokens gastos por vídeo/bloco/etapa
```

## Regras do sistema
- **Sem YouTube.** O sistema não busca, abre nem baixa nada do YouTube: buscas automáticas lá bloqueiam o IP. Vídeo vem só de bancos livres (Pexels, Pixabay, Wikimedia Commons, Internet Archive).
- **Sem IA para gente real.** Nunca se gera com IA a imagem de uma pessoa real ou de um acontecimento real.
- **Origem registrada.** O `creditos.txt` de cada bloco registra a origem e a licença de cada asset. Confira os direitos antes de publicar.
