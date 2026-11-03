---
tags: [bestiario, edicao]
---

# Visual do Bestiário

- **1920×1080 a 30 fps** (imagem parada que anda devagar: 60 fps só dobraria o render). O vídeo final (`final.py`) usa o fps do primeiro bloco.
- **Fundo** #060607, vinheta preta (máscara elíptica, 70%) e grão de 3% sem cor no bloco; o vídeo final ainda põe o ruído dele.
- **Cores**: branco de papel velho #EEEBE4 e vermelho #D7262B (só destaque: rótulos do D1, tamanho do E1, fonte da citação, uma frase T1 por bloco).
- **Fontes**: Baskerville SemiBold (títulos e frases), Baskerville Italic (citação), Avenir Next Heavy em maiúsculas (legendas e rótulos). Todas do macOS.
- **Imagens**: fusão de 0,45 s na entrada e na saída; zoom de 1,2%/s até 12%, alternando aproximar e afastar. Gravura e ilustração em modo tela; foto em preto e branco (Python); vídeo com Tint + Brilho/Contraste (After); trecho curto segura o último quadro.
- **Textos**: entram em 0,25 s subindo 14 px; saem com o estado.

## Controle de qualidade
`formato.json › qa.checagens`: `tela_vazia` (tela quase toda preta por mais de 0,5 s no meio do bloco reprova), `layout_tempo` (texto menos de 0,7 s na tela reprova) e `origem` (marca d'água, assunto proibido do tema). O detector de cards do explained não serve no fundo preto e não roda.

## A calibrar no piloto
Ritmo (assets/min), tempo de cada imagem, tamanho dos textos, força do zoom e da vinheta. Medir antes de mudar: gerar a montagem antes e depois e comparar o `DADOS` do `montar_NN_v2.jsx`.
