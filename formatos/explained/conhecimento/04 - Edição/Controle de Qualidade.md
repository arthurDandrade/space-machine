---
tags: [pro-football, edicao, qa]
pasta: motor/edicao_ae/qa/
---

# Controle de Qualidade

Voltar: [[00 - Pro Football (Índice)]] · Relacionado: [[Edição no After Effects]] · [[Da Narração às Cenas]] · [[Biblioteca de Cenas]]

Todo bloco passa pelo verificador **antes** de chegar ao Arthur. Ele mede a prévia renderizada + o plano de edição e compara com números medidos nas 4 referências.

```bash
cd motor/edicao_ae
../../.venv/bin/python qa/qa_bloco.py <projeto> --item 01      # usa a prévia mais recente
```
Desde 2026-10-16 a prévia é de rascunho, em 960×540 a 15 Mbps (o vídeo final é renderizado dos .aep dos blocos). Medido no bloco 06 do nfl-draft: as 7 conferências deram igual à prévia cheia e a altura mediana dos textos ficou a mesma (84 px). A 5 Mbps não serve: a compressão engorda as letras e a altura subiu para 92 px (+10%), o que esconderia texto pequeno.

Saída: `edicao/qa_01.md` (✅ OK / ❌ FALHA, com os tempos para corrigir) e `edicao/qa_01.jpg` (nosso frame × frame de referência do mesmo tipo de cena). FALHA = não entregar; corrigir e renderizar de novo.

## O que é verificado (enxuto desde 2026-10-15)
Só o que já pegou defeito de verdade. Cada uma é OK ou FALHA; não há mais ATENÇÃO.
| Verificação | Regra (das referências) | Pega qual problema |
|---|---|---|
| Palco vazio | nada acima de 0,5 s com a tela >92% papel | buracos entre cenas (positions 07 e 14) |
| Texto cortado na borda | nenhum texto a menos de 16 px da borda, por ≥ 2 frames seguidos (0,5 s) e altura ≤ 220 px | zoom da cena empurrando texto para fora (positions 20, rings 02); card saindo da tela não conta |
| Tamanho do texto solo | FALHA com a mediana abaixo de 70% do p10 das referências (108 px → 76 px) | texto pequeno (positions 05: 60 px) |
| Tamanho do nome/rótulo junto dos cards | FALHA com a mediana abaixo de 80% do p10 (84 px → 67 px) | "nome acima" miúdo |
| **Texto por cima de imagem** (2026-10-13) | texto solo/rótulo não cobre > 20% de card/recorte do mesmo estado; nome SOBRE o card não conta | "since 1994" em cima do capacete (E3) |
| **Texto pouco tempo na tela** (2026-10-13) | cada texto ≥ 0,7 s (o ideal é ≥ 1,0 s; título não conta) | "one snap" 0,37 s, "behind the line" 0,52 s, A4 trocando a cada palavra |
| **Origem dos assets** (2026-10-13) | nada de domínio bloqueado (mesma lista do buscador: Vecteezy, Shutterstock...) nem assunto proibido no tema do canal (`canal.json` › `regras.qa`) se o pedido não for desse assunto | marca d'água, vídeo da Copa de 2022 |

### O que saiu em 2026-10-15 e por quê
Medido nos logs dos blocos rodados pelo orquestrador (11–14/10): 53 QAs, 42 aprovados, 11 reprovados em 6 blocos.
- 5 reprovações eram defeito visível e a correção automática resolveu sozinha: palco vazio (positions 07 e 14), texto cortado na borda (positions 20, rings 02) e texto solo pequeno (positions 05).
- 1 era alarme falso: no rings 13, o detector leu um pedaço de foto como rótulo de 52 px. Foram 4 renders, o bloco parou duas vezes e precisou de conserto no código (rótulo só conta quando o `layout_NN.json` diz que há texto).
- As **conferências do plano** nunca reprovaram e saíram, porque o storyboard já cobra as mesmas regras antes de renderizar (`compilar_cenas.py` + `storyboard.py`, com voltas de correção). Eram: texto sobre imagem ≤ 45%, frases sobre imagem, asset ≥ 1,8 s, texto solo 2–6 palavras, textos solo seguidos, variedade de layouts e cenas que evoluem.
- As **atenções** não travavam nada e ninguém lia, então saíram: ritmo, tamanho dos cards, tempo de tela dos assets e tempo só com texto. A mais comum, tempo só com texto, reclamava de 0% em blocos sem texto solo; a faixa de texto solo (12–20%, decisão de 13/10) o `storyboard.py` já cobra. A faixa de atenção do tamanho do texto (70–85% do p10) e do texto rápido (0,7–1,0 s) agora passa.
- Conferido antes de trocar:
  - Em 9 blocos entregues, antigo e novo deram o mesmo veredito.
  - Cada defeito mantido foi forçado numa cópia do rings 13 (texto 0,5 s, texto em cima do card, asset da Vecteezy, texto encostado na borda, 1,5 s de palco vazio, nomes encolhidos), e os dois QAs reprovaram igual.
  - O tempo quase não mudou (28 → 26,5 s num bloco de 58 s): o que pesa é a detecção a 4 fps, que as conferências mantidas usam.
- Se o storyboard terminar "com avisos" aceitos, um asset abaixo de 1,8 s pode passar sem o QA pegar (o storyboard terminou assim 3 vezes, todas com motivo aceito; o QA antigo nunca reprovou por asset curto).

As de texto por cima de imagem e texto pouco tempo leem `edicao/layout_<item>.json`, que o `gerar_ae2.py` grava com posição e tempo final de cada texto e card. A de origem lê o `manifesto.json`. Calibradas nos 21 blocos do positions: pegaram "one snap" (0,37 s), "behind the line" (0,52 s) e "a gap opens" (0,69 s), que ninguém tinha visto. Sem o `layout_<item>.json` (bloco de antes de 2026-10-13), as duas ficam de fora.

## Validação
- Prévia antiga v3 (texto demais, assets curtos, nomes pequenos) → **❌ REPROVADO**: pegou os 3 problemas que o Arthur tinha apontado.
- Prévia atual v5 → **⚠️ aprovado com 1 atenção** (5 textos solo seguidos em 66 s; essa conferência saiu em 2026-10-15).

## Como funciona por dentro
- `medidas_qa.json` desta pasta do formato = linha de base (gerada por `motor/edicao_ae/qa/linha_base.py` a partir das detecções em `<dados>/referencias/<formato>/estudo_cenas/det/`).
- **Conferência no pixel (2026-10-05):** o detector só reconhece cards **retangulares**, e card + globo/bandeira encostados (E5, M5, F9) some dele. Por isso o QA mede, numa passada só (`fracao_ocupada`), quanto de cada frame é diferente do fundo de papel:
  - **Palco vazio** só é acusado se a tela for >92% papel.
  - **Texto solo** só conta frames em que o texto ocupa <15% da tela (senão é um card que o detector perdeu).
- **Nome/rótulo junto dos cards:** conta rótulos acima, à direita **e à esquerda** dos cards (B10, B4); exige formato de palavra (largura ≥ 1,6× a altura, ≥120 px) e a mesma caixa num frame vizinho (≤0,5 s). Antes, o nome à esquerda não contava e sobravam ruídos (caixinhas do vídeo, pedaços do globo): dava 50–62 px com o nome visivelmente em ~90 px. Linha de base regenerada com v1–v4: mediana 112 px (igual), p25 96 px.
- `qa/detectar.py` acha cards, textos pretos e recortes a 4 fps; `qa/medidas.py` tem as medidas usadas igualmente nas referências e nas nossas prévias (comparar igual com igual).
- Cuidados: card em movimento/motion blur pode ser lido como recorte; faixas de placar podem ser lidas como 2º card — os critérios já filtram isso (par = 2 cards lado a lado de altura parecida; texto solo = sem nada mais na tela; texto ≥ 40 px).
- Ao achar um tipo de erro novo que o QA não pegou: adicionar uma verificação aqui e registrar no [[Log de Aprendizados]].
