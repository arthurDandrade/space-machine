---
tags: [space-machine, sistema, orquestrador, tokens]
criado: 2026-10-11
pasta: SpaceMachine/space_machine/
---

# Space Machine: o orquestrador (ex-Estúdio)

> [!info] Desde 2026-10-13 o Estúdio e o ProFootball viraram um produto só, o **Space Machine** (ver `README.md` e `CLAUDE.md` na raiz do repo). Esta nota é o histórico das decisões do orquestrador: "Estúdio" = `space_machine/`, `<dados>/.env` = `<dados>/.env`, `estudio.json` = `<dados>/space_machine.json`, `canais.json` = pastas `<dados>/canais/*/`.

> [!danger] YouTube REMOVIDO do sistema (2026-10-11)
> As buscas automáticas fizeram o Google bloquear o IP do Arthur e acusá-lo de fraude/proxy. Nenhum script busca, abre ou baixa nada do YouTube (yt-dlp e plugin de PO token desinstalados; `yt_seguro.py` virou uma trava que sempre recusa; `achar_lance.py` desativado). Vídeo só de bancos livres: Pexels, Pixabay, Wikimedia Commons, Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies). Backup: `ProFootball_backups/antes_remover_youtube_2026-10-11.tar.gz` e `youtube_removido_2026-10-11/`.

Voltar: [[00 - Pro Football (Índice)]] · Log: [[Log de Aprendizados]]

O Estúdio é um sistema próprio, que roda o pipeline sozinho e chama o Claude **só nas decisões**. Cada decisão é uma chamada isolada e curta (`claude -p`, pela assinatura). Ele serve para vários canais (`canais.json`); por enquanto só o Pro Football está ativo. Plano completo: `~/.claude/plans/sim-mas-planeje-tudo-splendid-eclipse.md`.

## Por quê
Dentro de uma conversa do Claude Code, cada saída de script e cada folha de contato fica no histórico, e o histórico é relido a cada passo. Medido em 2026-10-10 (`python -m space_machine medir`): o subagente `escolher-assets` gastou **~47 mil tokens equivalentes por asset** (~720 mil por bloco; 27 execuções, 413 assets).

## Como a chamada é enxuta
O código fica em `space_machine/motor_claude.py`.
- Sem MCP, sem CLAUDE.md, sem memória e sem o system prompt padrão. Só vai o prompt curto da etapa (`space_machine/prompts/*.md`).
- A imagem vai em base64 direto na mensagem, sem um turno extra de Read.
- A resposta volta em JSON validado (`--json-schema`).
- **`--effort low` e `MAX_THINKING_TOKENS=0` nas escolhas.** Sem isso, o Sonnet "pensava" de 1,5 a 8,7 mil tokens de saída por resposta (a saída pesa 5×) e o gasto ficava em ~40 mil por asset, quase igual ao do subagente.
- Cada chamada registra tokens e custo em `<dados>/space_machine.sqlite`; o resumo sai com `python -m space_machine consumo`.
- Se a assinatura bater no limite de uso, a rodada para e baixa o que já foi escolhido.
- Login: token da assinatura (`claude setup-token`) gravado em `<dados>/.env` como `CLAUDE_CODE_OAUTH_TOKEN=...`.

## Escolha de assets (Fase 1, pronta)
`python -m space_machine escolher <bloco>` (de dentro do repo, com `.venv/bin/python`).
- **Imagem:** uma chamada com a `folha.jpg` + o pedido + a lista dos candidatos → `{n, recortar, conferir}`.
- **Vídeo:**
  - Uma chamada com as `v*_folha.jpg` → `{n, inicio, detalhar?}`.
  - Se pedir detalhe, roda `detalhar_video.py` e faz uma segunda chamada com a folha de 0,5 s.
  - Card com `"lance"`: escolhe só em banco livre e marca "conferir" (o `achar_lance.py` saiu junto com o YouTube); sem vídeo, vira foto (`foto_no_lugar`).
  - O Python garante que `inicio + duração` cabe no vídeo.
- **Nada serve:** `{nova_busca: [...]}`, então roda `buscar.py --refazer` e pergunta de novo (até 2 vezes).
- **Grava o `escolhas.json`** no formato de sempre e roda `finalizar.py` **só com os `--asset` novos**. Sem `--asset`, o `finalizar.py` baixa tudo de novo.
- **Conferência:**
  - Tarja preta: o `ffmpeg cropdetect` acha e corta (com `setsar=1`), sem Claude.
  - Texto por cima ou cena errada: o Haiku olha 2 quadros e, se reprovar, o asset é trocado automaticamente.
- **Modo sombra** (`--sombra`): refaz as escolhas de um bloco pronto em `escolhas_estudio.json`, sem baixar nada. Gera `_estudio/sombra.md` e `_estudio/sombra_divergencias.jpg`.
- O subagente `escolher-assets` continua como plano B.

## Resultado do modo sombra (2026-10-10, "Who Makes the NFL Possible", 14 blocos, 186 assets)
- **~7.500 tokens equivalentes por asset**, contra 47 mil do subagente (cerca de 6× menos). Imagem: ~3.700. Vídeo: ~8.400.
- Concordância com o subagente: 12–45% por bloco. Isso **não mede qualidade**. O Arthur olhou as folhas de divergência e concluiu: "apesar de não terem escolhido os mesmos assets, a qualidade não caiu". Muitas diferenças são o mesmo vídeo em outro momento ou uma alternativa igualmente boa. Os "pulados" do sombra acontecem porque ele não faz busca nova.
- Erro visto: no 01-09-a, o Estúdio escolheu um homem falando para a câmera em vez da tela pedida. Se isso se repetir, testar `esforco` `medium` só para `escolher_video` (em `estudio.json`).

## Versionamento (2026-10-13)
O Space Machine é um repositório git local (antes: `Estudio/` e `ProFootball/`). Mudança no código = commit (nada de `_backup_*`). Revisão de 2026-10-13 e o que ela corrigiu: [[Log de Aprendizados]].

## Regra de manutenção
Os prompts em `space_machine/prompts/` são **resumos** de [[Critérios de Escolha]] e da skill `buscar-assets`. Quando uma regra de escolha nova entrar no [[Log de Aprendizados]], o prompt correspondente também precisa ser atualizado.

## Orquestrador (Fase 2, pronta)
`python -m space_machine rodar <bloco> [--de etapa] [--ate etapa] [--obs "..."]`: narração → transcrição → storyboard → busca → escolha → edição + QA → entrega (`edicao/bloco N.mp4`).
- Cada etapa pula o que já está feito. Se precisar de você, o bloco **para com o motivo** em `<bloco>/_estudio/estado.json`, e os logs ficam em `_estudio/log_<etapa>.txt`.
- **Storyboard:** uma sessão `claude -p` com o prompt de sistema montado na hora (regras do agente storyboard + Biblioteca + Da Narração + topo do Log + um exemplo). O Python compila e mede, e devolve os avisos ao Claude (até 4 voltas). Nas correções, o Claude devolve só as cenas que mudaram.
- **Nome do tópico:** vem sempre do roteiro. Se o Whisper escreveu diferente ("Lambo Field"), a forma transcrita vai em `"nome_fala"` (campo novo do `compilar_cenas.py`).
- **Vídeo que não existe em banco livre:** vira foto automaticamente (`buscar.py --tipo foto`), marcado "foto no lugar do vídeo" para conferir.
- **Escolha repetida:** quando o mesmo arquivo cai em dois cards, o segundo é refeito.
- **After:** uma trava (`dados/trava_after`) garante um bloco por vez.
- **QA reprovado:** uma correção automática do `cenas.json`; se reprovar de novo, para.

## Painel (Fase 3, pronto)
`python -m space_machine painel` → http://localhost:8765. Também dá para abrir pelo painel de prévia do Claude Code, com o nome "estudio" no `.claude/launch.json`.
- **Canais:** os vídeos de cada canal, com o progresso.
- **Vídeo:** kanban dos blocos por etapa (atualiza a cada 5 s).
- **Bloco:** Rodar (de/até/observação) e Parar, etapas, log ao vivo, prévia, QA, o que conferir e a revisão dos assets.
- **Consumo:** tokens por etapa e por bloco.
- **Novo vídeo:** colar o roteiro com `# Tópico` em cada bloco.

## Custos medidos (bloco 02 do Every NFL Stadium, 2026-10-11)
- Storyboard: ~426 mil tokens equivalentes, 315 mil só na 1ª volta (55 mil de saída, quase tudo raciocínio: `MAX_THINKING_TOKENS` não limita esse modelo). Passou a usar `--effort low`; medir no próximo bloco.
- Conferência pós-download: era ~6.700 tokens por asset, inclusive em foto copiada sem mudança. Agora confere só vídeo e recorte.
- Escolha de imagem: ~4 mil por asset. Escolha de vídeo: ~4,6 mil.

## Gestão e configuração (Fase 4, pronta em 2026-10-11)
- **Produção** (`/canal/<canal>/producao`): kanban do canal com as colunas Ideias → Roteiro → Produção → Edição final → Agendado → Publicado. Roteiro e Produção andam sozinhos pelos blocos; as outras você marca no formulário "Publicação" do vídeo. Uma ideia pode "virar vídeo", que abre o formulário de vídeo novo já com o título.
- **Calendário** (`/canal/<canal>/calendario`): mês com os vídeos na data de publicação.
- **Publicação**, na página de cada vídeo: título no YouTube, descrição, tags, data, status, link e notas (guardados em `<dados>/space_machine.sqlite`). **Sem upload pelo sistema** (decisão do Arthur): ele sobe no YouTube Studio e cola o link.
- **Canais** (`/config/canais`):
  - nome e ativo;
  - identidade (5 cores + fonte), gravada no `canal.json` da raiz do canal;
  - "Novo canal": copia o motor do Pro Football para `/Users/arthur/Canais/<Nome>`, sem produções, cache, backups nem chaves, e cria a pasta de conhecimento com as notas do formato. Testado com um canal descartável, depois apagado.
- **Identidade por canal:** desde 2026-10-11, `gerar_ae2.py`, `gerar_mapa.py` e `gerar_tabela.py` leem cores, fonte e fundo do `canal.json` (backups `_backup_*_antes_canal_json`). O Pro Football ganhou o seu `canal.json` com os mesmos valores, e a montagem saiu idêntica.
- **APIs** (`/config/apis`): Claude (vale para todos os canais), Fish Audio (chave, voz, modelo), Pexels, Pixabay, Serper e Smithsonian. Cada canal tem as suas, nos mesmos `.env` que os scripts já liam. As chaves aparecem mascaradas e cada uma tem um botão "Testar"; o Serper não é testado, porque gasta crédito.
- O Pro Football está **sem chave do Pexels**: a busca de vídeo livre só usa o Pixabay.

## Modelos por etapa (2026-10-11)
`/config/modelos`: para cada etapa com Claude (storyboard, escolher imagem, escolher vídeo, confirmar trecho, conferir download, corrigir QA), escolhe-se o modelo (Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1) e o esforço (low → max). Fica gravado em `estudio.json` e vale a partir da próxima chamada. **Esforço low = sem raciocínio** (`MAX_THINKING_TOKENS=0`), o que deixa as escolhas baratas. A página mostra a média de tokens por chamada de cada etapa.

## Checagem do claude antes de rodar (2026-10-11)
Antes da 1ª etapa, o `rodar` (e o `escolher` avulso) chama `checar_claude`: uma chamada mínima (`ok`, sem raciocínio) com cada modelo que as etapas pedidas usam (storyboard → `storyboard`; escolher → `escolher_imagem`, `escolher_video`, `confirmar_trecho`, `conferir`; editar → `qa`). O resultado fica guardado por 15 min em `dados/claude_checagem.json` (por versão + modelo). Se o claude for velho demais para o modelo, ele roda `claude update` sozinho e testa de novo. Se ainda falhar, o bloco para em **"checagem do Claude"** com o motivo e o que fazer: atualizar, gerar novo token (`claude setup-token` → página APIs), trocar o modelo ou esperar o limite. Teste manual: `python -m space_machine checar`.

**(2026-10-12: trava desligada, `travar_conferir: false`; lista só informativa.)** **Conferir antes de entregar (2026-10-11):** `entregar` para enquanto houver "conferir" ou asset pulado sem aprovação; o painel mostra a lista e o botão "Aprovei, pode entregar" (`_estudio/conferir_ok.json`, por texto: mudou a escolha, volta a travar).

**Fila de produção (2026-10-11):** botão "Produzir todos (fila)" na página do vídeo: todos os blocos não entregues, até N por vez (padrão 3); parados ficam de fora; `python -m space_machine fila <vídeo> --max 3`.

**Rodada solta do painel (2026-10-11):** o painel lança cada rodada via `sh … &` com stdin em /dev/null; ela é adotada pelo launchd e sobrevive a fechar/reiniciar o painel.

**Uma rodada por bloco:** o painel considera o bloco "rodando" enquanto o pid em `_estudio/pid` estiver vivo (recolhe zumbis), e o `rodar` se recusa a começar se já houver outra rodada viva. Duas rodadas juntas estragam `cenas.json` e a busca (2026-10-11).

## Roteiro com cold open (2026-10-11)
No "Novo vídeo", um tópico é qualquer linha começando com `#` (`# Nome`, `#Nome` ou `#Nome.`; o ponto sai do nome). Cada tópico vira `blocos/NN/roteiro.txt` com `# Nome` (não narrado) + `Nome.` (narrado) + texto. O texto **antes** do 1º `#` é o **cold open**: vira o `blocos/00`, marcado com `#! cold open`. O storyboard dele sai com `"sem_titulo": true` e `"nome_fala"` igual às 3 primeiras palavras, e o compilador e o editor pulam o card de título (backups `_backup_*_antes_sem_titulo`). A prévia entregue é `edicao/bloco 0.mp4`.

## Próximos passos (onde paramos em 2026-10-12)
**Every NFL Position Explained in x Minutes: 21/21 blocos entregues** em `edicao/bloco N.mp4` (QA 0 falhas; 0,7 s depois da última palavra). Consumo: 1.038 chamadas, ~7,0 mi tokens equiv. (~US$ 32 em API); 2 limites de sessão vencidos pela fila sozinha. Detalhes do dia no [[Log de Aprendizados]] (entradas de 2026-10-11 e 2026-10-12).

Pendências, em ordem:
1. **Arthur assistir** os blocos com mais resgates (02 e 18, 4 cada; 38 no total — buscar "resgate" no `escolhas.json`) e decidir se a escada escolhe bem.
2. **Cortar o ruído do "conferir"** (354 anotações em 21 blocos): deixar só dúvida de identidade/time/época + resgates (prompts `escolher_imagem`/`escolher_video`/`conferir_asset` + `estado._para_conferir`).
3. **Modelo do storyboard:** Opus = 57% do custo (US$ 18 de 32). Testar Sonnet num bloco do próximo vídeo e comparar (decisão do Arthur).
4. **Validar no próximo vídeo** a regra nova do storyboard ("vídeo é exceção, ação vira foto"): medir % de vídeos pedidos e de resgates.
5. QA: "texto solo grande" (~176 px vs 108–136 nas referências) em 5 blocos — medir contra as referências antes de mexer no `gerar_ae2.py`.
6. Licença "desconhecida" em muitas fotos da web (inclusive resgates): risco de direitos a avaliar.
7. Antigos: Every NFL Stadium (blocos 03–30), chave do Pexels, crédito do Fish Audio, Fase 5 (novos canais). YouTube: removido de propósito, não religar.

**Como rodar o próximo vídeo:** painel → vídeo → **Produzir todos (fila)**, até 3 por vez. Rodadas e fila saem soltas do painel (fechar o painel não para nada) e o Mac fica acordado enquanto a fila existir (`fila.lancar_fila` lança `caffeinate -w <pid da fila>`; pela linha de comando `python -m space_machine fila`, iniciar o caffeinate à mão).

## Próximas fases
- Fase 2: um comando que leva o bloco do roteiro até a prévia aprovada pelo QA.
- Fase 3: painel no navegador.
- Fase 4: kanban de produção, calendário e upload para o YouTube.
- Fase 5: outros canais.
