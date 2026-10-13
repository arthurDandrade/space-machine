---
tags: [pro-football, producao]
criado: 2026-10-05
pasta: /Users/arthur/Canais/ProFootball/producoes/videos/who-makes-the-nfl-possible/
---

# Who Makes the NFL Possible

Voltar: [[00 - Pro Football (Índice)]] · Log: [[Log de Aprendizados]]

14 tópicos, um bloco por tópico em `blocos/NN/`. A narração veio **num mp3 só** (`~/Downloads/Who Makes the NFL Possible.mp3`, 894 s); cópia em `_completo/narracao_completa.mp3`, dividida no silêncio antes de cada título (ver Log 2026-10-05 (8)). Roteiro inteiro em `roteiro_completo.txt`.

| Bloco | Tópico | Duração | Status |
|---|---|---|---|
| 01 | The Schedule Makers | 63 s | ✅ QA (v1) · `edicao/bloco 1.mp4` |
| 02 | The Football Makers of Ada, Ohio | 61 s | ✅ QA (v2; atenção ritmo 7,9/min) · `edicao/bloco 2.mp4` |
| 03 | The K-Ball Coordinator | 67 s | ✅ QA (v1; atenção ritmo 7,2/min) · `edicao/bloco 3.mp4` |
| 04 | The Field Director & Turf Crews | 76 s | ✅ QA (v1; atenção ritmo 8,0/min) · `edicao/bloco 4.mp4` |
| 05 | The Equipment Managers | 65 s | ✅ QA (v1) · `edicao/bloco 5.mp4` |
| 06 | The Event Frequency Coordinators | 67 s | ✅ QA (v1; 4 atenções: ritmo 7,3/min, poucas cenas F, texto solo 88 px, texto 4% — candidato a refazer) · `edicao/bloco 6.mp4` |
| 07 | The Sideline Tech Crew | 66 s | ✅ QA (v1; atenções: ritmo 7,3/min, texto solo 1% — conferir medida) · `edicao/bloco 7.mp4` |
| 08 | The Officiating Game Day Assistants | 51 s | ✅ QA (v2; atenção card único = B4/B5, medido ok) · `edicao/bloco 8.mp4` |
| 09 | The Replay Officials & Art McNally GameDay Central | 70 s | ✅ QA (v1; atenção ritmo 8,6/min) · `edicao/bloco 9.mp4` |
| 10 | The Chain Crew | 62 s | ✅ QA (v1; atenção ritmo 8,8/min) · `edicao/bloco 10.mp4` |
| 11 | The Medical Spotters | 59 s | ✅ QA (v1; atenções: ritmo 6,2/min e 5 cards únicos seguidos — candidato a refazer) · `edicao/bloco 11.mp4` |
| 12 | The Green Hat | 59 s | ✅ QA (v1; atenção: 4 cards únicos seguidos) · `edicao/bloco 12.mp4` |
| 13 | The Team Video Departments | 65 s | ✅ QA (v1; ritmo 2,8 e texto 0% = falso alarme, conferido em 9 frames) · `edicao/bloco 13.mp4` |
| 14 | The TV Production Crews | 64 s | ✅ QA (v1; atenção: texto solo 2%) · `edicao/bloco 14.mp4` |

Próximo passo em cada bloco: planejar `cenas.json` → compilar → buscar → subagente `escolher-assets` → editar → QA.

## Notas de transcrição (Whisper errou; texto na tela segue o roteiro)
- 01: "Bye weeks" saiu "Five weeks"; "5,000 Vals" saiu "5,000 valves".
- 04: "turf crews" saiu "turf cruise" (título emendado na 1ª frase).
- 10: "Phil Finanger" saiu "Phil Finanjar".
- 12: título emendado ("The Green Hat TV pays…"): a 1ª cena começa em "TV needs" para o título não sumir.

## Fluxo combinado com o Arthur (2026-10-05)
- Um subagente por bloco (`escolher-assets`): cada um busca e escolhe **só o seu bloco**. Blocos 01–07 buscaram por script e escolhem por subagente; 08–14 buscam e escolhem no subagente.
- Máximo de ~5 buscas ao mesmo tempo (o DuckDuckGo limita).

## A conferir
- 01: kickoff é o de 2024 (BAL@KC, retorno já em andamento, placar embaixo) (01-01-a); horário nobre virou sobrevoo noturno do Allegiant Stadium (01-05-c); Pinchbeck e o quadro magnético são frames do vídeo da NFL Films "The Making of the NFL Schedule" (eaVwY3ptryw), identificação pelo contexto (01-07-a/b); 01-08-a pode pegar o plano seguinte no último frame.
- 08: quase nada de NFL na web para esse tema. Relógio de jogo = celular filmando TV (08-02-a); operador = console Daktronics amador (08-02-c); assistentes bordô → funcionário de colete vermelho (08-03-a); cabine de replay → operador de CableCam (08-04-a) e sala de controle CBS (08-08-b); field communicator/árbitro de headset = Fiesta Bowl (universitário) (08-07-a, 08-08-a). v1 reprovou: 08-02-c 1,7 s → troca antecipada para "ball" (v2).
- 10: Phil Finanger sem foto → chain crew dos Vikings, sem saber se ele está nela (10-07-a); chain crew "2025" é imagem antiga da NFL Films (10-05-a); Tottenham preparado, trecho não detalhado (10-04-b); gráfico Virtual Measurement num monitor (10-08-b).
- 03: medição de pressão = teste de engenharia da Mide, não árbitro da NFL (03-01-a, 03-03-a); vestiário de árbitros da Big 12 (universitário) (03-02-a); K-ball = foto do responsável com colete "K" (03-04-a); Brady 2015 vem de 360p, ficou mole (03-06-a); túnel = entrada do SB LVI, não intervalo (03-07-a).
- 04: corte = drill de treino dos Falcons (04-01-a); médicos com Nyheim Hines identificável (04-01-b); BEAST só em 640x360 com logo AP (04-04-a/b); STRIKE não existe em vídeo → máquina de teste de grama do WSJ (04-05-a); 04-06-b mostra vala com tubo, não colheita de grama; Sills 560x720 (04-07-c).
- 05: nada dos Bucs → vídeo oficial da equipe de material dos Jets (vestiário, caminhão, Arrowhead) em 05-01-a/b, 05-02-a, 05-03-c, 05-06-a; chuteiras da USC (05-03-b); Bucs x Colts 2015 genérico (05-09-a); T.J. Watt de headset no lugar de técnico, selo Prime (05-09-b); título = flight case genérico.
- 11: Cam Newton identificável no hit e se levantando (11-01-a, 11-06-b), sem lesão grave; 11-01-a em 1100x618; 11-04-b e 11-07-a sem staff médico; jogador dos Bills nº 17 entrando na tenda (11-05-b); 11-04-a em câmera lenta 0,55x. Bloco lento: ritmo 6,2/min, 5 cards únicos seguidos.
- 07: Browns de 1962 (Paul Brown), não 1956 (07-02-a); SB XXIX = temporada 1994 (07-03-a); boné laranja com escudo NFL recortado, sem técnico (07-05-a); headsets num banco (GeekWire), não a cabine dos técnicos (07-05-b).
- 12: 12-03-a aparado (tirei 1,9 s do técnico dos Panthers) e em câmera lenta 0,75x; orange sleeves = foto recortada do Commons (12-04-a); sinal de TV timeout = árbitro amador IFAF (12-04-b); torcida em Munique no lugar de fãs em casa (12-07-a).
- 06: EFC de boné laranja = infográfico "The Hat System" com texto (06-03-a); coordenação de frequência = analisador RF Explorer genérico (06-05-a); placar = telão dos Steelers :06→:00 (06-06-a); radioamador com antena yagi (06-08-a); revista de bolsas nos Colts (06-08-b).
- 09: caminhão de replay da CBS no lugar da cabine (09-01-b); estação de replay do @NFLOfficiating — confirmar se é o GameDay Central (09-02-b); desafio NE x KC no lugar de replay assist, ponta do logo CBS (09-04-b); bandeira já no chão (09-05-e); 09-05-g/h em câmera lenta leve; 09-06-c cortado para 1920x734; no-call Rams x Saints 2018 (09-06-d); reunião de árbitros da Big 12 (09-07-c); Blakeman com braço de jogador na borda (09-08-c).
- 02: v1 reprovou (02-05-b 1,5 s: gatilhos "sew"/"turn" colados) → troca antecipada para "leather" (v2). TD do Cam Newton com placar no topo (02-01-a); 02-08-c em 360p (mole); 02-09-a = cesto de bolas/bolas do SB LI no lugar de caixas despachadas; foto de Ada do site da Ohio Northern University (02-11-a).
- 14: vídeo da Verge/FOX "Inside the control room" serviu para 9 cards; caminhão só aparece bem a partir de ~3 s (14-03-a); cinegrafistas da NFL Films anos 80/90, foto (14-05-a); abertura FOX 1994 em VHS (14-05-b); skycam SB XLVI em baixa resolução com placar NBC (14-06-a); final = cinegrafista SNF + Lambeau à noite no lugar do fã ligando a TV (14-06-d).
- 13: videomaker dos Chargers no vestiário (13-01-a); All-22 Game Pass com logo e círculo de anotação (13-02-a); end zone view → Ray Lewis/Roquan vendo filme (13-03-a); câmera da torre → close de câmera Sony (13-03-c); tablet = demo na CES (13-05-a); árbitros da Big 12 (13-06-a).

## Pendências finais (2026-10-06)
- Os 14 blocos passaram no QA (0 falhas). Ajuste sugerido de ritmo/variedade: 06, 11, 12 (e talvez 03, 07).
- Arthur conferir as substituições listadas acima por bloco.

## Fundo novo (2026-10-08)
- Os 14 blocos foram remontados com o fundo de adesivos (`identidade/fundo_papel_nfl.png`, ver [[Identidade Visual]]), sem QA (já aprovados). Prévias `previa_bloco_NN_vfundo.mp4`, copiadas para `edicao/bloco N.mp4`. Conferido: o adesivo da bola aparece no canto dos 14.
- Achado no bloco 02 (~16 s, F8 fábrica + mapa de Ohio): o texto "5,300 PEOPLE" fica parcialmente coberto pelo mapa. Já estava na versão aprovada; o 09 usa o mesmo layout (conferir).
