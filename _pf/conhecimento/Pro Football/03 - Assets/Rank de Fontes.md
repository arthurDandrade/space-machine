---
tags: [pro-football, assets, fontes, rank]
---

# Rank de Fontes (e como a busca evita repetição)

> [!danger] YouTube REMOVIDO do sistema (2026-10-11)
> As buscas automáticas fizeram o Google bloquear o IP do Arthur e acusá-lo de fraude/proxy. Nenhum script busca, abre ou baixa nada do YouTube (yt-dlp e plugin de PO token desinstalados; `yt_seguro.py` virou uma trava que sempre recusa; `achar_lance.py` desativado). Vídeo só de bancos livres: Pexels, Pixabay, Wikimedia Commons, Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies). Backup: `ProFootball_backups/antes_remover_youtube_2026-10-11.tar.gz` e `youtube_removido_2026-10-11/`.

Voltar: [[00 - Pro Football (Índice)]] · Técnico: [[Sistema Buscador de Assets]]

Qual ferramenta a busca usa primeiro para cada tipo de asset. Criado em 2026-10-10.

## Princípio
**Não buscar a mesma coisa em várias fontes nem duas vezes na mesma fonte.** Medido em 2026-10-10 nos 4 vídeos já feitos (476 assets): só 2,5% das buscas eram repetidas ao pé da letra, mas **15% dos previews do YouTube (150 de 983) eram de vídeos já abertos em outro card** e 9% das imagens baixadas (209 de 2268) eram repetidas. E cada card de vídeo sem `"fontes"` (305 de 314!) ia a 5 lugares e gerava até 6 folhas, quando 287 de 287 vídeos escolhidos vieram do YouTube.

## Como a busca funciona agora
1. **Camadas** (`config.json` → `fontes_por_tipo`): cada tipo é uma lista de camadas, da melhor para a pior. A busca usa a 1ª camada e **só desce se faltar candidato** (imagem: menos de 16 de tamanho bom; vídeo: menos de `videos_por_asset`, ou YouTube bloqueado).
2. **Parar cedo dentro da fonte**: as 2–3 buscas do card vão do específico ao geral; se a 1ª já trouxe o bastante, a fonte não roda as outras. Nos bancos livres de vídeo, a camada para de consultar fontes quando já tem vídeos suficientes.
3. **Cache global** em `buscador_assets/_cache/` (vale para todos os blocos e vídeos):
   - `busca/`: resultado de cada consulta por fonte, por 7 dias (`cache_busca_dias`). Resultado vazio não é guardado.
   - `img/`: cada imagem baixada, por URL; URL que deu 403/404 fica marcada por 7 dias.
   - `yt_quadros/`: os quadros do storyboard de cada vídeo do YouTube (por id). Vídeo repetido não chama o yt-dlp de novo (menos risco de bloqueio).
   - Limpa sozinho o que passa de 30 dias a cada `buscar.py`. Pode apagar a pasta inteira sem perder nada.
4. O card manda: `"fontes"` muda o rank daquele card (lista simples = uma camada; ou camadas `[["pixabay"], ["google"]]`).

## O rank atual
**Google (Serper) é pago → sempre a última camada de imagem (pedido do Arthur, 2026-10-10)**, e só entra se as grátis trouxerem menos que `candidatos_por_asset` (8) de tamanho bom — não os 16 das outras camadas. Lista de fontes pagas: `fontes_pagas` no `config.json`.


| Tipo | 1ª camada | 2ª camada | 3ª camada |
|---|---|---|---|
| foto | DuckDuckGo, Commons | Pixabay | Openverse, Smithsonian → **Google (pago)** |
| histórica | DuckDuckGo, Smithsonian | Commons | Openverse → **Google (pago)** |
| recorte | DuckDuckGo transparente, DuckDuckGo | Commons | **Google transparente, Google (pago)** |
| logo | DuckDuckGo transparente, Commons | DuckDuckGo | **Google transparente, Google (pago)** |
| mapa | Commons, DuckDuckGo | **Google (pago)** | — |
| bandeira | Commons, DuckDuckGo transparente | **Google transparente (pago)** | — |
| vídeo (sem `"fontes"`) | Pexels, Pixabay | Commons, Archive (só se faltar) | — |
| vídeo de época (`["archive", "commons"]`) | Archive, Commons | — | — |



## De onde vem o rank (medido)
Todas as escolhas de 2026-10-02 a 2026-10-09 (`escolhas.json` × `candidatos.json` de todas as produções): quantos candidatos de cada fonte foram parar na folha e quantos foram escolhidos.

| Tipo | Fonte | Escolhidos / na folha | Taxa |
|---|---|---|---|
| foto | web (DuckDuckGo) | 64 / 468 | 13,7% |
| foto | Commons | 10 / 97 | 10,3% |
| foto | Openverse | 0 / 60 | 0% |
| foto | Smithsonian | 0 / 7 | 0% |
| histórica | web | 9 / 92 | 9,8% |
| histórica | Commons | 0 / 7 | 0% |
| logo | web | 29 / 249 | 11,6% |
| logo | Commons | 5 / 47 | 10,6% |
| recorte | web | 36 / 275 | 13,1% |
| recorte | Commons | 0 / 34 | 0% |
| vídeo | YouTube | 287 / 949 | 30,2% |

Leitura:
- **Busca geral da web ganha quase tudo** (138 de 153 imagens escolhidas). O DuckDuckGo segue no topo; o Google (Serper) dá o mesmo tipo de resultado, mas é pago, então fica como reserva no fim (quando o DuckDuckGo limitar a taxa ou não achar).
- **Commons** acerta em foto e logo (~10%), mas nunca em recorte → recorte põe Commons por último.
- **Smithsonian: o 0% não vale** — rodava com a `DEMO_KEY` (10 buscas/hora) e quase sempre voltava vazio sem avisar (corrigido em 2026-10-10; sem `SI_API_KEY` fica fora da busca). Remedir depois de ter a chave.
- **Openverse e Smithsonian: zero escolhas** → última camada (só aparecem quando nada mais deu).
- **Pixabay** é bom só para genérico (estádio, bola, torcida); fica na 2ª camada de foto, ou no topo quando o card pede `"fontes": ["pixabay", ...]`.
- Google e Pixabay ainda não têm histórico: **refazer a medição depois de 2–3 vídeos** e ajustar as camadas.

## Como refazer a medição
Rodar o mesmo cruzamento (para cada asset em `escolhas.json`, a fonte do candidato `n` em `_work/candidatos/<id>/candidatos.json`, agrupado por tipo e fonte) e atualizar a tabela acima com a data.
