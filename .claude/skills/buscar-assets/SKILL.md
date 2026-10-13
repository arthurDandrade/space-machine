---
name: buscar-assets
description: Busca na internet todos os assets (fotos, vídeos de bancos livres, PNGs recortados, logos, mapas) de um vídeo do canal Pro Football no formato "___ Explained" (cards sobre fundo de papel), a partir do roteiro e da narração pronta. Planeja as cenas, busca, escolhe, recorta, baixa os trechos de vídeo e entrega a pasta assets/ + manifesto.json para a edição. Use quando o Arthur pedir para buscar, achar, baixar ou levantar os assets/imagens/clipes de um vídeo.
---

# Buscar assets — formato "___ Explained"

> **YouTube REMOVIDO do sistema (2026-10-11).** As buscas automáticas fizeram o Google bloquear o IP do Arthur e acusá-lo de fraude/proxy. Nenhum script busca, abre ou baixa nada do YouTube (o yt-dlp foi desinstalado). Vídeo só de bancos livres: Pexels, Pixabay, Wikimedia Commons, Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies).

Você recebe **roteiro + narração** e entrega **todos os assets prontos** para a edição, cada um amarrado à palavra da narração em que aparece. O formato visual está descrito em
`formatos/explained/referencias/Analise_Edicao/ANALISE_EDICAO.md` — leia as seções 3, 4 e 6 antes de planejar o primeiro vídeo.

Motor: `motor/busca/` (scripts em `scripts/`, Python em `../../.venv/bin/python`). Rode sempre a partir dessa pasta:

```bash
cd motor/busca
PY=.venv/bin/python
```

## Fluxo (cenas primeiro, assets depois)
```
1. projeto/      roteiro + narração (copiados, nunca mexa nos originais do Arthur)
2. transcrever   → _work/transcricao.txt (tempo de cada palavra)
3. PLANEJAR      → cenas.json            ← você: cenas com códigos da Biblioteca de Cenas, escritas com PALAVRAS
4. compilar      → plano.json (o que buscar) + edicao/plano_edicao_<item>.json (como montar)
5. buscar        → _work/candidatos/<asset>/folha.jpg
6. ESCOLHER      → escolhas.json         ← você, olhando cada folha
7. finalizar     → assets/ + manifesto.json + creditos.txt + revisao.html
8. editar        → motor/edicao_ae/gerar_ae2.py → After Effects → prévia (ver nota "Edição no After Effects")
```
O layout de cada cena decide o formato do asset (par → retrato, card único → paisagem, PNG → recorte/logo,
troca no lugar → vídeo vertical). Por isso a cena é planejada ANTES da busca.

### 1. Projeto
Pasta padrão: `<dados>/canais/<canal>/producoes/<slug>/` com `roteiro.txt` (itens separados por `# Nome do item`) e a narração copiada.

### 2. Transcrever
```bash
$PY scripts/transcrever.py <projeto>
```
Leia `_work/transcricao.txt` (`[12.34]palavra`). Modelo `small.en` (inglês).

### 3. Planejar (`cenas.json`) — via subagente `storyboard`
**Desde 2026-10-06 o planejamento é feito pelo subagente `storyboard`** (`.claude/agents/storyboard.md`), um por bloco: ele escreve e compila o `cenas.json`, roda `scripts/storyboard.py <projeto>` (gera `storyboard_<NN>.md` com tempo, tipo de cena e asset de cada cena, e avisa variedade < 8, card único > 35%, 3 cards únicos seguidos, asset/troca < 1,8 s, < 15 assets/min, < 40% de cenas que evoluem, texto solo fora de 12–35%) e corrige até não sobrar aviso. Mostre o storyboard ao Arthur antes da busca quando ele pedir. As regras abaixo continuam valendo — são as que o subagente segue.
Leia antes, na pasta de conhecimento (`conhecimento/`): `Pro Football/02 - Cenas/Biblioteca de Cenas.md` (códigos A–F) e `Da Narração às Cenas.md`.
O formato completo está no topo de `scripts/compilar_cenas.py`. Resumo:
```json
{"itens": [{"id": "01", "nome": "Adapting the Pass When the Play Breaks Down",
  "titulo": {"descricao": "Patrick Mahomes mid-throw, full body", "buscas": ["Patrick Mahomes throwing"]},
  "cenas": [
    {"estados": [
      {"layout": "B", "fala": "When pressure forces a quarterback to move,",
       "cards": [{"gatilho": "pressure", "tipo": "video", "descricao": "...", "buscas": ["..."],
                  "sobre": [["forces a quarterback to move", "forces"]]}]},
      {"layout": "A", "fala": "the available passing lanes change.", "textos": ["the available passing lanes change"]}]},
    {"estados": [
      {"layout": "C1", "fala": "Patrick Mahomes can adjust his position",
       "cards": [{"gatilho": "Patrick", "tipo": "foto", "descricao": "...", "buscas": ["..."], "acima": "Patrick Mahomes"},
                 {"gatilho": "throwing", "tipo": "video", "descricao": "...", "buscas": ["..."], "legenda": ["throwing motion", "motion"]}]}]}
  ]}]}
```
- **Nada de segundos**: `fala` = começo do trecho falado (as 3 primeiras palavras localizam o estado); `gatilho` = palavra em que o elemento entra. Tudo escrito como na transcrição.
- **Uma cena = vários estados** quando a composição evolui (família F). Cada estado: `layout` + `cards` e/ou `textos`/`rotulos`.
- Vídeo: só bancos livres. Sem `"fontes"`: Pexels + Pixabay, e Commons + Archive se faltar. Imagem de época: `"fontes": ["archive", "commons"]`. Buscas curtas e visuais, sem nome de time.
- Imagem: sem `"fontes"`, segue o rank em camadas do `config.json` (DuckDuckGo + Commons primeiro; Google/Serper é pago e fica por último; ver nota **Rank de Fontes**). Use `"fontes"` no card só para mudar o rank (ex.: genérico → `["pixabay", "google"]`). Chave do Serper (Google) no `.env` do canal (painel › APIs).
- Card: `tipo` (foto/video/historica/recorte/logo/mapa/bandeira), `descricao`, `buscas`, opcionais `sobre`, `acima`, `legenda`, `sticker` (outro asset), `troca` (lista de assets que trocam no mesmo quadro), `png`, `entra`/`sai`.
- Reaproveitar: `{"reusar": "<id>"}` (asset já pronto) ou `{"arquivo": "_work/candidatos/<id>/04.jpg"}` (alternativa já baixada).
- Textos: `"texto"` ou `["texto", "gatilho", "cresce"|"2linhas"|"abaixo"]`.
- Densidade: ~30% texto (A); 20–25 assets por minuto; não repita o mesmo código duas vezes seguidas.
- **Texto sobre imagem é exceção** (~30% das cenas de imagem): só nome, número, preço, data ou termo-chave — nunca frase da narração. Frases vão para texto solo (A).
- **Cada asset ≥ 1,8 s na tela**; deixe cenas de vídeo durarem 5–15 s. Não picote a cena para seguir cada palavra. Corrija todo AVISO do compilador.

Regras de conteúdo e de buscas (continuam valendo): ver "Buscas que Funcionam" na pasta de conhecimento e a seção abaixo.

**Como escrever as buscas (em inglês, sempre):**
- Do específico para o geral, 2–3 buscas, com time + ano/evento para a época e o uniforme certos.
- Pessoas no Commons: nome entre aspas em `buscas_por_fonte.commons`.
- Lance específico de um jogo: não existe em banco livre — use foto do lance (busca de imagem), texto ou número.
- Gesto técnico genérico: `"NFL quarterback throwing slow motion"`.
- Nome acima do card (`"acima"`, B8): só em **par/trio** (C1/C8 → C4). Em card único sai cortado no topo: para pessoa + nome use **B10** (card desliza e o nome entra) ou B4/B5 (rótulo ao lado). Para escolher o layout de cada situação, ver a tabela "Que layout usar para cada situação" em `02 - Cenas/Da Narração às Cenas.md`.
- Layouts novos (2026-10-05, ver Biblioteca de Cenas): **C8** (par/trio com `troca` num card só), **D5** (sanduíche: cards esq, dir, meio), **D6** (baralho de 3–4), **B10** (1 retrato + `rotulos`: entra no centro e desliza para a direita). Use-os para variar e evitar C1/B seguidos. Também: **A4** (frases curtas encadeadas, uma por gatilho), **B11** (estado logo depois do que fica desfocado atrás; card novo por cima), **G1** (1 card + `"citacao": {texto, grifo, fonte, gatilho}` — texto real da regra/Wikipedia). Vídeos verticais com cortes internos (shorts já editados) são bons para B2/B6. Mais (4ª leva): **B9** lista que acumula, **C9** pilha [trás, frente], **D7** recorte + par, **E5** card + `"lateral"` (bandeira), **E6** diagrama PNG + card, **F8** foto (com `sobre` nome→data) + mapa por cima, **F9** foto com bandeira + mapa à esquerda, **G2** `"tabela"`, **G3** `"grafico"` (dados reais + fonte), **M3** mapa com `troca` + `"dissolve"`, **M5** card + `"lateral": {"mapa": {..., "globo": true}}`, **M6** `"mapa": {..., "silhueta": true}` + mapa, **M7** mapa com `"sticker": {..., "pos": "dentro"}`. Detalhes e medidas: Biblioteca de Cenas › "Como escrever no cenas.json".
- Treino/offseason/OTAs: destaques oficiais dos times (`"<ano> OTA Practice Highlights <Time>"`, `"<Time> Mandatory Minicamp Highlights"`); um vídeo serve para vários cards (copie a entrada no `candidatos.json` do outro asset). Confira frames do trecho baixado: sobreposições ("SUBSCRIBE", rótulos) não aparecem na folha.
- Depois que o `plano.json` existe, **não recompile** o `cenas.json` para ajustes pequenos (gera ids novos e quebra o `escolhas.json`): edite o `edicao/plano_edicao_<item>.json`.
- `recorte`: objeto isolado; `logo`: `"<time> logo"`; `mapa`: prefira **gerar** com `"mapa": {"eua": ["Missouri"], "pontos": ["Kansas City:39.10:-94.58"]}` ou `{"pais": ["Germany"]}` no card (cores do canal, sem busca; ver Biblioteca de Cenas › M); buscar `"<cidade> locator map"` só para mapas que o gerador não faz (satélite, mapa antigo).
- Vídeo em layout retrato (pares, troca no lugar) ganha automaticamente variações `#shorts`.

### 4. Compilar
```bash
$PY scripts/compilar_cenas.py <projeto>
```
Acha o tempo de cada fala/gatilho, cria os ids dos assets (nunca repete um id existente), define orientação e duração pelo layout, e gera `plano.json` + `edicao/plano_edicao_<item>.json`. Se listar "CORRIGIR", ajuste a palavra no `cenas.json` (copie da transcrição) e rode de novo. `scripts/status.py <projeto> --pendentes` mostra só o que ainda falta buscar.

### 5. Buscar
```bash
$PY scripts/buscar.py <projeto> --item 01          # um item por vez
```
Fontes em camadas (nota **Rank de Fontes**): imagens DuckDuckGo + Commons primeiro, Google (pago) por último; vídeos: só bancos livres. Cache global em `buscador_assets/_cache/` (buscas 7 dias, imagens e quadros do YouTube): repetir uma busca em outro bloco ou com `--refazer` não vai de novo à internet. ~2–3 min para 10 assets. Sites de banco de imagens com marca d'água (Alamy, Getty, Shutterstock…) são descartados automaticamente; duplicatas também.

### 6. Escolher (`escolhas.json`) — via subagente `escolher-assets`
**Não abra as folhas na conversa principal.** Depois do `buscar.py`, chame o subagente `escolher-assets` (`.claude/agents/escolher-assets.md`) com o caminho do bloco; ele faz os passos 6, 6b e 7 (escolher, achar lance, finalizar, conferir frames) e devolve só um resumo com o que ficou para conferir. Vários blocos podem rodar em paralelo. As regras abaixo continuam valendo — são as que o subagente segue.
Ajudantes: `scripts/juntar_folhas.py` (junta folhas), `scripts/reusar_candidato.py` (usa o candidato de outro asset), `scripts/conferir_assets.py` (2 frames de cada asset baixado).
Abra (Read) cada `_work/candidatos/<asset>/folha.jpg`. Para vídeo, as folhas são `v1_folha.jpg`, `v2_folha.jpg`… com o tempo de cada frame.

```json
{"01-03-a": {"n": 7},
 "01-01-a": {"n": 2, "recortar": true},
 "01-04-a": {"n": 1, "inicio": 12.5},
 "01-07-b": {"arquivo": "/caminho/imagem.png", "fonte": "IA (Higgsfield)"},
 "01-09-a": {"pular": true}}
```

**Critérios (nesta ordem):**
1. **Literal**: mostra exatamente o que é dito (a pessoa certa, o time certo, a época e o uniforme certos). Na dúvida entre bonita e certa, escolha a certa.
2. **Limpa**: sem marca d'água, sem texto/gráficos por cima, sem moldura, sem colagem, sem foto de quadro autografado/produto, sem print de tela com interface.
3. **Legível em card**: assunto grande e central; funciona cortada em retrato se o layout pede retrato.
4. **Resolução**: prefira ≥1200 px no lado menor para card grande; ≥700 para cards de 2–3.
5. `recorte`: **um assunto só**, sem outro jogador encostando ou na frente (a remoção de fundo leva junto quem estiver colado: um defensor caído virou parte do recorte no teste), fundo simples, de preferência corpo inteiro e sem cortes nas bordas. Se a melhor é uma foto com fundo, tudo bem: o motor tira o fundo. Para logo com fundo branco/colorido, use `"recortar": true`.
6. Vídeo: escolha o trecho que **começa um pouco antes da ação** (snap, arremesso) e não tem só o narrador falando, replays com gráficos ou o placar cobrindo o lance. Se a folha de 2 em 2 s não for precisa, detalhe:
   ```bash
   $PY scripts/detalhar_video.py <projeto> <asset> <n_video> <ini> <fim>   # frames a cada 0,5 s
   ```

Quando escolher um trecho de vídeo sem detalhar, ou quando não tiver certeza de que é o lance certo, adicione `"conferir": "motivo"` na escolha: aparece em destaque na `revisao.html` para o Arthur olhar. Para pular um asset, use `{"pular": true, "motivo": "..."}`.

**Se nada serve:**
1. Rode de novo com outras buscas: `$PY scripts/buscar.py <projeto> --refazer --asset ID --consulta "..." --consulta "..."` (até 2 tentativas).
2. Ainda sem nada: **gere com IA** (Higgsfield `generate_image`, foto realista, fundo coerente com o estilo) **apenas para coisas genéricas** — objetos, conceitos, cenas sem pessoa identificável (ex.: "um playbook rabiscado", "um vestiário vazio"). **Nunca gere imagem de jogador, técnico ou lance real**: isso fabricaria um registro falso de uma pessoa ou evento real. Nesses casos, troque o asset por texto (layout A/E) ou por outra imagem relacionada, e anote para o Arthur.
3. Registre a imagem gerada com `{"arquivo": "...", "fonte": "IA (Higgsfield)"}`.

### 6b. Lance específico de um jogo — desativado
O `achar_lance.py` casava o placar de transmissões baixadas do YouTube; saiu do sistema junto com o YouTube (removido em 2026-10-13). Lance específico vira foto (busca de imagem), texto ou número.

### 7. Finalizar
```bash
$PY scripts/finalizar.py <projeto>                 # tudo
$PY scripts/finalizar.py <projeto> --asset 01-03-a # refaz só um
$PY scripts/status.py <projeto> --pendentes
```
- Imagens copiadas; `recorte`/`bandeira` (e quem tiver `"recortar": true`) passam por remoção de fundo (rembg) e ficam em PNG cortado rente.
- Vídeos: baixa só o trecho escolhido (duração do card + 1 s de margem), 1080p H.264, sem áudio.
- Confira 3–4 recortes abrindo o PNG final; se o recorte comeu parte do assunto, escolha outro candidato.

### 8. Entregar
- Mostre ao Arthur a `revisao.html` (cada cena: fala, escolhido em verde, alternativas numeradas). Ele pede trocas como "no 03-05-a usa a 4".
- Avise: quantos assets, quantos vídeos, o que ficou sem asset ou foi gerado com IA, e que `creditos.txt` lista fonte e licença de cada um.
- O `manifesto.json` é o que o agente de edição vai ler (arquivo, item, cena, tipo, gatilho, tempo, papel, dimensões, origem).

## Avisos
- **YouTube REMOVIDO do sistema (2026-10-11).** As buscas automáticas fizeram o Google bloquear o IP do Arthur e acusá-lo de fraude/proxy. Nenhum script busca, abre ou baixa nada do YouTube (o yt-dlp foi desinstalado). Vídeo só de bancos livres: Pexels, Pixabay, Wikimedia Commons, Internet Archive. Nunca religar nem contornar (VPN, proxy, cookies).
- Material da NFL (fotos de jogo, transmissões, logos) é protegido por direitos autorais; o Arthur escolheu usar busca na web sabendo disso. Mantenha o `creditos.txt` sempre gerado.
- A busca do DuckDuckGo pode limitar a taxa de buscas: o script espera entre buscas e tenta de novo; se falhar muito, espere alguns minutos e rode `buscar.py` de novo (ele só busca o que falta).
- Smithsonian só entra na busca com `SI_API_KEY` (grátis em api.data.gov) no `.env` do canal; sem ela é pulado (a `DEMO_KEY` só dava 10 buscas/hora).

## Registrar o que aprendeu (pasta de conhecimento)
O conhecimento do canal vive na pasta de conhecimento `conhecimento/Pro Football/` (arquivos `.md`, editados direto no disco). Ao terminar uma busca de assets:
- Acrescente no topo de `Pro Football/05 - Aprendizados/Log de Aprendizados.md` uma seção datada com o que deu certo/errado.
- Se virou regra, atualize também a nota do tópico (`03 - Assets/Buscas que Funcionam.md`, `Critérios de Escolha.md`, `02 - Cenas/...`) **e** esta skill.
- Atualize a nota da produção em `Pro Football/06 - Produções/` (status, o que falta conferir).

## Controle de qualidade (obrigatório antes de entregar um bloco)
Depois de renderizar a prévia no After:
```bash
cd motor/edicao_ae && ../../.venv/bin/python qa/qa_bloco.py <projeto> --item <id>
```
Leia `edicao/qa_<id>.md` e abra `edicao/qa_<id>.jpg`. Com qualquer ❌ FALHA: corrija o `cenas.json`, compile, remonte, renderize e rode o QA de novo — não entregue. Mostre ao Arthur as ⚠️ ATENÇÕES restantes junto com a prévia. Detalhes na pasta de conhecimento: `Pro Football/04 - Edição/Controle de Qualidade.md`.
