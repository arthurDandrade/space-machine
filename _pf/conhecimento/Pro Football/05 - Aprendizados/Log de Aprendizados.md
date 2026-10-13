---
tags: [pro-football, aprendizados, log]
---

# Log de Aprendizados

Voltar: [[00 - Pro Football (Índice)]]

Tudo o que descobrimos em cada teste ou produção, em ordem de data (mais recente em cima). Quando um aprendizado vira regra, ele também é atualizado na nota do tópico e na skill.

---

## 2026-10-13 — Revisão do sistema (Estúdio + ProFootball): falhas corrigidas
Revisão do código inteiro procurando falhas e lixo. Backup do código antes: `ProFootball_backups/codigo_antes_revisao_2026-10-13.tar.gz`.
- **Botão "Parar" do painel não parava nada.** A rodada é filha de um `sh` líder de sessão, então o grupo de processos é o do `sh` e não o pid da rodada. O `killpg(pid)` dava erro calado, o painel apagava o pid e liberava outra rodada no mesmo bloco, que é o caso que estraga o `cenas.json`. **Agora** usa `killpg(getpgid(pid))` (testado: mata a rodada e os filhos dela).
- **Fila podia "ver" o limite liberado antes da hora.** A checagem do claude fica guardada por 15 min. Se o limite batia logo depois de uma checagem ok, a fila acordava, lia o "ok" guardado e relançava os blocos. **Agora** o limite apaga a checagem guardada (`motor_claude.chamar`) e a fila sempre testa de verdade.
- **QA velho podia aprovar prévia nova.** Se o QA da v5 não rodasse, o `qa_NN.md` ainda era o da v4 (aprovada), e o `rodar` aprovava a v5. **Agora** o `rodar` só aceita o QA se a linha "Prévia:" cita a prévia daquela versão.
- **Prévias da v10 em diante:** o `editar` ordenava por nome (`v10` antes de `v2`). Agora `rodar` usa `estado.previas` (ordem numérica) nos 3 lugares.
- **`editar_bloco.sh`:**
  - Se a montagem falhava, ele renderizava o `bloco_NN_v2.aep` da versão anterior. **Agora** sem "OK comp=" no log, para com erro.
  - O render esperava o log para sempre. Com o After travado num diálogo, isso segurava a trava do After (e a fila inteira) até o timeout de 3 h. **Agora** espera no máximo 1 h.
- **Ruído:** o Estúdio deixava 2 arquivos por chamada ao Claude em `dados/claude_cwd/` (1.332 arquivos). Agora só ficam os das chamadas que falharam.
- **Docs:** o exemplo do CLAUDE.md apontava para uma pasta que não existe mais. A nota [[Edição no After Effects]] ainda ensinava o editor v1 (`gerar_ae.py`). A nota do [[Estúdio (orquestrador)]] ainda citava o `achar_lance.py`.

## 2026-10-13 — Aprendizados viram regra automática (para não depender de ninguém lembrar)
O Arthur perguntou se os aprendizados estavam resolvidos para os próximos vídeos. Parte estava só anotada. Agora:
- **Busca:** `buscar.py` troca "football" sozinho por "american football" (`sem_soccer`), a não ser que a consulta já diga american/NFL/college/soccer.
- **Escolha e conferência (Estúdio `prompts/escolher_imagem.md`, `escolher_video.md`, `conferir_asset.md` + subagente `escolher-assets`):** recusar soccer (bola redonda, rede de gol, FIFA, Copa), marca d'água de banco (inclusive a da Vecteezy, fraca e em diagonal) e render de IA no lugar de foto.
- **Storyboard (subagente `storyboard.md`, que o Estúdio também usa, regras 12–14) + `storyboard.py` avisa:** B10 com o nome < 1,5 s depois do card (→ B4), rótulos a < 1,2 s um do outro (menos no B9), último texto < 1,2 s antes da troca, A4 com frases a < 1,0 s, "cresce" que não começa com o texto anterior, buscas com "football" sozinho. Testado: pega o Brady (01), o "receiver" (05) e o "Monday Night Football" (08).
- **QA (`qa_bloco.py`) com 3 verificações novas:** texto por cima de imagem, texto pouco tempo na tela, origem dos assets (ver [[Controle de Qualidade]]). A de origem usa a lista de domínios do buscador: "alamy"/"dreamstime" no NOME do arquivo de foto licenciada republicada (PFF etc.) não é problema.
- **Editor:** A4 em que alguma frase ficaria < 1 s empilha as frases (como lista) em vez de trocar.

## 2026-10-13 — Mapa/logo cortados pelo card, nomes empilhados na cascata, "cresce" falso
Arthur viu nos blocos 04, 07 e 08 do positions:
- **"DETROI" cortado (04) e "G" dos Packers cortado (07):** o card preenche o espaço do layout cortando a imagem (certo para foto, errado para mapa 4:3 em card quadrado e para logo). **`gerar_ae2.py`:** mapa gerado e assets `logo`/`mapa`/`bandeira` ficam **inteiros**: o card toma o formato da imagem dentro do espaço do layout (`Montador.inteiro`).
- **Mapa inteiro no par (C1) ficava minúsculo:** o C1 limita cada card a ≤ 1:1 (retrato). O mapa 4:3 inteiro encolhia para ~1/4 da tela e o QA reprovou 14 e 20 por "palco vazio". **Agora** mapa/logo usam o próprio formato na conta do par (até 1,78) e ganham largura em vez de encolher.
- **Nomes por cima uns dos outros na cascata D6** ("JERRY KRAMER / KEN BOWMAN / JETHRO PUGH / BART STARR"): cada card trazia o nome ("sobre") até o fim do estado. **Agora** o nome de um card sai quando entra o nome de um card que cai em cima dele.
- **"November 18, 1985" → "Monday Night Football" (08):** o storyboard marcou "cresce", mas a frase nova não completa a anterior. A data sumia num corte e o texto novo entrava sem fade. **Agora** "cresce" só vale se o texto começa com o anterior; senão é troca normal (0,13 s de palco vazio + fade).

## 2026-10-13 — Nomes nos mapas pequenos, repetidos e cortados
- O QA acusava texto de 36 px nos mapas: `gerar_mapa.py` escrevia o nome da cidade com 40 px e o rótulo da região com 64 px num PNG de 1600, e no vídeo o card mostra o mapa a ~45% (~18/28 px). O "PITTSBURGH" saía **duas vezes** (rótulo + ponto), e o do ponto **cortado na borda** ("PITTSBURG"), porque só o rótulo checava os limites.
- **Correção (`gerar_mapa.py`):** rótulo da região de 150 px (diminui até 76 para caber); cidade de 96 px (64 com mais de 3 pontos), também diminuindo; ponto com o mesmo nome do rótulo não repete o texto; nada sai do mapa; rótulo pode ir embaixo/em cima alinhado pelo lado de dentro (região na borda, "NEW YORK GIANTS" no NJ). Os mapas do vídeo foram refeitos (o nome do arquivo é o hash da especificação, então refazer = mesma spec + `compilar_cenas.gerar_mapa`).

## 2026-10-12 — Última palavra empilhada sumia antes de dar para ler (B9 "fullback / tight end / receiver")
- No B9 (e no B10/A) a última palavra é dita colada na troca de cena: "receiver" ficava 0,8 s e "2 safeties" (bloco 14) 0,42 s. O Arthur viu no bloco 05.
- **`gerar_ae2.py`:** se o último rótulo ou texto de um estado ficaria menos de 1,2 s na tela, o estado seguinte espera até 0,8 s, sem passar de 1 s antes do estado depois dele. Com a saída junto do card (0,8 s), a palavra fica legível ~2 s. Mudou 11 blocos do positions, entre 0,05 e 0,8 s cada.

## 2026-10-12 — Positions, bloco 03: futebol no lugar de futebol americano, mais Vecteezy, lista rápida
- **03-03-a ("packed football stadium crowd") era um vídeo da Copa de 2022** do Internet Archive, com selo FIFA. O "conferir" até citava o selo FIFA e o placar "3-4 ARGENTINA", e mesmo assim passou. **"football" sozinho traz futebol**: nas buscas escrever "american football" ou "NFL". Escolha que menciona FIFA, Copa ou gol tem que ser recusada. Trocado por Arrowhead lotado (Commons). O 03-03-b, que era um resgate (foto de handoff no lugar de torcida), virou torcida dos Rams no SoFi.
- **Mais 3 assets da Vecteezy no mesmo bloco**: o microscópio e o cérebro (PNG com marca d'água) e o 03-05-a (render 3D gerado por IA). Trocados por microscópio do Pixabay recortado com rembg, cérebro do Pixabay com o fundo preto removido e arquibancada vazia real (Washington 2020, Commons). A Vecteezy já está bloqueada no buscador.
- **Lista narrada em sequência ("memory loss, confusion, years of struggle") no A4** trocava a cada ~0,85 s. Para lista dita de uma vez, **empilhar** (textos "cresce", a frase que cresce): os itens ficam todos na tela.
- **Nome no B10 aparecia 0,6 s** ("Bennet Omalu" dito no fim da fala, com a cena seguinte logo atrás). Correção: B4, rótulo em "named" e a cena seguinte entrando na palavra-chave ("brain") em vez da 1ª palavra. **Regra:** rótulo de nome precisa de ≥ 1,5 s até o próximo estado.
- **Varredura do vídeo inteiro:** mais 13 assets da Vecteezy em 9 blocos (vários vindos de sites como inspiredpencil, que hospedam o arquivo da Vecteezy). **Bloqueio reforçado:** `buscar.py` descarta o resultado se "vecteezy" (ou outro domínio bloqueado) estiver na URL, na página, no título ou no autor. ⚠️ Tentei também excluir na consulta do Serper com `-site:vecteezy.com`, mas **a conta grátis do Serper recusa o operador** ("Query pattern not allowed for free accounts") e o Google voltava vazio, o que estragou o 1º lote de trocas. Desfeito: o bloqueio fica só no filtro. A troca automática pelo Estúdio também deixou a desejar (2 pulados, logo e end zone ainda da Vecteezy, mesma foto de 462 px em dois títulos, saco de dinheiro, recorte com 3 jogadores), e terminei à mão: Serper `google_transparente` + Pixabay + rembg. Os 14 foram buscados de novo (recortes e logos começando pelo `google_transparente`) e escolhidos pelo Estúdio com a observação "sem marca d'água/IA/futebol".
- **A chave do Pexels (`PEXELS_API_KEY`) está vazia** em `.env.fontes`: o Pexels não está sendo consultado.
- Commons devolve "too many requests" com várias chamadas seguidas: juntar títulos numa consulta só (`titles=A|B|C`) e esperar uns segundos entre os downloads.

## 2026-10-12 — Positions, bloco 01: texto por cima do recorte, texto saindo antes da imagem, rótulos rápidos demais
Arthur viu na prévia aprovada pelo QA (o QA não pegou nenhum dos três):
- **E3 "since 1994": texto por cima do capacete.** O gerador punha o texto do E3 no centro da tela. **`gerar_ae2.py`:** no E3 o texto vai para o espaço à direita do recorte. E3 sem PNG usa a geometria do B4.
- **Texto saía antes da imagem.** Os textos sumiam num corte seco (no início ou no fim da saída), e o card ainda levava 0,8 s saindo. **Agora** todo texto que vai até o fim do estado sai junto com os cards: fica até o fim da saída e apaga na mesma janela de 0,8 s.
- **Tom Brady (B10): "Tom Brady" → "199th pick" → "2000 draft" trocando a cada ~0,8 s, fora da fala.** Duas causas. (1) No B10 o card entrou junto com "Tom", então o 1º rótulo só aparecia depois do deslize, quando a fala já estava em "199th". A regra (card ≥ 1,5 s antes da palavra) já existia, mas o storyboard não a cumpriu. **Nesse caso usar B4.** (2) **Regra nova no gerador:** rótulo que ficaria menos de 1,2 s na tela entra junto com o seguinte, em 2 linhas ("199th pick / 2000 draft").
- **Marca d'água da Vecteezy no capacete (01-05-a)**, de novo e com o "conferir" dizendo "sem marca d'água". O aviso de 2026-10-09 estava no log, mas o domínio nunca foi bloqueado. **`buscador_assets/config.json`:** `vecteezy` em `dominios_bloqueados`. Trocado por recorte do Pixabay (7701535).

## 2026-10-12 — Blocos "parados há horas": busca lenta no Archive + kanban enganoso
- Vídeos do Internet Archive de ~17 min (abaixo do corte de 30) levavam 1–2 min **por quadro** da folha; o bloco 06 passou 15 min num só vídeo. **`buscar.py`:** prazo de 90 s por vídeo (`PREVIEW_MAX_S`) e no máximo 60 s por quadro; estourou, fica com os quadros que deu ou pula o vídeo.
- O kanban mostrava "parado: escolher" (motivo antigo) em blocos que estavam **na fila** esperando vaga. Agora mostra **"na fila"**.

## 2026-10-12 — Assets faltando paravam metade dos blocos: prevenção + resgate automático
- Medido nos 10 blocos parados: faltavam **18 de 64 vídeos (28%)** e **5 de 8 históricas (62%)**; **0 de 79 fotos** e 0 de 23 recortes/logos. Causa: o storyboard pedia vídeo de ação de futebol americano (inexistente nos bancos livres sem o YouTube); a foto no lugar usava a mesma descrição específica e o Claude recusava. Históricas caíam em livros escaneados (djvu do Commons, "The Film Daily").
- **Prevenção:** prompt do storyboard (Estúdio e subagente) — vídeo é exceção, ação é foto, histórica é foto de acervo; ver [[Buscas que Funcionam]]. Commons filtra djvu; histórica busca Commons primeiro.
- **Resgate (o bloco não para mais por asset):** \`escolher.resgatar()\`: (1) foto com busca **genérica** e escolha "a relacionada mais próxima"; (2) candidato não usado de outro asset da mesma cena; (3) repetir o vizinho. Tudo com "conferir". Teste: 19-04-a (bloqueio na linha, vídeo) → foto ótima de linha de scrimmage. \`estudio.json\` → \`"resgatar_assets": false\` desliga.
- A fila tenta de novo blocos parados por "assets sem arquivo".

## 2026-10-12 — Vídeo gigante do Internet Archive derrubou a busca de 9 blocos
- A busca de vídeo trouxe "Super Bowl X" (transmissão inteira, horas) do Archive. Tirar quadros dele pela rede estourava o timeout de 120 s do ffmpeg, e o `TimeoutExpired` subia e **derrubava o `buscar.py` do bloco inteiro** (06, 08, 11, 12, 14, 16, 17, 18, 20).
- **Correção (`buscar.py`):** vídeo com mais de 30 min é pulado antes do preview (`DURACAO_MAX_S`); timeout de um quadro perde só aquele quadro; erro no preview de um vídeo pula só aquele vídeo.
- A fila agora tenta de novo (1 vez por fila) blocos parados por "busca falhou" ou "erro inesperado".

## 2026-10-12 — Limite do Claude de madrugada: fila queimou 15 blocos e não voltou
- O claude novo avisa o limite como **"You've hit your session limit · resets 1:40am"**; o Estúdio só reconhecia "usage limit". Virou "erro do Claude" comum: a fila não viu o limite e lançou 06–20 em 5 min (todos pararam na hora). Agora `motor_claude.eh_limite()` reconhece os textos (session/weekly/rate limit, "hit your … limit").
- A fila pulava **todo** bloco parado, até os parados por limite: clicar "Produzir todos" de manhã não fez nada. Agora: parado por limite/erro do Claude/checagem **volta para a fila**; só parado por decisão (assets sem arquivo etc.) fica para o Arthur.
- No limite, a fila **pausa** (status "pausada" no kanban, com a hora que libera), testa a cada 10 min e **continua sozinha** quando libera.
- Durante o limite as escolhas falham e alguns assets ficam sem escolha ou com "pular" falso: conferir `escolhas.json` dos blocos que pararam em "assets sem arquivo" depois de um limite.

## 2026-10-12 — Trava do "conferir" desligada (pedido do Arthur)
- Na prática a trava só atrasava: o Arthur não usa a lista para barrar a entrega. Agora `estudio.json` → `"travar_conferir": false`: a entrega não espera; a lista continua no painel como **"Para conferir (não trava a entrega)"** com o botão **"Marcar como visto"**. Para religar: `true`.
- A fila entrega sozinha bloco que parou só pelo conferir (rodadas que começaram com o código antigo).

## 2026-10-11 — Fila de produção ("Produzir todos") + bloco 02 morto em silêncio
- **Fila:** botão na página do vídeo põe todos os blocos não entregues em fila, até N por vez (padrão 3). Conta no limite os blocos rodando à mão; bloco "parado" (esperando o Arthur) fica de fora; cada bloco é lançado uma vez por fila; "limite de uso" do Claude encerra a fila. "Parar fila" só impede novos lançamentos. Estado em `<vídeo>/_estudio/fila.json`, log em `log_fila.txt`. Linha de comando: `python -m estudio fila <pasta do vídeo> --max 3`.
- **Bloco 02 morreu na escolha** por erro meu: a lista "outros assets da cena" quebrava no asset do **título** (não tem cena). E o `rodar` só tratava erros do Claude: erro de programa matava o bloco com "rodando" no estado, sem aviso. Agora qualquer erro inesperado vira "parado" com o motivo.

## 2026-10-11 — Rodada morria ao fechar o terminal do painel (bloco 01)
- A rodada era filha do painel (`subprocess.Popen` com `start_new_session`) e herdava o stdin do terminal dele. Ao fechar a aba do terminal do painel (eu fiz isso para reiniciar), (1) a rodada do bloco 01 morreu sem deixar erro, e (2) antes disso, todo script que ela abria falhava na largada (`Fatal Python error: init_sys_streams … Bad file descriptor`): as buscas de "foto no lugar do vídeo" nem rodaram e 4 assets viraram "pular" por falso "nada serviu".
- **Correção:** o painel lança a rodada **solta** (`sh -c '"$@" </dev/null >>log 2>&1 & echo $!'`: quem adota é o launchd, PPID 1) com stdin em /dev/null. Fechar ou reiniciar o painel não afeta mais as rodadas. ⚠️ Vale só para rodadas iniciadas **depois** de reiniciar o painel com o código novo.
- Sinal para procurar: "Bad file descriptor" em `_estudio/log_*.txt` = buscas que não rodaram; os "pular" daquele trecho são falsos.

## 2026-10-11 — Vários blocos ao mesmo tempo
- A saída de cada chamada do Claude ia para `dados/claude_cwd/ultima_<etapa>.jsonl`: dois blocos no storyboard (ou na correção do QA) ao mesmo tempo escreviam no **mesmo arquivo**. Agora o nome leva vídeo + bloco (+ asset).
- O que já era seguro: uma rodada por bloco (pid), o After em fila (`dados/trava_after`: um bloco por vez renderiza, os outros esperam "esperando a vez no After"), assets com ids próprios por bloco.
- Limite prático: o Claude da assinatura é um só (cada bloco na escolha já faz 3 chamadas em paralelo); 2–3 blocos juntos é o razoável.

## 2026-10-11 — Frase final contínua + painel que não fica atualizando
- **Final do cold open parecia 3 cenas:** A4 ("This is" some → palco vazio → "every NFL position") + troca de estado para o "explained". Para uma frase só, o A4 quebra a leitura. **Editor:** estado com textos em cadeia `"cresce"` (cada um = anterior + palavras) vira **frase que cresce**: nada some, cada pedaço entra numa linha embaixo e o bloco sobe meia linha (0,35 s) para ficar centrado. Use **A4 só para frases diferentes**; frase única que se completa = um estado com a cadeia `"cresce"`.
- **Painel atualizando o tempo todo:** a página do bloco redesenhava a cada 4 s (o player da prévia recomeçava e travava) e o kanban a cada 5 s. Agora: sem mudança, o servidor responde 204 (nada é trocado); com o bloco parado, 286 (a página para de perguntar). Rodar/Parar/Aprovar recarregam a página e o acompanhamento volta.
- ⚠️ O htmx **troca o conteúdo** numa resposta 286 (vazia): o kanban sumia. `base.html` agora cancela a troca no 286. E o `video.html` tinha o formulário de Publicação colado dentro do `{% block titulo %}` (título da aba quebrado): corrigido.

## 2026-10-11 — Fim do bloco sem silêncio + "conferir" trava a entrega
- **Silêncio no fim:** a composição durava `fim da fala + 3 s` fixos (`gerar_ae2.py`), e o Arthur cortava ~3 s à mão em cada bloco ao juntar. Agora o bloco acaba **0,6 s depois da última palavra** (`FIM_BLOCO`), ou quando termina a última saída animada (no máximo +2 s). Como cada bloco começa 0,2 s antes da fala, a emenda fica com ~0,8 s de pausa. Cold open: 15,4 → 13,1 s.
- **"conferir" trava a entrega (Estúdio):** a etapa `entregar` para se houver "conferir" ou asset pulado ainda não aprovado. No painel aparece a lista e o botão **"Aprovei, pode entregar"** (grava `_estudio/conferir_ok.json` e entrega). A aprovação vale para aquele texto: se a escolha mudar, o item volta a travar.

## 2026-10-11 — Snapper do Jets debaixo do logo do Giants (escolha isolada)
- O agente de escolha **viu** o problema ("Jets uniform visible, not generic") mas escolheu mesmo assim: era a última tentativa, com a regra "escolha a mais próxima com conferir", e ele **não sabia** que o logo do Giants (outro asset, 00-02-f) ia por cima. O `conferir` não trava nada e o QA não olha conteúdo, então passou.
- Raiz também no storyboard: pediu snap "generic, no logos" e pôs o sticker do Giants em cima. Cena com logo de time pede asset **daquele time**.
- **Correção:** o pedido de escolha lista os outros assets da cena; regra de coerência nos prompts `escolher_imagem`/`escolher_video` e em [[Critérios de Escolha]]. Asset trocado por Casey Kreiter (long snapper do Giants) em posição de snap.

## 2026-10-11 — Cold open do Every NFL Position: B10, A2 e recorte
- **B10 com a fala cedo:** o rótulo ("19 years") entrava no tempo da palavra, mas o card só desliza depois de terminar a entrada (~1 s) → texto por cima da foto ainda no centro. **Editor:** o 1º rótulo do B10 agora espera o fim do deslizamento (−0,1 s). Para o rótulo não ficar atrasado em relação à fala, o card do B10 deve entrar ≥ 1,5 s antes da palavra do rótulo.
- **A2 que se completa ("every NFL position" → "…, explained"):** o editor trocava pela frase inteira, que encolhia de 150 para ~100 px num salto. **Agora:** quando a frase nova começa com a anterior, a anterior fica parada (mesmo tamanho e lugar) e só o resto entra na linha de baixo.
- **Recorte:** a troca automática pegou o candidato #2 (sapato do Dempsey cortado no topo e borrado); o #1 (inteiro no pedestal) recortou bem. Recorte precisa do objeto **inteiro** no quadro.
- **Estúdio:** "Rodar de editar" com observação pulava a edição ("já aprovado") e a observação se perdia. Agora a edição renderiza de novo se for pedida (`--de editar`) ou se `cenas.json`, `plano.json`, `manifesto.json` ou o `gerar_ae2.py` forem mais novos que o QA aprovado. A observação ainda **não** chega à edição (só ao storyboard e à escolha).

## 2026-10-11 — Três "Rodar" no mesmo bloco ao mesmo tempo (Every NFL Position, bloco 00)
- Durante a checagem do claude (~17 s antes da 1ª etapa) o `estado.json` ainda dizia "parado", e o painel liberou o botão. Saíram 3 rodadas às 22:34: os três storyboards editaram o mesmo `cenas.json` (um quebrou com `_avisos_aceitos` dentro do `"trocar"`), as buscas apagaram a pasta `_baixando` umas das outras e os candidatos ficaram de um plano diferente do final (ex.: `00-01-b` era logo dos Saints no plano e foi buscado como a chuteira do Dempsey).
- **Correções:** (1) o painel decide "rodando" pelo **pid vivo**, não pelo `estado.json`; (2) o `rodar` se recusa a começar se já há outra rodada viva no bloco e só apaga o pid se for o seu; (3) o painel recolhe rodadas que terminaram (zumbis faziam o pid parecer vivo e o painel respondia 409 para sempre); (4) o storyboard aceita `_avisos_aceitos` dentro do `"trocar"`.
- A busca misturada foi para `blocos/00/_backup_busca_misturada_2026-10-11/`; o storyboard final (22:36:31) ficou e o bloco volta a rodar a partir da busca.

## 2026-10-11 — Estúdio parou no storyboard: `claude` velho e login vencido
- O Estúdio chama o `claude` do npm (`/opt/homebrew/bin/claude`), não o do app desktop. Ele estava na 2.1.133 e o `claude-opus-5-5` exige 2.1.280 ou mais nova → "API Error: 400 … does not support this model". Resolvido com `claude update` (2.1.296).
- Depois disso o login do terminal tinha vencido (o Arthur refez com `claude /login`). O Estúdio usa o `CLAUDE_CODE_OAUTH_TOKEN` do `Estudio/.env`, que continuava valendo.
- **Agora o `rodar` checa o claude antes da 1ª etapa** (`motor_claude.checar_claude`): faz uma chamada mínima com cada modelo das etapas pedidas, roda `claude update` sozinho se a versão for velha e, se falhar, para em "checagem do Claude" com o que fazer. Teste à mão: `python -m estudio checar`. Detalhes em [[Estúdio (orquestrador)]].

## 2026-10-11 — Estúdio: 1º bloco do começo ao fim (Lambeau Field) + painel
- O bloco 02 do Every NFL Stadium saiu do roteiro até a prévia aprovada no QA pelo `python -m estudio rodar`, só com bancos livres. Ficaram **28 imagens e 0 vídeos**: Pexels e Pixabay não têm nada do Lambeau, e 4 vídeos viraram foto. O formato sem vídeo de jogo fica mais parado; vale planejar mais F (cenas que evoluem), mapas e números.
- **O Whisper erra nomes próprios** ("Lambeau" virou "Lambo") e o título ia sair errado. Agora o `nome` vem do roteiro e a forma transcrita vai em `"nome_fala"` (`compilar_cenas.py`, backup `_backup_compilar_cenas_antes_nome_fala.py`).
- **No `claude -p` com Opus, `MAX_THINKING_TOKENS` não limitou o raciocínio:** a 1ª volta do storyboard gerou 55 mil tokens de saída. O que funciona para cortar é `--effort`.
- Escolhas em paralelo podem pegar a **mesma foto** para dois cards (02-13-c e 02-15-c). Agora o Estúdio confere e refaz o repetido.
- A API do Fish Audio ficou sem crédito (HTTP 402 no `s2.1-pro`). O bloco 02 usou `--modelo s2.1-pro-free` (decisão do Arthur, "por enquanto").
- → [[Estúdio (orquestrador)]]

## 2026-10-11 — YouTube removido do sistema (IP do Arthur acusado de fraude/proxy)
- Durante o modo sombra do Estúdio e as rodadas valendo dos blocos 01–02 do Every NFL Stadium, as chamadas automáticas ao YouTube (buscas, folhas de storyboard, detalhes de 0,5 s, downloads) fizeram o Google bloquear o IP e acusar o Arthur de fraude e uso de proxy. Foi o 2º bloqueio (o 1º foi em 2026-10-06), mesmo com o freio (`yt_seguro.py`: 1 chamada por vez, pausa) e o "PO token" que imitava navegador. O erro foi rodar volume grande de automação contra o YouTube, que proíbe isso nos termos.
- **O Arthur pediu para excluir toda e qualquer busca no YouTube.** Feito:
  - `buscar.py`: vídeos só de bancos livres, e `"youtube"` num card é ignorado.
  - `fontes.py`: a busca no YouTube foi apagada.
  - `finalizar.py` e `detalhar_video.py`: recusam qualquer endereço do YouTube.
  - `achar_lance.py`: desativado.
  - `yt_seguro.py`: virou uma trava que sempre recusa.
  - `config.json`: vídeo = `[["pexels","pixabay"],["commons","archive"]]`.
  - yt-dlp, yt-dlp-ejs e bgutil (PO token) desinstalados; `bgutil/`, `_youtube/` e `_cache/yt_quadros/` movidos para `ProFootball_backups/youtube_removido_2026-10-11/`.
  - Estúdio: ignora candidatos de YouTube salvos em blocos antigos e refaz a busca desses assets nos bancos livres.
  - Skill, subagentes, CLAUDE.md, README e prompts atualizados. Backup de tudo: `ProFootball_backups/antes_remover_youtube_2026-10-11.tar.gz`.
- **Consequência para o formato:** transmissão de jogo, lance específico, coletiva e bastidor de time não existem em banco livre. O storyboard agora planeja foto, texto, número (G2/G3) ou mapa para esses momentos, e vídeo só para plano genérico ou imagem de época.

## 2026-10-11 — Estúdio: escolha de assets fora do subagente (~6× menos tokens)
- Linha de base medida nos transcripts: o `escolher-assets` gastava ~47 mil tokens equivalentes por asset (~720 mil por bloco). A maior parte era o histórico, relido a cada passo, com as folhas de contato dentro.
- O Estúdio (`/Users/arthur/Canais/Estudio`) faz uma chamada `claude -p` isolada por asset e fica em ~7.500 por asset (modo sombra em 14 blocos do "Who Makes the NFL Possible"). O Arthur conferiu as divergências e a qualidade não caiu.
- **No `claude -p`, o raciocínio é o que mais gasta:** sem `--effort low` + `MAX_THINKING_TOKENS=0`, o Sonnet gerava até 8,7 mil tokens de saída para responder um JSON de 50. Com eles, a saída caiu para ~170.
- O `finalizar.py` sem `--asset` baixa de novo todos os assets do bloco. Para refazer só alguns, passe sempre os ids.
- O `claude` do terminal tem um login separado do app desktop: para rodar sem conversa, use `claude setup-token` → `Estudio/.env`.
- **Busca nova em card com bancos livres na frente** (`"fontes": ["pexels", "pixabay", "youtube"]`): os livres "bastam" com qualquer coisa genérica e o YouTube nunca roda. A busca "Soldier Field colonnade" voltou praia e floresta (01-02-c). Agora `buscar.py --fontes youtube` força a fonte, e o Estúdio usa isso na 1ª busca nova de um card de vídeo assim.
- **Tarja preta passava pelo `cropdetect=24`**: vídeo comprimido tem ruído na barra. Com limite 40 e o corte que mais se repete, pegou o 640×480 → 640×360 do 01-10-e. Quem avisou foi a conferência pelo Haiku.
- **Asset que não existe em vídeo** (colunas do Soldier Field de perto): reaproveitar o drone de outro card (`reusar_candidato.py`) e pedir o trecho em que o assunto aparece melhor (`estudio escolher --asset ID --obs "..."`).
- Valendo (9 vídeos do Every NFL Stadium bloco 01): ~21 mil tokens por vídeo, contando buscas novas, folhas de detalhe e conferência. Ainda menos da metade do subagente.
- → [[Estúdio (orquestrador)]]


## 2026-10-10 — Narração: DarkPlanner → Fish Audio
- A narração passa a ser gerada pela **API do Fish Audio** (pedido do Arthur). Mesmo comando: `buscador_assets/scripts/gerar_narracao.py <pasta do bloco>` → grava `narracao.mp3` no bloco, sempre um bloco por vez.
- Chave/voz/modelo em `ProFootball/.env.fishaudio` (`FISH_API_KEY`, `FISH_VOICE_ID` = reference_id do modelo de voz, `FISH_MODEL`, padrão `s2.1-pro`). `--vozes [busca]` lista vozes, `--uso` mostra créditos, `--speed`/`--modelo` ajustam.
- O Fish Audio não devolve SRT (nada no pipeline usava; a transcrição continua sendo feita na etapa de assets). A resposta é síncrona (sem job/status).
- Voz escolhida: `fb7ec16ca51a45a5a4db881244d7990a` ("WNBA VOICEOVER", inglês). **Crédito de API é separado do crédito da plataforma**: com saldo de API 0 o `s2.1-pro` dá HTTP 402; o `s2.1-pro-free` (gratuito para desenvolvedores) funciona (`--modelo s2.1-pro-free`).
- Versão antiga guardada em `gerar_narracao_darkplanner.py` (chave em `.env.darkplanner`).

## 2026-10-10 — Smithsonian estava desligado
- Sem `SI_API_KEY`, usava a `DEMO_KEY` (10 buscas/hora); estourava e devolvia 0 **sem avisar** — por isso só 7 candidatos em todos os vídeos e o "0% de escolha" no [[Rank de Fontes]] não mede a fonte de verdade. Agora lê a chave do `ProFootball/.env.fontes` e, **sem chave, fica fora da busca** (volta sozinho quando a chave for colocada). Chave grátis em api.data.gov/signup.

## 2026-10-10 — Serper (Google) por último
- O Serper é pago: passou para a última camada de todas as imagens e só entra com menos de 8 candidatos bons das fontes grátis (`fontes_pagas` no `config.json`). Teste "Lambeau Field": 8 candidatos de DuckDuckGo + Commons, nenhum crédito gasto. → [[Rank de Fontes]]

## 2026-10-10 — Busca sem repetição (projeto inteiro)
- Medido nos 4 vídeos: 15% dos previews do YouTube eram de vídeo já aberto em outro card; 9% das imagens baixadas, repetidas; 305 de 314 cards de vídeo sem `"fontes"` iam a 5 lugares (até 6 folhas) e 100% dos vídeos escolhidos eram do YouTube.
- Agora: cache global (`buscador_assets/_cache/`: buscas 7 dias, imagens, quadros do YouTube), fontes em camadas que só descem se faltar, e cada fonte para quando já tem o bastante. Vídeo sem `"fontes"` = YouTube primeiro; livres só se bloquear ou faltar. Mesma busca repetida: 10,6 s → 0,9 s. → [[Rank de Fontes]]
- Backups: `buscador_assets/_backup_antes_rank_fontes/`, `_backup_antes_cache/`.

## 2026-10-10 — Rank de fontes da busca
- Medido nas escolhas de 10-02 a 10-09: busca geral da web deu 138 de 153 imagens escolhidas; Openverse e Smithsonian, zero; Commons nunca serviu para recorte. → [[Rank de Fontes]]
- Busca agora em camadas (Google + Commons primeiro; DuckDuckGo/Pixabay só se faltar; Openverse/Smithsonian por último). Refazer a medição depois de 2–3 vídeos com o Google.

## 2026-10-10 — Google Imagens (Serper)
- Busca de imagens do Google pela API do Serper, na frente do DuckDuckGo (que limitava a taxa). DuckDuckGo segue de reserva. → [[Sistema Buscador de Assets#Google Imagens pelo Serper (2026-10-10)]]

## 2026-10-10 — Pixabay para fotos
- Pixabay (API) adicionado como fonte de **foto** além de vídeo; mesma `PIXABAY_API_KEY`. Fotos chegam no máx. a 1280 px (lado maior) → bom para genérico, não para jogador. → [[Sistema Buscador de Assets#Fotos do Pixabay (2026-10-10)]]

## 2026-10-09 (4) — Escolha de assets do Every NFL Stadium Explained, bloco 01 (só imagens)
- `reusar_candidato.py` copiava o candidato de imagem mantendo `"arquivo": "01.jpg"`, que no destino apontava para o 01 **do próprio destino** (o 01-05-f saiu com a foto errada). Corrigido: agora copia o arquivo como `NN.jpg` no destino.
- Resultados da Vecteezy (`static.vecteezy.com`) vêm com marca d'água espalhada, invisível na folha de contato, só aparece no PNG final. Evitar; "Doric column png transparent" só trouxe Vecteezy (e nem eram dóricas). Funcionou: "Greek Doric column isolated on white" + corte manual de uma coluna.

## 2026-10-09 (6) — Onde foi o gasto da sessão do bloco 01 (Every NFL Stadium)
- Medido nos transcripts (peso: cache lido 0,1×, cache escrito 2×, saída 5×). Conversa principal ≈ 2,65 M de custo relativo; subagentes: storyboard 0,36 M, escolher-assets 0,35 M. **A conversa principal custou ~4× os dois subagentes juntos.**
- 68% do custo da principal é **reler o contexto** a cada chamada (18 M de tokens lidos do cache). O contexto já começa em **~69k** só com instruções e ferramentas, e chegou a 236k.
- Por etapa: **desenvolver PO token + vídeos livres = 52%** (51 chamadas com 150–236k de contexto); dividir o roteiro = 12% (reescrevi o roteiro inteiro de 30 tópicos à mão: saída custa 5×); storyboard + busca + correções = 11%; conectar a API de narração = ~15%.
- Lições: (1) mexer no sistema numa sessão separada da produção; (2) roteiro longo chega como arquivo (`roteiro.txt`), não colado no chat; (3) uma sessão por bloco continua valendo: o custo de cada chamada cresce com o tamanho da conversa.

## 2026-10-09 (5) — PO token no YouTube e vídeos de bancos livres
- O YouTube bloqueou ("not a bot") logo nas primeiras chamadas do bloco 01 de [[Every NFL Stadium Explained]]: o IP já estava marcado, não foi excesso nosso. Arthur pediu duas melhorias: PO token e fontes de vídeo fora do YouTube. Detalhes em [[Sistema Buscador de Assets]].
- PO token: plugin `bgutil-ytdlp-pot-provider` + gerador em `buscador_assets/bgutil/server`, ligado no `yt_seguro.py`. Ainda **não testado contra o YouTube** (IP bloqueado na hora); testar na próxima busca pelo `yt_seguro`.
- Vídeos livres: Pexels, Pixabay (precisam de chave grátis em `.env.fontes`), Wikimedia Commons e Internet Archive. Com o YouTube bloqueado, o `buscar.py` grava os livres e marca `youtube_pendente`.
- **Wikimedia devolve 429** no `upload.wikimedia.org` com 6 conexões ao mesmo tempo ou ao baixar o arquivo original. Usar só as versões convertidas e uma conexão; depois do 429 o bloqueio dura algum tempo.
- **Recompilar o `cenas.json` renomeava os assets** (01-10-e virou 01-10-a): os cards não guardavam id e o compilador inventava letras novas, deixando `escolhas.json`/`manifesto.json` apontando para ids que sumiram. Recuperei casando a descrição com `_work/candidatos/*/candidatos.json`. Corrigido: o `compilar_cenas.py` agora grava o id em cada card do `cenas.json` (inclusive sticker e lateral) e recompilar mantém os ids (backup `_backup_compilar_cenas_antes_id_fixo.py`).
- Erro meu: testei o plugin chamando `.venv/bin/yt-dlp` direto, fora do `yt_seguro`, com o IP bloqueado. Toda chamada ao YouTube, até teste, passa pelo `yt_seguro`.

## 2026-10-09 (3) — Storyboard do Every NFL Stadium Explained, bloco 01
- `storyboard.py` quebrava com cards que têm `"sticker"` (o plano de edição guarda como lista `[asset, t]`). Corrigido pelo subagente; backup `buscador_assets/scripts/_backup_storyboard_antes_sticker_lista.py`.
- Mapa gerado com `"vista"` começando em "-" (longitude oeste): o `compilar_cenas.py` passa o valor sem "=", e o argparse lê como opção. Contorno usado: espaço antes do sinal (`" -92.5,37.0,-83.5,44.0"`). Corrigido no mesmo dia: o compilador agora passa `--chave=valor` (backup `_backup_compilar_cenas_antes_vista_igual.py`); o espaço não é mais necessário.
- O gerador de mapa não desenha os Grandes Lagos (os estados cobrem o Lago Michigan).
- A citação do G1 tinha sido escrita de memória pelo subagente e não batia com o NPS. **Conferir sempre o texto de `"citacao"` na fonte** antes da busca. Texto oficial usado: "National Historic Landmarks (NHLs) are historic properties that illustrate the heritage of the United States." (nps.gov).

## 2026-10-09 (2) — Narração gerada pela API do DarkPlanner
- A narração agora pode ser gerada por script: `buscador_assets/scripts/gerar_narracao.py <pasta do bloco>` lê o `roteiro.txt` (pula linhas `#`), grava `narracao.mp3` no bloco e as 3 SRTs em `_work/narracao_srt/`. `--vozes` lista as vozes, `--uso` mostra o limite do dia. Docs: https://app.darkplanner.com.br/api-docs.
- A chave fica em `ProFootball/.env.darkplanner` (`DARKPLANNER_API_KEY=`, e a voz padrão em `DARKPLANNER_VOICE_ID=`). **Voz do canal: Clark - The Trusted Narrator & Storyteller** (`71a5254a-9a3c-4d30-ab07-47e9d2764a42`), escolhida pelo Arthur. Nunca colar a chave no chat.
- O Cloudflare do DarkPlanner devolve **403 "error code: 1010"** para o User-Agent padrão do Python: é preciso mandar um User-Agent de navegador (já está no script).
- **Regra do Arthur: a narração é sempre gerada tópico por tópico** (um job por bloco), nunca o roteiro inteiro de uma vez.
- Plano Pro: 50 áudios por dia, até 150 mil caracteres por áudio, 10 requisições por minuto. São 982 vozes; pausas no texto com `<break time="1.5s"/>`.

## 2026-10-09 — Análise do canal FooDiscover (títulos e thumbs)
- Analisados 50 vídeos e 24 thumbs do @Foodiscover pelo vidIQ. O que mais pesa é o tamanho do tema: categorias amplas ou com marcas (café, chocolate, frutas, água) passam de 600 mil; temas de nicho (omelete, donut, ponto da carne) ficam entre 8 e 30 mil.
- Títulos curtos no molde "Every/All ___ Explained". Emoji e tema repetido derrubam. Thumb padrão: grade 4×2 com o nome de cada item, fundo claro, sem título na imagem, misturando itens conhecidos e 2 ou 3 estranhos. Detalhes em [[Canal de Referência FooDiscover]].
- **Decisão do Arthur:** os clusters de tema T6 (prato/aspecto específico), T7 (luxo, "melhores do mundo") e T8 (bastidores/história) estão descartados. Os vídeos novos saem só de T1 a T5.
- Pesquisa de temas NFL no vidIQ: a série "Every Team" do NFL Throwback (3,8–17,5 M) prova o formato catálogo; "football explained" tem 170 mil buscas/mês com concorrência baixa. 5 títulos escolhidos em [[Banco de Temas]].
- Roteiro: o FooDiscover escreve fichas (nome → o que é → origem do nome → história → curiosidade), começa pelos itens famosos e fecha no mais raro. Nossa escrita é melhor (números, fechos fortes), mas os itens eram funções que ninguém reconhece. Molde novo em [[Análise de Roteiro]].

## 2026-10-08 (2) — Texto sobre o card ficava embaixo do card seguinte
- Bloco 02 (F8, fábrica + mapa de Ohio): o mapa cobria o "5,300 PEOPLE". No After a camada criada por último fica por cima, e o `gerar_ae2.py` criava o texto `"sobre"` logo depois do próprio card, antes do mapa. O Arthur resolveu subindo o texto e a caixa acima do mapa no After; renderizei o projeto dele direto do After aberto (sem reabrir o `.aep`, que estava com alterações não salvas).
- Correção no editor: os textos `"sobre"` de um estado agora são criados **depois de todos os cards** do estado (vale para F8, C2, D5, D6, F9). Backup: `editor_ae/_backup_gerar_ae2_antes_sobre_por_cima.py`. Bloco 09 (mesmo caso, "SINCE 2014") remontado.
- O QA não pega texto coberto por outro card. Novo achado no mesmo quadro do 09: o rótulo de cidade do `gerar_mapa.py` passa da borda ("NEW YORK CI") — o gerador não confere se o nome cabe na imagem.
- Antes de rodar o render padrão (que reabre o `.aep`), conferir se o projeto aberto está com alterações não salvas (`app.project.dirty`).

## 2026-10-08 — Fundo novo com adesivos em todos os blocos
- O Arthur pôs no bloco 01 (no After) uma imagem de papel com adesivos nos cantos, a 50% entre o "Fundo" e a "Textura papel". Li os valores direto do projeto aberto por script (.jsx que lista camadas, transformações e efeitos) e levei para o editor: `FUNDO_IMAGEM` em `gerar_ae2.py` + bloco novo em `montar_modelo2.jsx`. Ver [[Identidade Visual]].
- Blocos já aprovados foram remontados sem QA: `SEM_QA=1 editor_ae/editar_bloco.sh <bloco> NN <versao>` (opção nova). Backups: `_backup_gerar_ae2_antes_fundo_imagem.py`, `_backup_montar_modelo2_antes_fundo_imagem.jsx`, `_backup_editar_bloco_antes_sem_qa.sh`; projeto do Arthur salvo em `blocos/01/edicao/bloco_01_v2_arthur_fundo_novo.aep`.
- Remontar um bloco **sobrescreve o `.aep`** dele: antes de remontar, copie qualquer projeto que o Arthur tenha editado à mão.

## 2026-10-07 — "Obsidian" virou "pasta de conhecimento"
- A pedido do Arthur, a base de notas passou a se chamar **pasta de conhecimento** e a pasta foi renomeada de `obsidian/` para **`conhecimento/`** (notas em `conhecimento/Pro Football/`).
- Atualizados: CLAUDE.md, skill `buscar-assets`, agentes `escolher-assets` e `storyboard`, comentários do `editor_ae/gerar_ae*.py`, Índice e este Log. Ficaram como estavam: arquivos `_backup_*`, o caminho antigo do iCloud citado na entrada de 2026-10-05 e as permissões `mcp__obsidian__*` no settings (nome técnico da ferramenta).
- Nada no pipeline depende do app Obsidian: tudo é lido e escrito direto nos `.md`.

## 2026-10-06 (2) — Pouca variedade de cenas → subagente `storyboard`
- Medido em [[Who Makes the NFL Possible]]: 157 estados, só **15 das 60 variações**; B 39%, C1 18,5%, A 18,5% (76% juntos); 4–7 layouts por bloco; 19 layouts prontos no editor nunca usados. Causa: planejamento pelo caminho seguro (um card por frase), sem nada obrigando a variar; o compilador só avisava texto demais.
- **"60 no banco × 34 no editor" é só nome**: as 60 variações funcionam; 26 delas são um layout genérico + campo (`sobre`, `troca`, `acima`, `sticker`, `mapa`, vários `estados`…). Ver tabela em [[Biblioteca de Cenas]].
- Novo `buscador_assets/scripts/storyboard.py`: storyboard em Markdown (tempo, narração, variação, assets com tempo na tela, texto) + métricas e AVISOS. Medida dos 14 blocos: 5–9 variações, card único 30–67%, 10–17 assets/min.
- Novo subagente **`storyboard`** (pedido do Arthur): planeja um bloco por vez, compila, mede e corrige antes da busca; devolve só o resumo. CLAUDE.md, skill e [[Da Narração às Cenas]] atualizados.

## 2026-10-06 — Freio no YouTube e limite de subagentes
- **Falso alarme do QA com cards de gramado** (bloco 13): quase todos os cards eram campo verde visto de cima (All-22, end zone, treino) e o QA mediu ritmo 2,8/min e texto solo 0%, mas a prévia troca normal (9 frames conferidos) e tem o texto final. O detector não separa cards parecidos em sequência. Candidato a ajuste no `qa_bloco.py`.
- **Busca ficou lenta com a fila única** (Arthur): cada preview baixava até 5 min do vídeo em 360p (2+ min) e segurava a fila. Troquei pelo **storyboard do YouTube** (miniaturas da barra de progresso): ~7 s por vídeo, vídeo inteiro coberto, folha legível. Backup: `_backup_antes_yt_seguro/buscar_antes_storyboard.py`.
- Implementado `buscador_assets/scripts/yt_seguro.py` (ver [[Sistema Buscador de Assets]]): 1 chamada ao YouTube por vez no Mac, pausa entre chamadas, deno, parada automática de 2 h no bloqueio (código 75). Testado: 2 chamadas simultâneas saíram em 8 s e 16 s (fila); bloqueio simulado → código 75.
- `deno` instalado (Homebrew) a pedido do Arthur; o aviso "No supported JavaScript runtime" sumiu. (O Node 25 já existia e também serviria com `--js-runtimes node`.)
- `buscar.py --refazer` não perde mais candidatos; pula vídeos quando bloqueado.
- **Troca (B6) com gatilhos muito próximos reprova no QA** e o `compilar_cenas.py` não avisa: 02-05-b ("sew"→"turn", 1,3 s) e 08-02-c (1,7 s). Ao planejar troca, conferir ≥1,8 s entre gatilhos na transcrição; correção = mover o `t` da troca no `plano_edicao`. Candidato a aviso no compilador.
- Regra: **no máximo 3 subagentes ao mesmo tempo**. Erro 529 da API (sobrecarga do servidor) derrubou 5 subagentes seguidos; retomar na hora fazia cair de novo, esperar ~10 min funcionou.
- Bloqueio não tem a ver com a conta do Arthur: o yt-dlp é anônimo (sem cookies). Trocar de rede liberou na hora.

## 2026-10-05 (9) — Buscas do "Who Makes the NFL Possible" (subagentes por bloco)
- **Um subagente por bloco** (pedido do Arthur): cada `escolher-assets` busca e escolhe só o seu bloco; nada de encadear blocos num processo só. Limite prático ~5 buscas ao mesmo tempo.
- **Laço `until ! pgrep -f "buscar.py .*blocos/09"` nunca termina**: o pgrep acha a própria linha de comando do laço. Ficaram 4 shells presos por 2 h após o subagente cair por limite de uso. Usar `pgrep -f "[b]uscar.py"` ou esperar a notificação da tarefa.
- Subagentes que caem por limite de uso podem ser **retomados** (SendMessage) com o contexto intacto; a busca em segundo plano deles continua e termina sozinha.
- **YouTube bloqueou o IP** ("Sign in to confirm you're not a bot") depois de ~8 h com 5–6 buscas/downloads em paralelo. Bloqueia download, folha e até leitura de título. Não é a conta do Arthur (yt-dlp anônimo, sem cookies). Saída: o Arthur trocou de rede. Com bloqueio, `--refazer` de vídeo apaga os candidatos e volta vazio: backup antes. Depois de liberar, baixar **um bloco por vez**.
- Outros achados dos subagentes: `u2net_human_seg` recorta árbitro (listras pretas) muito melhor que o rembg padrão; rembg estraga logo com letras pretas grossas (usar flood fill das bordas); vídeo oficial "NFL Rules Changes for the 2025 Season" (4BvfF_jLltU) tem o Art McNally GameDay Central (285–316 s) e replay assist (346–361 s); `finalizar.py --asset` não restringe ao asset (refaz o título do bloco junto).
- macOS não tem `timeout`: `timeout 7200 buscar.py ...` saiu na hora com código 127. Rodar sem ele.
- `buscar.py --refazer` **substitui** os candidatos do asset (alternativas razoáveis se perdem): copiar `_work/candidatos/<id>` antes.
- Pessoa histórica sem foto limpa (Val Pinchbeck): frame de documentário oficial (NFL Films "The Making of the NFL Schedule", youtube eaVwY3ptryw, cobre quase todo o tópico do calendário).
- `detalhar_video.py` falhando no download → baixar o vídeo inteiro com yt-dlp e achar cortes com ffmpeg `select=gt(scene,0.25)`.
- Bastidores de arbitragem (relógio, cabine de replay, assistentes de boné bordô) quase não têm vídeo da NFL na web: melhores fontes foram The Verge "Inside the control room", CBS Sunday Morning e o vídeo da VOGO no Fiesta Bowl (universitário → marcar conferir).

## 2026-10-05 (8) — Narração num áudio só, dividida em blocos
- *Who Makes the NFL Possible* chegou com a narração inteira num mp3 (894 s, 14 tópicos). Divisão: transcrever o áudio todo, achar o título de cada tópico na transcrição e cortar no **silêncio real** (`ffmpeg silencedetect`, -40 dB, ≥0,25 s) logo antes dele, com **0,2 s de folga** antes da fala.
- O Whisper às vezes marca o título colado na palavra anterior (folga 0) e às vezes "engole" o *The* do título: não use o tempo do Whisper para cortar, use o silêncio. Com 0,1 s de folga o *The* do bloco 05 ficou a 0,05 s do corte; 0,2 s ficou seguro.
- Scripts reutilizáveis na produção: `_completo/achar_cortes.py` (acha títulos) e `_completo/dividir.py` (corta áudio + `roteiro.txt` de cada bloco).

## 2026-10-05 (7) — Falsos alarmes do QA corrigidos
- **"Rótulo pequeno" (50–62 px com o nome em ~90 px):** a medida só olhava texto acima ou à direita dos cards. O nome do B10 (à esquerda) não entrava, e ruídos entravam no lugar (caixas de 84×44 px dentro do vídeo, pedaços do globo). Agora conta os 3 lados, exige formato de palavra e persistência de 0,5 s. Teste: 50–62 → 96 px; bloco 01: 120 px.
- **"Texto solo pequeno" e "palco vazio" com o globo (M5):** quando o detector perde o card, os textos de dentro do vídeo viravam "texto solo". O QA agora mede no pixel quanto da tela não é papel (uma passada por vídeo) e usa isso nos dois checks.
- `referencia.json` regenerada (só o rótulo mudou). Backups: `qa/_backup_medidas_antes_rotulo.py`, `qa/_backup_referencia_antes_rotulo.json`.
- Teste final: leva4 sem nenhuma atenção; bloco 01 v12 aprovado sem atenções.

## 2026-10-05 (6) — Documentação de planejamento alinhada ao repertório novo
- [[Da Narração às Cenas]] reescrita: as letras antigas (E, H, I, J da [[Tipos de Cena]]) deram lugar aos códigos da [[Biblioteca de Cenas]], e entrou a tabela **"Que layout usar para cada situação"** (narração → código), cobrindo os 60+ layouts. Regras atualizadas: asset ~4 s (mín. 1,8 s), sequências F, 20–25 assets/min, variedade.
- **B8 corrigido na documentação:** o `acima` funciona em par/trio (vira C4), que foi o caso usado no bloco 01. Só em card único o nome sai cortado (a entrada de 2026-10-02 dizia que o B8 "não existe" de forma geral). Para pessoa + nome em card único: B10 ou B4.
- Skill `buscar-assets` aponta para a tabela de situações.

## 2026-10-05 (5) — Toda a Biblioteca v5–v8 no editor (4ª leva)
- Entraram B9, C9, D7, E5, E6, F8, F9, G2, G3, M3, M5, M6, M7 e T1–T3. Teste feito com os assets do bloco 01 (arquivos de teste apagados depois); QA aprovado (só atenção de tamanho de texto, por causa do globo).
- **Medir no frame cheio corrigiu de novo os relatórios dos subagentes:** no F9 o mapa entra **por cima** da foto (não por baixo); o globo do M5 tem ~85% da altura do card (~670 px, não 30% da tela); no E5 o card fica centralizado; o B9 empilha a partir do alto; o M6 é só um E2 com silhueta.
- Novos geradores (sem IA, dados reais): `gerar_mapa.py --globo` (ortográfico, PNG transparente), `--silhueta` (país cinza + regiões; `--regioes` para províncias), `gerar_tabela.py` (tabela G2 / gráfico de barras G3). No `cenas.json`, "mapa"/"tabela"/"grafico" funcionam em card, troca e lateral.
- Elemento **"lateral"** (bandeira/globo à direita do card): o globo entra rolando (`rot_keys`, suportado agora no .jsx). Um logo largo passava da tela, então agora ele encolhe para caber na margem considerando o zoom.
- **QA:** o detector só reconhece cards retangulares, e card + globo encostado sumia ("palco vazio" falso). O check agora confere o pixel contra o fundo de papel antes de acusar (>8% da tela diferente = há algo em cena).
- T1/T2 já existiam (`"sai"`/`"entra"`). T3 = `"dissolve": true` na troca.
- Backups desta leva: `editor_ae/_backup_gerar_ae2_antes_leva4.py`, `buscador_assets/scripts/_backup_compilar_cenas_antes_leva4.py`.

## 2026-10-05 (4) — Gerador de mapas no estilo do canal (M1/M2/M4)
- `buscador_assets/scripts/gerar_mapa.py` + dados Natural Earth 1:50m em `buscador_assets/dados/` (países 3,1 MB; estados/províncias 2,3 MB; baixados com autorização do Arthur).
- Desenho em PIL, sem bibliotecas de mapa: Albers (EUA) e equiretangular corrigida (países), supersample 2×.
- Card com `"mapa": {...}` no `cenas.json` → o compilador gera o PNG em `assets/mapas/` (nome por hash, reaproveita) e o card vira `arquivo`, fora da busca.
- 1º teste: o rótulo da região e os nomes das cidades se sobrepunham. Agora são 2 passadas (pontos, depois nomes) e cada texto tenta direita/esquerda/acima/abaixo até achar lugar livre.
- Antes disso, os mapas vinham da busca "<cidade> locator map" (Wikipedia: região em vermelho, fora da paleta). Continua valendo como alternativa.

## 2026-10-05 (3) — A4, B11 e G1 no editor + correções do estudo
- **Cortes rápidos dentro do card são do próprio vídeo**, não da edição (Arthur): shorts/reels já vêm editados. Para nós é 1 asset, e a regra dos 1,8 s continua. → Vídeos verticais com cortes internos são bem-vindos. Parte do C8 "troca a cada 1 s" contado pelos subagentes é isso.
- **A4 medido a 30 fps:** a frase some de uma vez, há ~0,17 s vazio e a próxima entra em ~0,1 s. O "fade passando por cinza" que os subagentes relataram era só o frame da entrada. Minha 1ª versão com fade lento gerou palco vazio de 0,8 s no QA. **Medir transições quadro a quadro, nunca deduzir da folha de contato.**
- **G1:** no frame cheio o card fica **centralizado** e a caixa cobre ~60% dele (o relatório dizia card deslocado e caixa de 25%). A caixa é desenhada em PNG pelo gerador (`desenhar_citacao`), com grifo azul por palavra e selo da fonte.
- **B11:** o estado anterior fica na tela, desfoca e sai junto. No After o desfoque age no tamanho original da camada, então o valor é dividido pela escala (18 px na tela). Os textos de trás passaram a sumir porque apareciam desfocados saindo por cima do card novo.
- Bug do B11: camada que entra **depois** do início do foco (ex.: nome acima) recebia chaves fora de ordem e ficava nítida. Agora ela já nasce desfocada/escondida, e as chaves antigas depois do foco são descartadas.
- `montar_modelo2.jsx` agora aceita `blur_keys` em fotos/vídeos (antes só em texto). Backups `_backup_*_antes_v5v8`.
- Compilador e QA tratam o estado antes de um B11 como se durasse até o fim do B11 (senão acusavam tempo mínimo).
- **M2 (gerador de mapas) pendente:** precisa de um arquivo de fronteiras (estados dos EUA/países); não há nada local.

## 2026-10-05 (2) — Layouts C8, D5, D6 e B10 no editor
- `compilar_cenas.py` (orientação), `gerar_ae2.py` (geometria/movimento) e `qa_bloco.py` (categorias) aceitam **C8, D5, D6, B10**. Como escrever cada um no `cenas.json`: [[Biblioteca de Cenas]]. Backups: `editor_ae/_backup_gerar_ae2_antes_v5v8.py`, `buscador_assets/scripts/_backup_compilar_cenas_antes_v5v8.py`.
- C8 não precisou de código novo: a `troca` (B6) já funcionava em qualquer card. Basta usá-la num card do par.
- **Medir no frame cheio mudou os números do relatório do subagente:** o meio do D5 é ~22% mais alto que os laterais (não 5–8%), e o B10 "entra no centro e desliza" só em v8#56 (em #133/#164 o card entra direto à direita).
- O detector junta cards sobrepostos num retângulo só. Para D5/D6, medir à mão no frame.
- 1º render: o D6 com 4 paisagens encolheu para ~430 px e o B10 com foto paisagem deixou o nome com 62 px. Correção: cortar em retrato/quadrado e card do B10 com 740 px, a 220 px da borda.
- No After, a camada adicionada por último fica por cima, então a ordem dos cards no JSON define quem cobre quem (D5: o meio é o 3º; D6: cada novo por cima).
- QA do teste: as falhas de "tempo mínimo" vieram de trocas rápidas de propósito (B6 rápido, ainda sem decisão do Arthur). O aviso de "rótulo 62 px" continuou mesmo com o nome visivelmente maior no frame (~90 px): conferir o que o QA está medindo.

## 2026-10-05 — Biblioteca de Cenas ampliada com 4 referências novas (v5–v8)
Resultado: [[Biblioteca de Cenas]] (+30 variações, marcadas 🆕; novas famílias G documentos, M mapas, T transições).

- Vídeos: v5 Donut, v6 Italian Cuisine, v7 Military Food, v8 Coffee Dessert → 906 cenas (folhas em `Videos Referencias/estudo_cenas/tiras/v5–v8_*.jpg`).
- **Mais usados e que faltavam:** C8 âncora fixa (um card do par fica, o outro troca), D5 sanduíche (card do meio na frente), D6 baralho (cascata de 3–4), B10 card que desliza e abre espaço para o nome, A4 frases encadeadas trocando por fade, mapas com região destacada.
- **Números:** pares sobrepostos subiram para **42%** dos frames com 2 cards (10% em v1–v4); card único 60% paisagem; só texto ~28%.
- Os 4 usam fonte sans arredondada, não Impact: mantivemos a [[Identidade Visual]].
- v8 tem séries de 5–7 cortes de 0,5–1,2 s **no mesmo quadro** (B6 rápido). Isso entra em conflito com a regra "asset ≥ 1,8 s". **Ainda não decidido**: perguntar ao Arthur se a exceção vale para B6.
- As variações 🆕 ainda não existem no `compilar_cenas.py`/`gerar_ae2.py`: até implementar, usar a alternativa indicada em cada linha.
- O segmentador de cenas usado em 2026-10-02 não tinha sido salvo. Agora existe `estudo_cenas/segmentar.py` (vídeo → `segs/vN.npy` → `tiras.py`), e `stats.py` aceita os números dos vídeos (`stats.py 5 6 7 8`).
- Fluxo que economiza contexto: um subagente por vídeo lê as folhas e devolve só as novidades; a conversa principal confere as principais numa grade de frames.

## 2026-10-05 — Kit universal "___ Explained" (para outros canais)
- Pasta `/Users/arthur/Canais/Kit-Explained/` (+ `Kit-Explained.zip`), **separada** deste sistema (o Pro Football não foi alterado; conferido por hash dos 185 arquivos).
- Tudo que é do canal saiu do código para o `canal.json` (nome, idioma, versão do After, cores, fontes, pasta de conhecimento); `novo_canal.py` cria o canal e sugere as cores a partir do logo; `instalar.sh`; `testar_kit.py` (mini-vídeo da Torre Eiffel, passou no QA numa instalação nova com identidade laranja de teste).
- Base de conhecimento virou modelo (`conhecimento/_modelo/`), com a nota nova **Lições Herdadas** (o que aprendemos aqui que vale para qualquer canal). Receitas de NFL ficaram como exemplo em *Buscas que Funcionam*; `achar_lance.py` virou módulo opcional de NFL.
- Mudanças feitas aqui que valem lá também: quando melhorar o editor/QA deste canal, levar para o kit.

## 2026-10-05 — Vault da pasta de conhecimento movido para dentro do projeto
- Antes: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Art`s Vault/` (iCloud). Agora: `/Users/arthur/Canais/ProFootball/conhecimento/` (notas em `conhecimento/Pro Football/`).
- Motivo: o sistema não depende da pasta de conhecimento para rodar, mas o conhecimento (Biblioteca de Cenas, Log, Identidade Visual) vivia fora do projeto e o MCP às vezes estourava o tempo. Agora tudo fica numa pasta só; a pasta de conhecimento continua sendo o leitor.
- Backup do vault antigo: `ProFootball_backups/vault_icloud_2026-10-05.tar.gz`. `CLAUDE.md` e o subagente `escolher-assets` apontam para o caminho novo.
- O vault deixa de sincronizar pelo iCloud.

## 2026-10-04 (3) — Logo largo cortado e título relâmpago (apontado pelo Arthur)
- **Sticker (E4) de logo largo** (IMG Academy, letreiro 7,9:1) era dimensionado só pela altura (26% do card) e saía da tela. Agora o `gerar_ae2.py` limita a largura a 55% do card e, se o logo for mais que 2× mais largo que alto, coloca-o **por dentro** do canto do card. Backup: `editor_ae/_backup_gerar_ae2_antes_sticker_largo.py`. Logos ~quadrados continuam iguais.
- **Título sumindo rápido** (bloco 3: 0,35 s): o narrador emendou "The hours, reaching college..." e eu comecei a 1ª cena em "reaching". Nas outras produções o título fica 1–2 s. O `compilar_cenas.py` agora avisa quando o título fica < 1 s; a 1ª cena deve começar na frase seguinte.
- O QA também não pegou o título curto — candidato a checagem nova.

## 2026-10-04 (2) — Cards cortados para fora da tela (apontado pelo Arthur, blocos 1 e 2)
- **Causa: pixel não quadrado.** Vídeos cortados com ffmpeg (`crop` + `scale`) saíram com SAR quase 1 (1899:1900, 2079:2080, 921:920), e o After interpretou como anamórfico e esticou o card além das bordas (IMG Academy e 7-on-7 no bloco 1; jogo noturno no bloco 2).
- **Correção:** todo crop termina em `,setsar=1` (regra no subagente `escolher-assets`) e o `editar_bloco.sh` agora confere o SAR de cada `.mp4` e corrige antes de montar.
- O QA não pegou: falta uma checagem "card maior que a tela / saindo da borda com a cena parada" (já anotado em 2026-10-03, continua pendente).
- Trocas pedidas: Jamal Adams (astro, não é practice squad) → documentário oficial dos Patriots "Do Your Job: Practice Squad"; VA Brain Bank com cérebros em potes → trecho do mesmo vídeo só com pesquisadoras. ⚠️ O 1º trecho trocado mostrava na tela a ficha de um ex-jogador real com nome e morte — **conferir telas/fichas em vídeos sobre CTE**.
- `buscar.py` de vídeo para em 3 vídeos acumulados: na prática só a 1ª `--consulta` é usada → pôr a melhor busca primeiro.

## 2026-10-04 — Vídeo "The Cost of Becoming a Pro Footballer" (7 blocos numa sessão)
Produção: [[The Cost of Becoming a Pro Footballer]]
- **Áudios numerados ao contrário de novo** (`01_...-7.mp3` = último tópico). Conferir a 1ª linha do `.srt` antes de copiar — já virou rotina.
- **Planejar os 7 blocos de uma vez e buscar em paralelo** funcionou: enquanto um bloco renderiza, outros buscam/escolhem. O After é a fila (um bloco por vez): encadear com `until grep "exited" <saída anterior>; do sleep; done; editar_bloco.sh ...`.
- **Busca demora mais de 30 min** com 3–4 em paralelo (DuckDuckGo dá "malformed headers"/limite): rodar `buscar.py` em segundo plano com `timeout` de 2 h; se cair, rodar de novo continua de onde parou.
- **Palco vazio por texto atrasado** (bug de planejamento): estado A cujo 1º texto tem gatilho bem depois do início da fala deixa a tela vazia (bloco 04: 1,2 s e 1,8 s). Regra: o 1º texto de um estado A entra no início do estado. Corrigido à mão nos `plano_edicao_*.json`; **o `compilar_cenas.py` agora faz isso sozinho** (estado só de texto: 1º texto entra no início do estado).
- **Falso "palco vazio"** em 3 casos: (1) vídeo com céu claro/fumaça no alto (cortar não bastou; trocar por jogo noturno resolveu); (2) logo fino sozinho em LOGOS (Aspen Institute) — resolvido com texto "abaixo" desde o início; (3) card pequeno esperando o 2º na cascata C2 por 4,6 s — real: adiantar o 2º card.
- **Rótulo B5 longo encosta na borda** ("2015–2016"): usar forma curta ("2015–16").
- **Barras de transmissão** (ESPN/NFL Network/FOX) ocupam ~20–25% de baixo: o subagente às vezes deixa passar (03-08-a) — conferir. Nos "FULL Combine Workout" da NFL, replays em câmera lenta não têm barra.
- Subagentes: "heat" traz Miami Heat (usar "hot weather"/"summer"); `reusar_candidato.py` só funciona com vídeo; `buscar.py --refazer` apaga os candidatos antigos; rembg apaga texto fino de logo em fundo branco (usar limiar com PIL); recorte de jogador com técnico atrás leva o técnico junto → trocar de foto.
- Buscas que funcionaram: canal oficial da Exos (preparação para a Combine); "<Jogador> Selected No. X Overall <Time> 2025 NFL Draft" (atravessando o palco); TXFBLIFE para jogo de high school à noite (cortar placar e marca).

## 2026-10-03 — Correções do Arthur nos blocos 2, 8 e 9
- **Esteira (D4) com o último card fora da tela** (blocos 2 e 9): era proposital (copiado das referências), mas o Arthur não quer. O editor agora centraliza a fila e encolhe os cards até todos caberem (margem de 100 px). O limite de zoom também passou a valer para a esteira.
- **Logo largo cortado** (Sleep Number, bloco 8, layout LOGOS): o layout usava altura fixa de 360 px, e um logo de proporção ~4:1 passava de 1920 px. Agora a dupla de logos encolhe para caber.
- O QA não pegou nenhum dos dois: ele procura texto encostado na borda, não card/logo cortado. Possível checagem nova: "card ou logo saindo da tela com a cena parada".
- Backup do editor antes da mudança: `editor_ae/_backup_gerar_ae2_antes_d4_logos.py`.
- Atalho novo no projeto: `editor_ae/editar_bloco.sh <bloco> NN [versao]` (monta, renderiza e roda o QA).

## 2026-10-03 — Gasto da sessão e subagente `escolher-assets`
- Medido no transcript (peso: leitura em cache 0,1×, escrita 2×, saída 5×): **olhar folhas/frames 36% + escolher/baixar 13% ≈ 50%** do gasto; instruções fixas 13%; After 9%; busca 8%; QA 4%; pasta de conhecimento 3%; planejar 2%.
- Causa: imagem aberta fica no contexto e é relida a cada passo; apagar o arquivo não adianta.
- Solução: subagente `escolher-assets` (escolhe + baixa + confere, devolve resumo) + uma sessão por bloco. Ajudantes novos: `reusar_candidato.py`, `conferir_assets.py`.
- Backup do sistema antes da mudança: `/Users/arthur/Canais/ProFootball_backups/sistema_2026-10-03_1907.tar.gz` (scripts, skill, CLAUDE.md, identidade, planos, notas da pasta de conhecimento, lista de pacotes; sem vídeos/áudios/.venv).
- Próximo vídeo: comparar o gasto com este.

## 2026-10-03 — Blocos 2 a 10 do vídeo reformulado (um bloco por tópico)
Produção: [[How Elite NFL Players Actually Work]] · cada tópico vira um bloco separado em `blocos/NN/` (o Arthur junta manualmente); prévias copiadas para `edicao/previa_bloco_NN.mp4`.
- **Narrações chegaram numeradas ao contrário** (`01_audio 10.mp3` = último tópico): conferir a 1ª linha do `.srt` de cada áudio antes de copiar.
- **Planejar todos os blocos primeiro e buscar em paralelo** (2–3 buscas ao mesmo tempo) enquanto um bloco renderiza no After economiza horas.
- **Download falha se o início do trecho passa da duração do vídeo** (yt-dlp: "Error configuring the trim filter"). Ao reaproveitar um vídeo de outro asset, conferir a `duracao` no `candidatos.json`. Downloads do YouTube também falham por acaso: rodar `finalizar.py --asset` de novo resolve.
- **Layout B8 (nome acima) não existe no editor**: o nome saiu cortado no topo (QA pegou "texto cortado na borda"). Usar B5 (rótulos ao lado) para pessoa + número.
- **QA "texto na borda" ajustado**: só reprova se aparecer em ≥ 2 frames seguidos e com altura ≤ 220 px; um card saindo da tela era lido como texto. Continua reprovando o erro real da v6 antiga. Backup: `editor_ae/qa/_backup_qa_bloco_antes_borda.py`.
- **Texto demais** (bloco 4: 43% do tempo só com texto) → trocar cenas de texto por card de vídeo com rótulos (B5) ou sobre (B).
- Assets que não existem e foram substituídos (marcados "conferir"): treino de 45 min dos Broncos no SB50 (→ campo de Stanford), iPad dos Bucs 2011 (→ sala de filme dos Ravens), fotos impressas do sideline (cena virou só o tablet), câmara hiperbárica do Wilson (→ a do LeBron), pesagem pós-treino (→ dietista dos Rams), coletes GPS em NFL (→ futebol/soccer).
- Fontes boas: canais oficiais dos times (OTAs, cozinha/nutrição dos Giants/Commanders/Patriots, vestiário), comerciais oficiais da Sleep Number × NFL, NFL Mental Health series.

## 2026-10-03 — Vídeo reformulado: tópico 1 "The Offseason Program"
Produção: [[How Elite NFL Players Actually Work]] (pasta `-v2`) · 56 s, 14 cenas, 18 assets · QA ✅ (1 atenção).
- **Destaques oficiais de OTA dos times** ("2024 OTA Practice Highlights | <Time>", "<Time> OTAs Highlights", "Mandatory Minicamp Highlights") são a melhor fonte para tópicos de treino: limpos, sem narração, e um vídeo só alimenta vários cards. Buscas genéricas ("NFL OTAs catch receiver", "offensive line drills OTAs") trouxeram vídeos de celular, universitários (Notre Dame) e tutoriais.
- Reaproveitar o vídeo de outro asset: acrescentar o candidato no `candidatos.json` do asset de destino (cópia da entrada, novo `n`) e escolher `{"n": X, "inicio": Y}`. Hoje é manual.
- **Recompilar o `cenas.json` depois que o `plano.json` existe gera ids novos** (o compilador nunca reaproveita ids) e quebra o `escolhas.json`. Para ajustar só um gatilho, editei direto o `edicao/plano_edicao_01.json` (e o `cenas.json`, para registro).
- **Sobreposições de canal** (rótulo "2 DUMBBELL INCLINE PRESS" da Men's Health, botão "SUBSCRIBE" dos Chargers) não aparecem na folha de 8 em 8 s: sempre conferir frames do trecho final baixado.
- QA "palco vazio" deu **alarme falso** com um card de céu claro (bola no ar), que se confunde com o fundo de papel. Resolvi começando o clipe 1 s depois.
- Sala de reunião de time da NFL: não há foto livre; usei uma da Ohio State (marcada para conferir).
- Render pela fila do After: o `osascript` estourou o tempo do AppleEvent (-1712), mas o render continuou; basta esperar o log `log_render_*.txt`.

## 2026-10-03 — Decisão: direitos autorais (clipes da NFL)
- Arthur decidiu **manter o uso atual** de clipes de transmissão e fotos (trechos curtos, sem áudio, recortados em cards). **Só mudar se começarem problemas no canal** (reivindicações/strikes).
- Se acontecer: (1) cortar/desfocar o trecho reivindicado pelo YouTube Studio; (2) criar um limite de clipes da NFL por minuto no QA; (3) priorizar fotos livres e material não-NFL fora dos lances essenciais. Não reenviar material derrubado por denúncia manual.

## 2026-10-03 — Lance certo nos vídeos (achar_lance)
- Novo `achar_lance.py`: play-by-play da ESPN (quarto, relógio, descida) × OCR do placar da transmissão (Vision do macOS, `buscador_assets/ocr/ocr`).
- Revelou 2 erros meus no bloco 01: sidearm escolhido em 131 s (depois do lance; certo = 118,5 s, placar 2Q 1:07 1st & 10) e no-look começando depois do snap (certo = 1,5 s). v12 usa os dois corrigidos; ✅ QA 16/16.
- A faixa de baixo dos highlights da NFL é placar de outros jogos — não serve para identificar o lance.
- QA: texto do próprio vídeo do card (placar da transmissão) saindo da tela dava falso "texto na borda" → ignorar texto dentro de card/recorte.
- Ainda manual: lances genéricos (sem jogo/placar) e conferir se a pessoa no vídeo é a certa (ex.: o Elway no "overhand").

## 2026-10-03 — Identidade visual do canal aplicada (v11)
- Extraída de logo/banner/thumbnail: cores medidas nos pixels; fonte condensada pesada maiúscula (Impact como equivalente local).
- Arthur escolheu entre 2 mockups: **Opção B** (identidade em título, nomes e caixas; frases no estilo das referências) e **sem elementos de prancheta**. Detalhes: [[Identidade Visual]].
- Ajuste: quebra do título em 2 linhas antes de palavra de ligação e nunca terminando linha em "WHEN/THE/OF…".
- v11: ✅ QA 16/16.

## 2026-10-03 — Entradas e saídas bruscas demais (apontado pelo Arthur)
- Medido quadro a quadro a 60 fps (`editor_ae/qa/comparar_animacao.py`, borda do card que entra primeiro):
  - entrada referências: 50% do trajeto em 0,13 s · 90% em 0,38 s · 98% em 0,54 s;
  - nossa v7: 50% em **0,05 s** (tranco) e freada longa → "brusco".
- A análise antiga ("deslocamento em ~0,3 s com ease-out forte") estava errada: medi olhando poucos frames. O certo:
  - **entrada = ease-out cúbico de 0,95 s** (do lado de fora da tela até a posição final; no After: 1º key velocidade 3·D/T com influência 33%, 2º key velocidade 0 com influência 67%) → v9: 50% 0,13 s · 90% 0,34 s · 98% 0,56 s;
  - **saída = ease-in quadrático de 0,8 s** (começa parada, acelera aos poucos; ~0,4 s visível saindo).
- Diálogo do After travou um render; foi preciso clicar OK na tela. Sem permissão de acessibilidade não consigo ver/fechar diálogos.
- v9: ✅ QA 16/16.

## 2026-10-03 — Zoom da cena cortando texto (apontado pelo Arthur)
- Causa: o push-in escala a cena inteira a partir do centro até 115%; elementos perto da borda (título no topo, rótulo lateral à direita) saíam do quadro (v6: 2,2–4,8 s e 22,8–24,8 s).
- Correção no editor: cada cena calcula a área ocupada por todos os elementos e **limita o zoom final** para nada passar de 50 px da borda (cena com rótulo lateral ≈ 102%; card central até ~114%). A esteira (D4), que sai da tela de propósito, fica de fora.
- QA ganhou a verificação **"Texto cortado na borda"** (FALHA): reprovou a v6 nos dois trechos e aprovou a **v7** (16/16).

## 2026-10-02 — Controle de qualidade automático
- Novo verificador ([[Controle de Qualidade]]): 15 checagens contra números das referências + folha lado a lado.
- Validado: reprova a v3 antiga pelos 3 problemas que o Arthur apontou (texto demais, assets < 1,8 s, nomes pequenos); aprova a v5.
- Aprendizado: o detector precisa dos mesmos filtros nas referências e nas prévias (comparar igual com igual); ruídos (placar, marca d'água, motion blur) geravam alarmes falsos até serem filtrados.
- Achado real no bloco 01: 5 textos solo seguidos (63,9–72 s) → corrigido na **v6** com uma imagem (alternativa já baixada) + o termo "adaptability". v6: **✅ 15/15 no QA**.

## 2026-10-02 — Texto demais, assets curtos demais (apontado pelo Arthur)
- Medido: referências ~30% das cenas de imagem com texto; nosso bloco 100%. Texto sobre imagem nas referências = número/preço/data/nome/termo, não frase.
- Seguir o texto o tempo todo picotava as cenas: 3 assets ficavam 0,8–1,0 s na tela.
- Correção no bloco 01 (prévia v5): tiradas as frases sobre os vídeos, "31 yards" virou número sobre o card do Ware, gatilhos ajustados → nenhum asset abaixo de 1,8 s.
- Regra registrada em [[Da Narração às Cenas#Texto × imagem (medido nas referências) ⭐]] e checada automaticamente pelo compilador.

## 2026-10-02 — Retrocesso nos textos (apontado pelo Arthur) e correção
- Fonte, tamanho e sombra dos textos antigos estavam iguais; o problema eram os **3 textos novos** da biblioteca, que eu tinha medido errado olhando miniaturas:
  - nome acima do card: nas referências é **grande** ("Red miso", "Harry Burnett Reese"); o nosso estava miúdo;
  - "mini-legenda": na verdade é texto branco **centralizado e médio** ("casein"); o nosso era rodapé ilegível;
  - rótulo lateral: card menor e rótulo **em 1 linha, grande** ("the aromatics"); o nosso quebrava em 2 linhas pequenas.
- Lição: **medir textos em frame cheio (1920×1080) lado a lado com a referência**, nunca em miniatura de folha de contato. Isso vai entrar no controle de qualidade automático (item 3).
- Com nome acima, os cards do par ficam menores e mais baixos para o nome não encostar no topo.

## 2026-10-02 — Processo invertido: cenas primeiro, assets depois
- Novo `compilar_cenas.py`: um único `cenas.json` (escrito com palavras, sem segundos) vira plano de busca + plano de edição.
- Teste: o bloco do Mahomes reescrito assim compilou com tempos a menos de 0,25 s do plano manual (onde diferiu, foi para a palavra exata) e reaproveitou 22 assets; só 1 asset novo (vídeo vertical para troca no lugar) foi buscado, escolhido e montado — fluxo inteiro sem editar tempos à mão.
- Cuidados implementados: ids de assets novos nunca repetem ids existentes; asset reaproveitado em 2 lugares (logo + sticker) é listado uma vez; vídeo em layout retrato ganha buscas `#shorts`.
- Bloco preparado para começar no meio da narração (deslocamento do áudio), base para juntar vários blocos.

## 2026-10-02 — Bloco 01 refeito com a Biblioteca de Cenas (v2)
- Mesmo bloco, agora com 9 variações: B3, A1, C3 par construído, B8 nome acima, B7 mini-legenda, B5 rótulo em lista, C4 comparação, logos + texto, E4 sticker, C2 cascata, A2 frase que se completa. 113 camadas.
- Reaproveitar **alternativas já baixadas** (`_work/candidatos/...`) dá variedade sem nova busca (ex.: 2ª foto do sidearm).
- 1ª versão do v2 deixou os pares pequenos (cortes paisagem): **pares/trios devem ser cortados em retrato/quadrado**.
- Precisou de 2 assets novos: logo dos Chiefs (sticker/logos) e foto do Spencer Ware (achada desta vez, 865×1050).

## 2026-10-02 — Estudo do repertório de cenas
Resultado: [[Biblioteca de Cenas]] (30+ variações em 6 famílias, A–F).

- O estoque estava limitado porque tratávamos cada cena como **uma composição parada**. Nas referências a cena **evolui** (1 → 2 → troca → texto) em 4–20 s, sem palco vazio → nova família F (sequências).
- Variações novas: cascata sobreposta, rótulo que troca em lista, troca de conteúdo no mesmo quadro, mini-legenda no card, frase que se completa, 1 grande + pequenos empilhados, esteira, sticker de logo no canto, pessoa + criação.
- Medidas corrigidas: gap entre cards é **15–50 px** (não 60); cards ≈ 85% da altura; 43% retrato / 43% paisagem.
- Ferramentas do estudo: `Videos Referencias/estudo_cenas/` (`tiras.py` = 3 momentos por cena; `detectar.py` = caixas de cards/textos a 4 fps; `stats.py`).

## 2026-10-02 — 1º bloco editado no After Effects
Detalhes em [[Edição no After Effects]]. Prévia: `producoes/videos/how-elite-nfl-players-actually-work/edicao/previa_bloco_01.mp4`.

- **Edição 100% por script funciona**: gerador Python → `.jsx` → After (osascript) → `.aep` + render. Montagem em segundos, render de 84 s em ~2 min.
- **Palco vazio**: cenas cujo 1º asset tem gatilho no meio da frase ficavam 1–2 s vazias. Regra nova: o 1º elemento da cena entra quando a cena começa.
- **Asset pulado deixa a cena vazia** → replanejar como texto solo em trechos. (Corrige o que eu tinha dito no teste de assets: "nome sobre o vídeo do lance" não acontece sozinho.)
- `DoScript` sempre devolve 0; o retorno é via arquivo de log.
- `aerender` não achou o template H.264 → render pela fila do After.
- Fonte: Avenir Next Heavy no lugar de Gilroy/Montserrat (não instaladas) — confirmar.

## 2026-10-02 — Teste "Adapting the Pass"
Produção: [[How Elite NFL Players Actually Work]] · 81 s de narração, 23 cenas, 21 assets (12 vídeos).

- **Lance específico → vídeo oficial "<Jogador> Highlights vs. <Adversário>".** Busca descritiva trouxe lances parecidos de outros jogos. → [[Buscas que Funcionam#Lance específico de um jogo (vídeo) ⭐]]
- **Preview de vídeo longo travava a busca** (10 min de preview por vídeo → +30 min). Reduzido para os primeiros 5 min e máx. 15 min de duração → 4 assets em 46 s.
- **Jogador menos famoso (Spencer Ware) quase não tem foto livre**: só Getty (bloqueada) ou ~600 px. Agora fotos pequenas entram no fim da folha marcadas BAIXA. Ware ficou sem foto → nome em texto sobre o vídeo.
- **Commons: nome de pessoa entre aspas** ("Spencer Ware" achava "Wickwire Spencer Steel").
- **Recorte do título levou junto um defensor colado** e deformou o braço → regra "um assunto só". → [[Critérios de Escolha#Recortes (PNG do título, objetos)]]
- **"Patrick Mahomes press conference" trouxe Patrick Estrela** → curadoria visual é indispensável.
- **"overhand throw" trouxe tutoriais amadores** → para gesto técnico, "NFL quarterback throwing slow motion".
- A duração de cada vídeo agora é calculada automaticamente (fim da cena − gatilho + 0,3 s).
- Escolhas duvidosas ganham `"conferir"` e aparecem em vermelho na `revisao.html`.

## 2026-10-02 — Teste "Philly Special" (narração sintética, 23 s)
- Fluxo de ponta a ponta funcionou: 9 assets, recortes limpos, vídeo em 1080p H.264 sem áudio.
- **Bancos com marca d'água** (Alamy etc.) apareciam nos resultados → domínios bloqueados.
- **Logos no Commons**: busca de texto trazia fotos de torcida → o sistema adiciona `intitle:logo`; logo da NFL vem da web com fundo transparente.
- **Uma fonte ocupava todas as vagas** → resultados das fontes agora são intercalados.
- Wikimedia exige User-Agent identificado.
- Preview de vídeo de 2 em 2 s é impreciso para achar o snap → criado `detalhar_video.py` (0,5 s).

## 2026-10-02 — Análise do formato (4 vídeos de referência)
- Formato "___ Explained" é um **template fixo**: fundo de papel, cards com sombra, texto ExtraBold, narração só.
- Medições completas em [[Visual do Formato]] e [[Animação e Ritmo]].
- ~30% das cenas são texto solo; ~50% dos cards são vídeo; algo novo a cada 1–2 s.
