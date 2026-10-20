# Space Machine: como trabalhar aqui

Este repo é um produto que qualquer pessoa instala no Mac para produzir vídeos no formato **"___ Explained"**: lista de tópicos narrada, sem apresentador, com cards de foto/vídeo sobre fundo de papel, editada no After Effects por script. O uso está no `README.md`; este arquivo é para quem mexe no código.

Desde 2026-10-13 (antes eram as pastas `ProFootball/` e `Estudio/`; o histórico das duas está no git).

## Duas coisas separadas: código × dados
- **Código** (este repo, igual para todo mundo). Nada de caminho absoluto, nome de pessoa ou regra de um tema específico aqui.
  - `space_machine/`: orquestrador (`rodar`, `fila`, `escolher`), servidor FastAPI (`servidor.py`: serve o painel na raiz, `/arquivo` e os redirecionamentos dos endereços antigos), `api.py` (API JSON do painel e `/api/eventos`, que avisa o navegador quando uma pasta de produção muda), `capas.py` (capas dos cards, em `cache/capas/` dos dados), `gestao.py` (quadro, ideias, calendário, novo vídeo, excluir para a lixeira — vídeo inteiro ou um bloco, que leva junto os MP4 entregues e volta pelo botão Restaurar; no bloco também dá para limpar só o que foi produzido, que aí vai para o Lixo do Mac), `final.py` (vídeo final: junta os blocos entregues num `final/final.aep` com a camada de ruído e, se pedir, renderiza), `atalho.py` (app "Space Machine" na área de trabalho e os tamanhos pequenos do ícone; o mestre é `painel/public/icone.png`), `meus_prompts.py` (os prompts do canal em `.md`, aba Prompts; não confundir com `prompts/`, que são os das etapas do motor), `limpeza.py` (o que a produção gera e não serve mais vai para o Lixo do Mac: prévias já entregues ou antigas, candidatos de blocos entregues, Auto-Save, e, se você marcar, a lixeira dos canais; roda sozinho ao entregar e pela aba Limpeza ou `limpar`), `configuracao.py` (chaves, identidade, regras do tema, modelos, novo canal), `motor_claude.py` (`claude -p` enxuto, pela assinatura), `prompts/` das etapas, `textos/pt.json` (textos do painel; `t("chave")` no React).
  - `painel/`: o painel em React (Vite + TypeScript). Abre na escolha de canais (`/`) e entra na produção de um canal (`/c/<canal>`); configurações do produtor em `/config`. Telas em `src/telas/`, moldura em `src/casca/`, peças em `src/componentes/`, estilos e tokens em `src/estilo/`. O build vai para `space_machine/static/app/` (fora do git): `instalar.sh` monta, e `./spacemachine` remonta quando `painel/` muda.
  - `space_machine/sistema.py`: pasta de dados, `config()` (`config_padrao.json` + `space_machine.json`), `canais()` e `ambiente_motor()`. `primeiros_passos.py`: checagem do que falta instalar ou configurar.
  - `motor/caminhos.py`: como os scripts do motor acham o canal (`SM_CANAL`), os dados (`SM_DADOS`), as chaves, o cache e as regras do tema. Rodando à mão, deduz o canal pelo caminho do bloco.
  - `motor/busca/scripts/`: buscar, finalizar, compilar_cenas, storyboard.py, transcrever, gerar_narracao, gerar_mapa/tabela.
  - `motor/edicao_ae/`: `gerar_ae2.py` → `montar_modelo2.jsx` → `renderizar.jsx`; `editar_bloco.sh` faz montar + render + QA; `qa/qa_bloco.py`.
  - `formatos/explained/`: o que é do FORMATO. Notas em `conhecimento/` (Biblioteca de Cenas, Da Narração às Cenas, Critérios de Escolha, Controle de Qualidade...), regras do storyboard (`storyboard.md`), `exemplo_cenas.json` e as análises das referências.
  - `docs/`: histórico das decisões do orquestrador.
- **Dados** (fora do repo). Vêm de `SM_DADOS`; senão de `~/.config/spacemachine/dados`; senão de `~/SpaceMachine-dados`. No Mac do Arthur: `/Users/arthur/Canais/SpaceMachine-dados`.
  - `space_machine.json`, `.env` (token do Claude), `space_machine.sqlite`, `cache/`, `logs/claude/`.
  - `referencias/explained/`: vídeos de referência e detecções (direito autoral: nunca no repo).
  - `canais/<slug>/`: `canal.json` (identidade + **regras do tema**), `.env` (chaves do canal), `identidade/`, `conhecimento/` (Índice, **Log de Aprendizados** do canal, Produções), `producoes/<vídeo>/blocos/NN/` (e `final/` do vídeo final, `thumbnail.*` enviada no painel, com as trocadas em `thumbnails_anteriores/`), `producoes/_lixeira/` (vídeos excluídos no painel; nada é apagado), `prompts/` (prompts do canal em `.md`, ex.: o de roteiro; apagados vão para `prompts/_lixeira/`).

## Formato × tema
- O que vale para qualquer canal do formato vai em `formatos/explained/` e nos prompts.
- O que é do ASSUNTO de um canal vai em `canal.json` › `regras`:
  - `escolha` e `storyboard`: listas de regras que entram no fim dos prompts por `motor_claude.prompt(nome, canal)`;
  - `busca.trocar_termos`: lido por `buscar.ajustar_consulta`;
  - `busca.genericas`: buscas do resgate em `escolher.genericas`;
  - `qa.termos_proibidos` + `qa.permitido_se`: lidos por `qa_bloco.checar_origem`.
- O painel edita e sugere essas regras (no canal › Regras do tema). Exemplo completo: o canal `pro-football` (soccer × futebol americano).

## Pipeline de um bloco (`python -m space_machine rodar <bloco>`)
narração (Fish Audio) → transcrição (whisper-cli) → storyboard (Claude, com voltas de correção medidas por `compilar_cenas.py` + `storyboard.py`) → busca → escolha (Claude por asset, com folhas de contato) → editar (`editar_bloco.sh`: After + prévia em meia resolução + QA; uma correção automática se o QA reprovar) → entregar (move a prévia aprovada para `<vídeo>/edicao/bloco N.mp4` e limpa o bloco, se `limpeza_automatica`). Com os blocos entregues, o botão "Juntar no After" (ou `python -m space_machine final <vídeo> [--render]`) monta o vídeo final importando o `bloco_NN_v2.aep` de cada bloco (o MP4 só entra se faltar o .aep) e renderiza tudo de uma vez em 1920×1080.
- **Reels (opcional, bloco a bloco, 2026-10-17):** o botão "Fazer Reels" na página do bloco (ou `python -m space_machine reels <bloco>`, `space_machine/reels.py`) monta o mesmo plano em 1080×1920 com `gerar_ae2.py --vertical` (`bloco_NN_vertical.aep`: cards em coluna ou grade de 2, card único quadrado, rótulo/citação embaixo do card, tabela inteira, texto longo em linhas, sem o botão do CTA) e renderiza `<vídeo>/reels/bloco N.mp4` a 30 fps (metade do tempo dos 60 fps do 16:9: ~2,4 s de render por segundo de vídeo). Nada da produção chama o Reels. O `--vertical` não pode mudar o 16:9: compare o `DADOS` do `montar_NN_v2.jsx` antes e depois.
- A prévia do bloco é de rascunho (2026-10-16): 960×540 a 15 Mbps, ~6x mais rápida. O QA mede em 480×270, então dá o mesmo resultado; a 5 Mbps não (a compressão engorda as letras). `PREVIA_CHEIA=1` antes do `editar_bloco.sh` volta a 1920×1080.
- Cada etapa pula o que já está feito. Bloco entregue conta como editado e aprovado (as prévias podem ter ido para o Lixo); a busca não baixa de novo os candidatos de um asset já escolhido.
- Quando precisa de gente, para com o motivo em `<bloco>/_estudio/estado.json`.
- A fila (`fila`) roda até N blocos por vez e espera o limite da assinatura passar.
- Não há subagentes nem skill de pipeline (removidos em 2026-10-13, sem uso desde 2026-10-10): tudo passa pelo orquestrador. Para refazer uma etapa à mão, use `python -m space_machine rodar <bloco> --de <etapa> --ate <etapa>` ou os scripts de `motor/` direto.

## Regras de trabalho
- **Git:** confira se o `git status` está limpo antes de mexer. Faça um commit por mudança que funcionou, com o porquê. Nunca crie `_backup_*`. Dados nunca entram no repo (`.gitignore`).
- **Sem caminho fixo e sem nome de pessoa no código.** Use `sistema.py`/`caminhos.py`. Mensagem que a pessoa vê fala com "você". Para conferir:
  ```bash
  grep -rn "/Users/" space_machine motor formatos
  ```
  O resultado precisa sair vazio.
- **Sem YouTube** (2026-10-11): buscas automáticas fizeram o Google bloquear o IP do Arthur. Nenhum script busca, abre ou baixa nada do YouTube. Vídeo só de Pexels, Pixabay, Wikimedia Commons e Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies).
- Nunca gerar com IA imagem de pessoa real ou acontecimento real.
- **Medir antes de afirmar.** Compare com as referências em frame cheio (1920×1080). As animações (entrada ease-out ~0,95 s, saída ease-in ~0,8 s) e o zoom por cena no `gerar_ae2.py` estão calibrados: não mexa sem medir. Teste de equivalência rápido: gere a montagem de um bloco pronto antes e depois da mudança e compare o `DADOS` do `montar_NN_v2.jsx`.
- Texto sobre imagem é exceção (~30% das cenas de imagem; só nome/número/data/termo). Cada asset ≥ 1,8 s na tela.
- **Registrar o que for aprendido.** O que é do formato vai na nota certa de `formatos/explained/conhecimento/`. O que é de um canal vai no Log de Aprendizados dele (entrada datada; as 4 do topo vão para o storyboard). Regra nova de escolha também atualiza o prompt correspondente em `space_machine/prompts/`.
- O After às vezes trava num diálogo. Se um script não responder, peça para alguém olhar a tela.
- Painel para testar: `.venv/bin/python -m space_machine painel` (config `space-machine` no `.claude/launch.json`). "address already in use" quer dizer que já há um painel ligado: use a config `space-machine-8766` para testar sem derrubar o dele. O servidor não recarrega sozinho: mudou Python, reinicie.
- Mexeu em `painel/`: `cd painel && npm run checar && npm run build`. Para ver as mudanças na hora, `npm run dev` (config `painel-dev`, porta 5173; repassa a API para a 8765). Versões fixas no `package.json` (o `overrides` segura o `motion-dom` que combina com o `framer-motion`). Texto que a pessoa vê vai no `pt.json` (`t("app....")`). Print de uma tela pelo Chrome headless: abra com `?sem-ao-vivo` (sem a conexão ao vivo a página termina de carregar).
