# Canal Pro Football — como trabalhar aqui

Canal de futebol americano (NFL) no formato **"___ Explained"**: lista de tópicos narrada, sem apresentador, com cards de foto/vídeo sobre fundo de papel claro, textos grandes e animação de entrada/saída. Editado no **After Effects** por script.

## Fonte da verdade: pasta de conhecimento
Todo o conhecimento do canal está na **pasta de conhecimento** `conhecimento/Pro Football/` (notas `.md`, lidas e escritas direto no disco). Leia e escreva direto nos arquivos. Antes de qualquer trabalho, leia `Pro Football/00 - Pro Football (Índice).md` e as notas do tópico da tarefa:
- Formato e cenas: `01 - Formato/`, `02 - Cenas/` (principalmente **Biblioteca de Cenas** e **Da Narração às Cenas**)
- Assets: `03 - Assets/` (Como Buscar Assets, Buscas que Funcionam, Critérios de Escolha)
- Edição: `04 - Edição/` (**Identidade Visual** do canal, Visual do Formato, Animação e Ritmo, Edição no After Effects, **Controle de Qualidade**)
- Erros já cometidos e corrigidos: `05 - Aprendizados/Log de Aprendizados.md` — leia para não repetir.
- Status de cada vídeo: `06 - Produções/`

A pasta de conhecimento fica dentro do projeto: `conhecimento/Pro Football/` (dá para abrir num leitor de Markdown, mas nada depende de app). Backup da base antiga do iCloud: `../ProFootball_backups/vault_icloud_2026-10-05.tar.gz`.

## Pipeline (roteiro + narração → vídeo editado)
1. **Assets**: skill `buscar-assets` (`.claude/skills/buscar-assets/SKILL.md`). Ordem: transcrever → **storyboard pelo subagente `storyboard`** (`.claude/agents/storyboard.md`, um por bloco: escreve e compila o `cenas.json`, mede variedade/ritmo com `scripts/storyboard.py` e entrega `storyboard_NN.md` com tempo, tipo de cena e asset de cada cena) → buscar → escolher → finalizar.
   Motor: `buscador_assets/` (Python em `buscador_assets/.venv/bin/python`).
   Lance específico de um jogo: não há mais vídeo (o `achar_lance.py` dependia do YouTube e foi desativado). Use foto do lance, texto ou número.
   **Escolher + baixar é sempre feito pelo subagente `escolher-assets`** (`.claude/agents/escolher-assets.md`), um por bloco, passando o caminho do bloco. As folhas de contato são imagens grandes: abertas na conversa principal, elas são relidas a cada passo (foi ~50% do gasto do vídeo de 2026-10-03). A conversa principal só lê o resumo que ele devolve.
   Vídeo com vários tópicos: cada tópico é um bloco em `producoes/videos/<slug>/blocos/NN/`; prévia final copiada para `edicao/bloco N.mp4`. De preferência uma sessão nova por bloco.
2. **Edição**: `editor_ae/gerar_ae2.py <projeto> --item NN` → rodar `edicao/montar_NN_v2.jsx` no After (`osascript -e 'tell application "Adobe After Effects 2026" to DoScriptFile "<jsx>"'`) → renderizar com `editor_ae/renderizar.jsx`.
   Atalho que faz montar + renderizar + QA de uma vez: `editor_ae/editar_bloco.sh <pasta do bloco> NN [versao]` (rodar em segundo plano; demora alguns minutos).
3. **QA (obrigatório)**: `editor_ae/qa/qa_bloco.py <projeto> --item NN`. Com qualquer FALHA, corrigir e renderizar de novo antes de mostrar ao Arthur.
4. Produções ficam em `producoes/videos/<slug>/`. Exemplo completo (feito pelo Estúdio, cold open + 20 blocos): `producoes/videos/every-nfl-position-explained-in-x-minutes/`.

## Estúdio (sistema que roda o pipeline) — desde 2026-10-11
O pipeline agora roda pelo **Estúdio** (`/Users/arthur/Canais/Estudio/`). É um orquestrador em Python que executa as etapas sozinho e só chama o Claude (`claude -p` enxuto, pela assinatura) nas decisões. Isso deu ~6× menos tokens na escolha de assets. Nota completa: `conhecimento/Pro Football/04 - Edição/Estúdio (orquestrador).md`.
- **Painel:** `cd /Users/arthur/Canais/Estudio && .venv/bin/python -m estudio servidor` → http://localhost:8765. Páginas: kanban de blocos, Rodar/Parar, Produção (kanban do canal), Calendário, Canais (novo canal + identidade), APIs, Modelos (modelo e esforço por etapa) e Consumo. Erro "address already in use" = já tem um painel ligado.
- **Um bloco do roteiro até a entrega:** `.venv/bin/python -m estudio rodar <pasta do bloco> [--de etapa] [--ate etapa] [--obs "..."]`. Pula o que já foi feito. Quando precisa do Arthur, para com o motivo em `<bloco>/_estudio/estado.json`.
- **Só a escolha de assets:** `python -m estudio escolher <bloco>`. Os subagentes `storyboard` e `escolher-assets` continuam como plano B.
- Config em `Estudio/estudio.json` (modelos/esforço), `Estudio/canais.json` (canais), `<canal>/canal.json` (cores/fonte) e `.env*` (chaves, editadas pelo painel). Consumo em `Estudio/dados/estudio.sqlite`.
- O motor não cria nada sozinho: o Estúdio chama os mesmos scripts (`buscar.py`, `finalizar.py`, `editar_bloco.sh`, `qa_bloco.py`...).

## Regras que não podem ser esquecidas
- **Git (desde 2026-10-13):** `ProFootball/` e `Estudio/` são repositórios git locais (sem GitHub). Antes de mexer em código, confira se o `git status` está limpo. Depois de cada mudança que funcionou, faça um commit com uma mensagem que explique o porquê. **Não crie mais cópias `_backup_*`**: o histórico do git já guarda as versões antigas. Produções, cache, `.venv` e `.env*` ficam fora do git (`.gitignore`).
- **YouTube REMOVIDO do sistema (2026-10-11).** As buscas automáticas fizeram o Google bloquear o IP do Arthur e acusá-lo de fraude/proxy. Nenhum script busca, abre ou baixa nada do YouTube (o yt-dlp foi desinstalado). Vídeo só de bancos livres: Pexels, Pixabay, Wikimedia Commons, Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies).
- **Registrar na pasta de conhecimento tudo que for aprendido** (entrada datada no Log de Aprendizados + atualizar a nota do tópico + nota da produção).
- Medir antes de afirmar: comparar com as referências em frame cheio (1920×1080), nunca em miniatura.
- Texto sobre imagem é exceção (~30% das cenas de imagem; só nome/número/data/termo). Cada asset ≥ 1,8 s na tela.
- Nunca gerar com IA imagem de jogador, técnico ou lance real.
- Cores, fonte (Impact maiúscula em títulos/nomes) e caixa azul seguem a nota **Identidade Visual**; arquivos de marca em `identidade/`.
- Animações (entrada ease-out ~0,95 s, saída ease-in ~0,8 s) e zoom limitado por cena já estão no `editor_ae/gerar_ae2.py`: não alterar sem medir contra as referências.
- Vídeos de referência do formato: `Videos Referencias/` (análise em `Videos Referencias/Analise_Edicao/ANALISE_EDICAO.md`, estudo de cenas em `Videos Referencias/estudo_cenas/`).
- O After às vezes trava num diálogo: se um script não responder, pedir ao Arthur para olhar a tela.
