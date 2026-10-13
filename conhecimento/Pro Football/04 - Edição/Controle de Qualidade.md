---
tags: [pro-football, edicao, qa]
pasta: /Users/arthur/Canais/ProFootball/editor_ae/qa/
---

# Controle de Qualidade

Voltar: [[00 - Pro Football (Índice)]] · Relacionado: [[Edição no After Effects]] · [[Da Narração às Cenas]] · [[Biblioteca de Cenas]]

Todo bloco passa pelo verificador **antes** de chegar ao Arthur. Ele mede a prévia renderizada + o plano de edição e compara com números medidos nas 4 referências.

```bash
cd /Users/arthur/Canais/ProFootball/editor_ae
../buscador_assets/.venv/bin/python qa/qa_bloco.py <projeto> --item 01      # usa a prévia mais recente
```
Saída: `edicao/qa_01.md` (✅ OK / ⚠️ ATENÇÃO / ❌ FALHA, com os tempos para corrigir) e `edicao/qa_01.jpg` (nosso frame × frame de referência do mesmo tipo de cena). FALHA = não entregar; corrigir e renderizar de novo.

## O que é verificado
| Verificação | Regra (das referências) | Pega qual problema |
|---|---|---|
| Texto sobre imagem | ≤ 45% das cenas de imagem (ref. ~30%) | "texto em toda cena" |
| Frases sobre imagem | só nome/número/data/termo | frases da narração em cima do vídeo |
| Tempo mínimo de cada asset | ≥ 1,8 s | assets que passam rápido demais |
| Texto solo 2–6 palavras / máx. 4 seguidos | | frases longas pequenas; muito tempo sem imagem |
| Variedade / cenas que evoluem | sem 3 layouts iguais seguidos; ≥ 30% das cenas com evolução | composição repetitiva |
| Ritmo | 10–21 mudanças visuais/min | vídeo parado ou frenético |
| Palco vazio | nada acima de 0,5 s | buracos entre cenas |
| Texto cortado na borda | nenhum texto a menos de 16 px da borda, por ≥ 2 frames seguidos (0,5 s) e altura ≤ 220 px | zoom da cena empurrando texto para fora (card saindo da tela não conta) |
| Tamanho do texto solo | altura ≈ 108–136 px | texto pequeno |
| Tamanho do nome/rótulo junto dos cards | mediana ≈ 112 px | "nome acima" miúdo |
| Tamanho dos cards (único e par) | ≈ 800–950 px de altura | cards pequenos |
| Tempo de tela dos assets / só texto | mediana ~2,8 s; 10–18% só texto | |
| **Texto por cima de imagem** (2026-10-13) | texto solo/rótulo não cobre > 20% de card/recorte do mesmo estado; nome SOBRE o card não conta | "since 1994" em cima do capacete (E3) |
| **Texto pouco tempo na tela** (2026-10-13) | cada texto ≥ 1,0 s; FALHA < 0,7 s (título não conta) | "199th pick" 0,8 s, "receiver" 0,8 s, A4 trocando a cada palavra |
| **Origem dos assets** (2026-10-13) | nada de domínio bloqueado (mesma lista do buscador: Vecteezy, Shutterstock...) nem futebol/soccer (FIFA, Copa, soccer) se o pedido não for de soccer | marca d'água, vídeo da Copa de 2022 |

As 2 primeiras leem `edicao/layout_<item>.json`, que o `gerar_ae2.py` grava com posição e tempo final de cada texto e card. A de origem lê o `manifesto.json`. Calibradas nos 21 blocos do positions: pegaram "one snap" (0,37 s), "behind the line" (0,52 s) e "a gap opens" (0,69 s), que ninguém tinha visto.

## Validação
- Prévia antiga v3 (texto demais, assets curtos, nomes pequenos) → **❌ REPROVADO**: pegou os 3 problemas que o Arthur tinha apontado.
- Prévia atual v5 → **⚠️ aprovado com 1 atenção** (5 textos solo seguidos em 66 s).

## Como funciona por dentro
- `qa/referencia.json` = linha de base (gerada por `qa/linha_base.py` a partir das detecções em `Videos Referencias/estudo_cenas/det/`).
- **Conferência no pixel (2026-10-05):** o detector só reconhece cards **retangulares**, e card + globo/bandeira encostados (E5, M5, F9) some dele. Por isso o QA mede, numa passada só (`fracao_ocupada`), quanto de cada frame é diferente do fundo de papel:
  - **Palco vazio** só é acusado se a tela for >92% papel.
  - **Texto solo** só conta frames em que o texto ocupa <15% da tela (senão é um card que o detector perdeu).
- **Nome/rótulo junto dos cards:** conta rótulos acima, à direita **e à esquerda** dos cards (B10, B4); exige formato de palavra (largura ≥ 1,6× a altura, ≥120 px) e a mesma caixa num frame vizinho (≤0,5 s). Antes, o nome à esquerda não contava e sobravam ruídos (caixinhas do vídeo, pedaços do globo): dava 50–62 px com o nome visivelmente em ~90 px. Linha de base regenerada com v1–v4: mediana 112 px (igual), p25 96 px.
- `qa/detectar.py` acha cards, textos pretos e recortes a 4 fps; `qa/medidas.py` tem as medidas usadas igualmente nas referências e nas nossas prévias (comparar igual com igual).
- Cuidados: card em movimento/motion blur pode ser lido como recorte; faixas de placar podem ser lidas como 2º card — os critérios já filtram isso (par = 2 cards lado a lado de altura parecida; texto solo = sem nada mais na tela; texto ≥ 40 px).
- Ao achar um tipo de erro novo que o QA não pegou: adicionar uma verificação aqui e registrar no [[Log de Aprendizados]].
