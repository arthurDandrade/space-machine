---
tags: [pro-football, assets, fluxo]
equivale: skill buscar-assets (.claude/skills/buscar-assets/SKILL.md)
---

# Como Buscar Assets

> [!danger] YouTube REMOVIDO do sistema (2026-10-11)
> As buscas automáticas fizeram o Google bloquear o IP do Arthur e acusá-lo de fraude/proxy. Nenhum script busca, abre ou baixa nada do YouTube (yt-dlp e plugin de PO token desinstalados; `yt_seguro.py` virou uma trava que sempre recusa; `achar_lance.py` desativado). Vídeo só de bancos livres: Pexels, Pixabay, Wikimedia Commons, Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies). Backup: `ProFootball_backups/antes_remover_youtube_2026-10-11.tar.gz` e `youtube_removido_2026-10-11/`.

Voltar: [[00 - Pro Football (Índice)]] · Detalhes: [[Buscas que Funcionam]] · [[Critérios de Escolha]] · [[Sistema Buscador de Assets]]

Entrada: **roteiro + narração pronta**. Saída: **todos os assets prontos**, cada um ligado à palavra da narração em que aparece, + `manifesto.json` para a edição.

> [!tip] Como pedir ao Claude
> "Busca os assets do vídeo X. Roteiro em …, narração em …"

> [!important] Fluxo atual (desde 2026-10-02): cenas primeiro, assets depois
> 1. Transcrever a narração.
> 2. **Planejar `cenas.json`** com os códigos da [[Biblioteca de Cenas]], escrevendo **palavras** (fala e gatilhos), não segundos.
> 3. **Compilar** (`compilar_cenas.py`): acha os tempos, cria os ids, define formato e duração de cada asset pelo layout e gera `plano.json` (busca) + `edicao/plano_edicao_<item>.json` (montagem).
> 4. Buscar → escolher → finalizar (como abaixo).
> 5. Editar no After (`gerar_ae2.py`) — ver [[Edição no After Effects]].
>
> Por quê: é o layout que decide o asset (par → retrato, troca no lugar → vídeo vertical, sticker → logo PNG). Buscar antes de planejar obrigava buscas extras e deixava pares em paisagem.

## Fluxo
```
1. Projeto      roteiro + narração copiados para producoes/videos/<slug>/
2. Transcrever  tempo de cada palavra da narração
3. PLANEJAR     plano.json — cenas, textos e assets (Claude)
4. Validar      acha o tempo de cada asset pela palavra-gatilho
5. Buscar       candidatos de cada asset + folhas de contato
6. ESCOLHER     escolhas.json — Claude olha cada folha (curadoria visual)
7. Finalizar    copia, recorta fundo, baixa trechos de vídeo → assets/ + manifesto
8. Revisão      Arthur abre revisao.html e pede trocas
```

### 1–2. Projeto e transcrição
- Pasta padrão: `<dados>/canais/<canal>/producoes/<slug>/`.
- Transcrição local (whisper `small.en`, inglês) → `_work/transcricao.txt` com `[12.34]palavra`.

### 3. Planejar
Regras em [[Da Narração às Cenas]] e layouts em [[Tipos de Cena]]. Um item por vez.

### 4. Validar
Preenche o `tempo` de cada asset (início da palavra-gatilho) e a `duracao` dos vídeos (fim da cena − gatilho + 0,3 s). Todo aviso de gatilho não encontrado tem que ser corrigido.

### 5. Buscar
| Tipo | Fontes (em ordem) |
|---|---|
| foto | Web (DuckDuckGo), Wikimedia Commons, Openverse, Smithsonian |
| histórica | Smithsonian, Commons, Web, Openverse |
| recorte | Web com fundo transparente, Web, Commons → remoção de fundo automática |
| logo | Web transparente, Commons, Web |
| mapa | Commons, Web |
| bandeira | Commons, Web transparente |
| vídeo | YouTube (preview dos primeiros 5 min, folha com o tempo de cada frame) |

- Os resultados de cada fonte são **intercalados** (nenhuma fonte ocupa todas as vagas).
- Bancos com marca d'água (Alamy, Getty, Shutterstock, iStock, **Vecteezy**…) são descartados automaticamente: o filtro olha a URL, a página, o título e o autor; no Google (Serper) **não dá para usar `-site:`** na consulta (a conta grátis recusa e volta vazio). A Vecteezy esconde a marca d'água na miniatura, e ela só aparece no arquivo grande (2026-10-12).
- Duplicatas são descartadas.
- Fotos pequenas só entram se faltar candidato, marcadas **BAIXA** no fim da folha.
- Receitas de busca: [[Buscas que Funcionam]].

### 6. Escolher — feito pelo subagente `escolher-assets` ⭐ (desde 2026-10-03)
A escolha (6), o lance exato (6b) e o download (7) são feitos por um **subagente** (`.claude/agents/escolher-assets.md`), um por bloco: ele abre as folhas de contato, grava `escolhas.json`, roda `finalizar.py`, confere 2 frames de cada asset baixado (`conferir_assets.py`) e devolve só um resumo com o que ficou para conferir.
- **Por quê:** as folhas são imagens grandes; abertas na conversa principal, são relidas a cada passo até o fim da sessão. No vídeo "How Elite NFL Players Actually Work" (10 blocos), olhar folhas + escolher foi **~50% do gasto** da sessão. No subagente, cada folha é vista uma vez.
- Como pedir: *"faz o bloco 3 usando o subagente para escolher os assets"* (ou automático, pela regra no `CLAUDE.md`).
- Ajudantes: `juntar_folhas.py`, `reusar_candidato.py` (mesmo vídeo oficial em vários cards), `conferir_assets.py`.

Critérios em [[Critérios de Escolha]]. Para vídeo, quando a folha de 2 em 2 s não basta: `detalhar_video.py` (frames a cada 0,5 s numa janela).
- Escolha duvidosa → `"conferir": "motivo"` (aparece em vermelho na revisão).
- Nada serve → refazer com outras buscas (até 2×) → IA **só para coisas genéricas** → senão `"pular"` e trocar por texto.

### 7. Finalizar
- Imagens copiadas; recortes/bandeiras passam pela remoção de fundo (rembg).
- Vídeos: baixa **só o trecho** (duração do card + 1 s), 1080p H.264, sem áudio (pronto para o After).
- Gera `manifesto.json`, `creditos.txt` e `revisao.html`.

### 8. Revisão
Arthur abre `revisao.html` (cada cena: fala, escolhido em verde, alternativas numeradas, avisos em vermelho) e pede trocas: *"no 01-09-a usa a 1"*.

## Regras fixas
> [!danger] Nunca gerar com IA jogador, técnico ou lance real
> Isso fabricaria um registro falso de uma pessoa/evento real. IA só para coisas genéricas (playbook, vestiário vazio, bola). Sem foto real boa → texto.

- Material da NFL tem direitos autorais; o Arthur escolheu usar web e YouTube sabendo disso. O `creditos.txt` registra tudo.

## Tempo esperado
- Busca: ~5–8 min por minuto de narração com muitos vídeos (depois da otimização do preview).
- Curadoria (Claude olhando as folhas): é a etapa mais longa.
