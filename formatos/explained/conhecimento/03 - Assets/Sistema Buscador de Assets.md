---
tags: [pro-football, assets, tecnico]
pasta: motor/busca/
---

# Sistema Buscador de Assets

> [!danger] YouTube REMOVIDO do sistema (2026-10-11)
> As buscas automáticas fizeram o Google bloquear o IP do Arthur e acusá-lo de fraude/proxy. Nenhum script busca, abre ou baixa nada do YouTube (yt-dlp e plugin de PO token desinstalados; `yt_seguro.py` virou uma trava que sempre recusa; `achar_lance.py` desativado). Vídeo só de bancos livres: Pexels, Pixabay, Wikimedia Commons, Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies). Backup: `ProFootball_backups/antes_remover_youtube_2026-10-11.tar.gz` e `youtube_removido_2026-10-11/`.

Voltar: [[00 - Pro Football (Índice)]] · Fluxo: [[Como Buscar Assets]]

Parte técnica do sistema. O Claude roda tudo; esta nota é referência.

## Onde fica
- Motor: `motor/busca/` (Python 3.12 isolado em `.venv`)
- Quem roda: o orquestrador (`space_machine/rodar.py`), etapa por etapa
- Configuração: `motor/busca/config.json` (o canal pode sobrepor em `canal.json` › `busca`) (ordem das fontes, tamanho mínimo, nº de candidatos, domínios bloqueados, duração do preview)

## Scripts
| Script | Faz |
|---|---|
| `transcrever.py <projeto>` | narração → `palavras.json` + `transcricao.txt` |
| `validar_plano.py <projeto>` | confere o plano, preenche tempos e duração dos vídeos |
| `buscar.py <projeto> [--item 01] [--asset ID --refazer --consulta "..."]` | busca e baixa candidatos |
| `detalhar_video.py <projeto> <asset> <n> <ini> <fim>` | frames a cada 0,5 s de um trecho |
| `juntar_folhas.py <projeto> <saida> <assets…>` | junta várias folhas para revisar rápido |
| `finalizar.py <projeto> [--asset ID]` | aplica escolhas → `assets/`, manifesto, créditos, revisão |
| `status.py <projeto> [--pendentes]` | o que falta |

Rodar sempre de dentro de `buscador_assets/` com `.venv/bin/python`.

## Estrutura de um projeto
```
producoes/videos/<slug>/
├── roteiro.txt, narracao.*
├── plano.json         cenas, textos e assets (gatilho + tempo)
├── escolhas.json      candidato escolhido / conferir / pular
├── assets/<item>/<cena>/NN_<gatilho>.(jpg|png|mp4)
├── manifesto.json     ← o agente de edição lê isto
├── creditos.txt
├── revisao.html
└── _work/             transcrição + candidatos (pode apagar depois)
```

## escolhas.json
```json
{"01-03-a": {"n": 7},
 "01-01-a": {"n": 2, "recortar": true},
 "01-04-a": {"n": 1, "inicio": 12.5},
 "01-11-a": {"n": 1, "inicio": 131, "conferir": "confirmar que é o lance"},
 "01-07-b": {"arquivo": "/caminho/img.png", "fonte": "IA (Higgsfield)"},
 "01-12-a": {"pular": true, "motivo": "..."}}
```

## Dependências
ffmpeg, whisper-cli (modelo `~/.cache/whisper/ggml-small.en.bin`), uv (Homebrew), e no `.venv`: ddgs, yt-dlp, rembg, pillow, requests.
Nenhuma chave de API obrigatória (Smithsonian usa `DEMO_KEY`; `SI_API_KEY` opcional).

## Limites conhecidos
- Narração em português exige baixar `ggml-small.bin` (multilíngue) e trocar no `config.json`.
- DuckDuckGo pode limitar a taxa de buscas → rodar de novo depois (só busca o que falta).
- Wikimedia exige User-Agent identificado (já configurado).


## YouTube: removido (2026-10-11)
O freio `yt_seguro.py` (2026-10-06) e o `achar_lance.py` saíram junto com o YouTube, depois de dois bloqueios de IP. Vídeo só de bancos livres (Pexels, Pixabay, Commons, Archive).

### Preview de vídeo por storyboard (2026-10-06)
O `buscar.py` monta a folha `v<n>_folha.jpg` pelas **miniaturas do storyboard do YouTube** (as da barra de progresso, 320x180, grades 3x3 no i.ytimg.com): 1 chamada `yt-dlp -j` + ~400 KB de imagens, **~7 s por vídeo** e cobrindo o vídeo inteiro (até 48 quadros). Antes baixava até 5 min do vídeo em 360p (2+ min por vídeo, e com a fila única do `yt_seguro` travava os outros blocos). Sem storyboard, cai no preview antigo. O título da folha termina em `[storyboard]`. Os tempos de cada quadro são os do storyboard (intervalo irregular de ~5 s); para precisão continua valendo `detalhar_video.py`.


## PO token no YouTube (2026-10-09)
Plugin `bgutil-ytdlp-pot-provider` 2.0.2 instalado no `.venv` (com `uv pip`; o venv não tem pip) e o gerador em `buscador_assets/bgutil/server` (clonado do GitHub oficial na tag 2.0.2, `npm ci && npx tsc`). Modo **script**: o yt-dlp chama o gerador com o node só quando precisa, sem servidor rodando. O `yt_seguro.py` passa `--js-runtimes node:...` e `--extractor-args youtubepot-bgutilscript:server_home=...` automaticamente (backup: `_backup_antes_yt_seguro/yt_seguro_antes_pot.py`). Faz o YouTube ver as chamadas como de navegador e reduz o "confirm you're not a bot". Se o yt-dlp for atualizado e o plugin parar, atualizar os dois juntos (mesma versão no plugin e no server).

## Vídeos fora do YouTube (2026-10-09)
O tipo `video` agora busca primeiro em bancos livres e só depois no YouTube (`config.json` → `fontes_por_tipo.video`). Backup: `buscador_assets/_backup_antes_videos_livres/`.
- **Pexels** e **Pixabay**: vídeos livres até 4K (baixamos até 1080p). Precisam de chave grátis: `PEXELS_API_KEY` / `PIXABAY_API_KEY` em `.env do canal`. Sem chave, são pulados.
- **Wikimedia Commons**: usa só as versões convertidas (`transcoded/...240p.webm` etc.). O arquivo original e várias conexões ao mesmo tempo dão **429**; a folha baixa a versão leve uma vez e tira os quadros localmente.
- **Internet Archive**: filmes de época e do governo dos EUA (muito domínio público). A busca é fraca: as palavras precisam estar no título, assunto ou descrição, e o arquivo de TV (C-SPAN) fica de fora. Mesmo assim vem coisa sem relação; o subagente descarta pela folha.
- Até `videos_livres_max` (3) candidatos livres, intercalando as fontes, + até `videos_por_asset` (3) do YouTube. A folha dos livres é feita pelo ffmpeg pulando para cada tempo (`preview: "direto"`); o trecho final é cortado pelo ffmpeg direto do arquivo (H.264, até 1080p, `setsar=1`). `detalhar_video.py` também funciona com eles.
- **YouTube bloqueado** não trava mais o vídeo: grava os livres e marca `"youtube_pendente": true` no `candidatos.json`; rodar `buscar.py` de novo depois da pausa completa só a parte do YouTube.
- O card pode limitar as fontes com `"fontes"` (ver Biblioteca de Cenas / agente `storyboard`): `["youtube"]` para lance/coletiva, `["pexels", "pixabay", "youtube"]` para plano genérico, `["archive", "commons", "youtube"]` para época.

## Fotos do Pixabay (2026-10-10)
Fonte `pixabay` também para **foto** (`fontes.py` → `pixabay()`; última da lista em `fontes_por_tipo.foto`). Mesma chave dos vídeos (`PIXABAY_API_KEY` em `.env do canal`; sem chave é pulada). Só `image_type=photo`, `safesearch`. Usa o `largeImageURL` (**máx. 1280 px no lado maior**; maior resolução exige acesso total aprovado pelo Pixabay). Serve para genérico (estádio, bola, gramado, torcida, cidade); quase nunca tem jogador ou lance real. Para um card só de genérico: `"fontes": ["pixabay", "commons", "openverse"]`. Limite da API: 100 buscas/min; os termos pedem para não fazer hotlink (a gente baixa, então ok).

## Google Imagens pelo Serper (2026-10-10)
Fontes `google` e `google_transparente` (`fontes.py` → `google()`), via API do Serper (`SERPER_API_KEY` em `.env do canal`; sem chave, puladas). **É pago: fica na última camada de todos os tipos de imagem** e só entra se as fontes grátis trouxerem menos de 8 candidatos bons (ver [[Rank de Fontes]]). Filtros do Google: `isz:l` (grande), `ic:trans` (fundo transparente), `iar:t/w/s` (retrato/paisagem/quadrado). Licença sempre "desconhecida", como no `web`; os domínios bloqueados (bancos com marca d'água) valem igual. Cada consulta gasta 1 crédito. Card antigo com `buscas_por_fonte.web` usa as mesmas buscas no `google`.

## Rank de fontes em camadas (2026-10-10)
`fontes_por_tipo` agora é uma lista de camadas; a busca só desce de camada se faltar candidato bom. Ordem e medição em [[Rank de Fontes]]. Backup: `buscador_assets/_backup_antes_rank_fontes/`.

## Cache e vídeo YouTube primeiro (2026-10-10)
Cache global em `buscador_assets/_cache/` e vídeos sem `"fontes"` buscados primeiro no YouTube (livres como reserva). Detalhes em [[Rank de Fontes]].
