---
tags: [pro-football, producao]
criado: 2026-10-11
pasta: /Users/arthur/Canais/ProFootball/producoes/videos/every-nfl-position-explained-in-x-minutes/
---

# Every NFL Position Explained in x Minutes

Voltar: [[00 - Pro Football (Índice)]] · Log: [[Log de Aprendizados]]

Cold open + 20 posições, um bloco por tópico em `blocos/NN/`. Roteiro inteiro em `roteiro_completo.txt`. **Primeiro vídeo feito do começo ao fim pela fila do Estúdio**: 21 blocos rodando de 3 em 3, de 2026-10-11 às 22h até 2026-10-12 às 15:38 ("todos entregues"). Depois veio a revisão do Arthur (2026-10-12 e 13), que gerou muitas correções no sistema.

**Vídeo final:** `final/Every NFL Position Explained.mp4` (20min31s, 1080p60). Os 21 blocos em sequência, com uma camada de ajuste com **Noise 6%** por cima ("para dar aquele charme", pedido do Arthur). Projeto do After: `final/final.aep`, montado por `final/montar_final.jsx`. Os blocos emendam direto: cada um termina 0,6 s depois da última palavra e o seguinte começa 0,2 s antes da fala.

| Bloco | Tópico | Duração | Versão final | Assets |
|---|---|---|---|---|
| 00 | Cold open | 13 s | v6 | 7 |
| 01 | Quarterback | 69 s | v4 | 23 |
| 02 | Wide Receiver | 57 s | v5 | 18 |
| 03 | Center | 61 s | v7 | 20 |
| 04 | Running Back | 61 s | v6 | 20 |
| 05 | Fullback | 61 s | v5 | 20 |
| 06 | Tight End | 62 s | v4 | 20 |
| 07 | Guard | 68 s | v8 | 20 |
| 08 | Offensive Tackle | 54 s | v6 | 15 |
| 09 | Defensive Tackle | 64 s | v6 | 17 |
| 10 | Defensive End | 68 s | v4 | 23 |
| 11 | Middle Linebacker | 65 s | v4 | 22 |
| 12 | Outside Linebacker | 57 s | v3 | 16 |
| 13 | Cornerback | 52 s | v6 | 14 |
| 14 | Nickelback | 62 s | v7 | 19 |
| 15 | Safety | 55 s | v2 | 18 |
| 16 | Kicker | 63 s | v2 | 18 |
| 17 | Punter | 55 s | v4 | 16 |
| 18 | Kick Returner | 60 s | v3 | 19 |
| 19 | Gunner | 57 s | v3 | 16 |
| 20 | Long Snapper | 67 s | v7 | 17 |

Todos aprovados no QA (inclusive nas 3 verificações novas de 2026-10-13). A prévia de cada bloco está em `edicao/bloco N.mp4`, e as versões anteriores em `blocos/NN/_work/`.

## O que a revisão do Arthur pegou (e virou correção no sistema)
Detalhes no [[Log de Aprendizados]] (entradas de 2026-10-12 e 2026-10-13).
- **Texto e imagem:** texto do E3 por cima do capacete; texto sumindo antes da imagem; rótulos trocando a cada ~0,8 s (Brady); última palavra empilhada sumindo ("receiver"); nomes sobrepostos na cascata (bloco 07); "cresce" falso ("Monday Night Football"). Tudo corrigido no `gerar_ae2.py`.
- **Mapas e logos:** nomes pequenos, repetidos e cortados (`gerar_mapa.py`); mapa e logo cortados pelo card (agora ficam inteiros e com o próprio formato).
- **Assets:** vídeo da Copa de 2022 (selo FIFA) no lugar de torcida de futebol americano; **17 assets da Vecteezy** com marca d'água ou render de IA, em 11 blocos. Todos trocados, e a Vecteezy foi bloqueada no buscador (URL, página, título e autor).
- **Prevenção:** busca corrige "football" para "american football"; instruções de escolha recusam soccer, marca d'água e IA; o `storyboard.py` avisa tempos de texto ruins; o QA ganhou "texto por cima de imagem", "texto pouco tempo na tela" e "origem dos assets".

## Para o Arthur conferir (ficou em aberto)
- **09 título:** jogador do Texas em três apoios. Tem um pedaço do jogador vizinho na borda esquerda, e o recorte é de 649×806 px.
- **11-02-b:** quem aponta antes do snap é um QB (Dak Prescott), não um linebacker.
- **05, começo:** vídeo de transmissão com a faixa "PRESENTED BY" e o logo da NFL Network.
- **Avisos do QA que não reprovam:** 17 e 20 com ~40% do tempo só com texto (as referências ficam em 10–18%); 07 e 09 com frases de 7 palavras; 11 e 18 com C1 3× seguidas; 02 e 12 com letras pequenas nos diagramas (árvore de rotas e formação 3-4).
- Itens "conferir" das escolhas de cada bloco: na `revisao.html` de cada bloco.

## Publicação
- Descrição do YouTube revisada em 2026-10-13: capítulos tirados do início real de cada bloco no vídeo final (00:13 Quarterback … 19:24 Long Snapper; vídeo de 20:30). A versão anterior ia até 24:20 e tinha números de ferramenta de palavras-chave colados no texto ("20 58 nfl positions").

## Números
- 21 blocos, 378 assets, ~18 vídeos de banco livre (o resto é foto, recorte, mapa ou logo). Sem YouTube.
- Narração tópico por tópico (ver [[Estúdio (orquestrador)]]).
