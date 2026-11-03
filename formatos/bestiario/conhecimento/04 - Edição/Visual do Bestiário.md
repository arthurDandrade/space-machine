---
tags: [bestiario, edicao]
fonte: medição dos 5 vídeos do Depth Theory (2026-11-03); visual implementado no gerar_ae.py + montar_modelo.jsx
---

# Visual do Bestiário

Decidido pelo Arthur em 2026-11-03, depois de medir os vídeos: **animação 2D vetorial como o Depth Theory** (antes o formato era gravura branca sobre preto, que é só o visual das thumbnails deles).

- **1920×1080 a 30 fps.** O vídeo final usa o fps do primeiro bloco.
- **Fundos** desenhados no After (`mar`, `noite`, `grade`, `escuro`) ou cenário gerado; ver [[Biblioteca de Cenas]].
- **Cores**: branco #F2F4F5, cinza #8FA3AD, vermelho #E5484D (destaque, carimbo, risco, sublinhado), papel #EFE7D6 com tinta #23262B (documento e moldura de foto), pílula #0A1820 a 72%.
- **Fontes** (do macOS): Avenir Next Bold em maiúsculas (títulos, frases, números), Avenir Next DemiBold espaçada (rótulos, itens), Baskerville SemiBold (título dentro do documento).
- **Movimento**: a criatura sempre oscila (~9 px, ~1,4°) e nada ~22 px/s para onde olha; entradas de 0,35 s (sobe 18 px), saídas de 0,2 s; linhas se desenham em 0,6–0,9 s; imagens paradas aproximam ~1%/s; foto real entra como foto impressa torta, subindo.
- **Trilha**: `<canal>/identidade/trilha.mp3` (de banco livre, ex.: Pixabay Music) entra no vídeo final (`final.py`) repetida até o fim, a −30 LUFS (canal.json › trilha.lufs), ~12 dB abaixo da narração como nas referências (−21 a −35 dBFS nas pausas). Sem o arquivo, o vídeo sai só com a narração.

## O que separava o nosso do deles (comparação quadro a quadro, 2026-11-03)
1. **A criatura parecia adesivo.** Agora é tingida pela luz do fundo (`FUNDOS[...]["luz"]`, 34%), escurecida (−10) e com a borda de cima acesa (Bevel Alpha); o corpo ondula de leve (Wave Warp).
2. **Fundo claro demais.** O mar deles é quase preto (#0B1D24 → #03080A); raios a 4,5%, partículas desfocadas grandes, vinheta a 62% por cima das imagens e por baixo dos textos.
3. **Criatura pequena e centralizada.** Agora ~70% da largura; no close sai da tela pelo lado de trás; com o "você", ela fica atrás e ele na frente dela.
4. **Frase-chave pequena.** 62 px em vermelho com sublinhado de 6 px, embaixo (como "IT KNOWS WHERE YOU ARE").
5. **Sonar de círculos.** Agora arcos saindo da criatura na direção do "você", que ganha cantoneiras vermelhas de alvo e lanterna.
6. **Falta:** o personagem "você" de verdade (o deles é um mergulhador desenhado que volta em todo vídeo; o nosso ainda é a silhueta branca provisória) — gerar uma vez e pôr em `<canal>/identidade/personagem.png` ou `<vídeo>/elenco/voce.png`.

## Controle de qualidade
`formato.json › qa.checagens`: `vazio_layout` (só o fundo na tela por mais de 0,5 s no meio do bloco, pelo `layout_NN.json`), `layout_tempo` (texto menos de 0,7 s) e `origem`. No teste de 2026-11-03 pegou um carimbo de 0,5 s e 1,1 s de palco vazio, os dois de verdade.

## Medidas das referências (para calibrar)
10–15 mudanças visuais/min, só 16–47% de quadro parado, ~180 palavras/min, trilha o tempo todo. Ver [[Canal de Referência Depth Theory]]. Medir antes de mudar: gerar a montagem antes e depois e comparar o `DADOS` do `montar_NN_v2.jsx`.
